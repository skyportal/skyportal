import asyncio
import json
import tempfile
import urllib

import arrow
import astropy.units as u
import requests
from astropy.time import Time, TimeDelta
from marshmallow.exceptions import ValidationError
from sqlalchemy.orm import scoped_session, sessionmaker, joinedload
from tornado.ioloop import IOLoop

from baselayer.app.access import auth_or_token, permissions
from baselayer.app.env import load_env
from baselayer.app.model_util import recursive_to_dict
from baselayer.log import make_log

from ...models import (
    Group,
    Obj,
    Spectrum,
    SpectrumObserver,
    SpectrumReducer,
    TNSRobot,
    Instrument,
    Stream,
)
from ...utils.tns import (
    get_IAUname,
    get_tns,
    post_tns,
    TNS_INSTRUMENT_IDS
)
from ..base import BaseHandler

_, cfg = load_env()

Session = scoped_session(sessionmaker())

TNS_URL = cfg['app.tns.endpoint']
upload_url = urllib.parse.urljoin(TNS_URL, 'api/file-upload')
report_url = urllib.parse.urljoin(TNS_URL, 'api/bulk-report')

log = make_log('api/tns')


class TNSRobotHandler(BaseHandler):
    @auth_or_token
    def get(self, tnsrobot_id=None):
        """
        ---
        single:
          tags:
            - tnsrobots
          description: Retrieve a TNS robot
          parameters:
            - in: path
              name: tnsrobot_id
              required: true
              schema:
                type: integer
            - in: query
              name: groupID
              schema:
                type: integer
              description: |
                Filter by group ID
          responses:
            200:
               content:
                application/json:
                  schema: SingleTNSRobot
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          tags:
            - tnsrobots
          description: Retrieve all TNS robots
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfTNSRobots
            400:
              content:
                application/json:
                  schema: Error
        """

        group_id = self.get_query_argument("groupID", None)

        with self.Session() as session:
            try:
                # get owned tnsrobots
                stmt = TNSRobot.select(session.user_or_token).options(joinedload(TNSRobot.auto_report_streams), joinedload(TNSRobot.auto_report_instruments))

                if tnsrobot_id is not None:
                    try:
                        tnsrobot_id = int(tnsrobot_id)
                    except ValueError:
                        return self.error("TNSRobot ID must be an integer.")

                    stmt = stmt.where(TNSRobot.id == tnsrobot_id)
                    tnsrobot = session.scalars(stmt).first()
                    if tnsrobot is None:
                        return self.error(f'No TNS robot with ID {tnsrobot_id}')
                    return self.success(data=tnsrobot)

                elif group_id is not None:
                    try:
                        group_id = int(group_id)
                    except ValueError:
                        return self.error("Group ID must be an integer (if specified).")
                    stmt = stmt.where(TNSRobot.group_id == group_id)

                tns_robots = session.scalars(stmt).unique().all()
                return self.success(data=tns_robots)
            except Exception as e:
                return self.error(f'Failed to retrieve TNS robots: {e}')

    @permissions(['Manage tnsrobots'])
    def post(self):
        """
        ---
        description: Post new TNS robot
        tags:
          - tnsrobots
        requestBody:
          content:
            application/json:
              schema: TNSRobotNoID
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          type: object
                          properties:
                            id:
                              type: integer
                              description: New TNS robot ID
        """

        data = self.get_json()

        auto_report_instrument_ids = data.pop('auto_report_instrument_ids', [])
        auto_report_stream_ids = data.pop('auto_report_stream_ids', [])

        with self.Session() as session:

            try:
                tnsrobot = TNSRobot.__schema__().load(data=data)
            except ValidationError as e:
                return self.error(
                    f'Error parsing posted tnsrobot: "{e.normalized_messages()}"'
                )

            group = session.scalars(
                Group.select(session.user_or_token).where(Group.id == tnsrobot.group_id)
            ).first()
            if group is None:
                return self.error(f'No group with specified ID: {tnsrobot.group_id}')
            
            if len(auto_report_instrument_ids) > 0:
                try:
                    instrument_ids = [int(x) for x in auto_report_instrument_ids]
                    if isinstance(instrument_ids, str):
                        instrument_ids = [int(x) for x in instrument_ids.split(",")]
                    else:
                        instrument_ids = [int(x) for x in instrument_ids]
                except ValueError:
                    return self.error('instrument_ids must be a comma-separated list of integers')
                instrument_ids = list(set(instrument_ids))
                instruments = session.scalars(
                    Instrument.select(session.user_or_token).where(
                        Instrument.id.in_(instrument_ids)
                    )
                ).all()
                if len(instruments) != len(instrument_ids):
                    return self.error(f'One or more instruments not found: {instrument_ids}')
                for instrument in instruments:
                    if instrument.name not in TNS_INSTRUMENT_IDS:
                        return self.error(f'Instrument {instrument.name} not supported for TNS reporting')
                tnsrobot.auto_report_instruments = instruments
            
            if len(auto_report_stream_ids) > 0:
                try:
                    stream_ids = [int(x) for x in auto_report_stream_ids]
                    if isinstance(stream_ids, str):
                        stream_ids = [int(x) for x in stream_ids.split(",")]
                    else:
                        stream_ids = [int(x) for x in stream_ids]
                except ValueError:
                    return self.error('stream_ids must be a comma-separated list of integers')
                stream_ids = list(set(stream_ids))
                streams = session.scalars(
                    Stream.select(session.user_or_token).where(
                        Stream.id.in_(stream_ids)
                    )
                ).all()
                if len(streams) != len(stream_ids):
                    return self.error(f'One or more streams not found: {stream_ids}')
                tnsrobot.auto_report_streams = streams

            session.add(tnsrobot)
            session.commit()
            self.push(
                action='skyportal/REFRESH_TNSROBOTS',
                payload={"group_id": tnsrobot.group_id},
            )
            return self.success(data={"id": tnsrobot.id})

    @permissions(['Manage tnsrobots'])
    def put(self, tnsrobot_id):
        """
        ---
        description: Update TNS robot
        tags:
          - tnsrobots
        parameters:
          - in: path
            name: tnsrobot_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: TNSRobot
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        data = self.get_json()

        # verify that the bot_id, bot_name, and source_group_id are not None and are integers (if specified)
        if 'bot_id' in data:
            try:
                data['bot_id'] = int(data['bot_id'])
            except ValueError:
                return self.error("TNS bot ID must be an integer (if specified).")
        if 'bot_name' in data:
            if (
                data['bot_name'] is None
                or data['bot_name'] == ''
                or not isinstance(data['bot_name'], str)
            ):
                return self.error(
                    "TNS bot name must be a non-empty string (if specified)."
                )
        if 'source_group_id' in data:
            try:
                data['source_group_id'] = int(data['source_group_id'])
            except ValueError:
                return self.error(
                    "TNS source group ID must be an integer (if specified)."
                )

        if 'auto_report_group_ids' in data:
            if isinstance(data['auto_report_group_ids'], str):
                try:
                    data['auto_report_group_ids'] = data['auto_report_group_ids'].split(
                        ','
                    )
                except Exception:
                    return self.error(
                        "TNS auto report group IDs must be a list (if specified)."
                    )
            if not isinstance(data['auto_report_group_ids'], list):
                return self.error(
                    "TNS auto report group IDs must be a list (if specified)."
                )
            for group_id in data['auto_report_group_ids']:
                try:
                    int(group_id)
                except ValueError:
                    return self.error(
                        "TNS auto report group IDs must be integers (if specified)."
                    )
            if len(data['auto_report_group_ids']) == 0:
                data['auto_reporters'] = ''

            if 'auto_report_instrument_ids' in data:
                try:
                    instrument_ids = [int(x) for x in data['auto_report_instrument_ids']]
                    if isinstance(instrument_ids, str):
                        instrument_ids = [int(x) for x in instrument_ids.split(",")]
                    else:
                        instrument_ids = [int(x) for x in instrument_ids]
                except ValueError:
                    return self.error('instrument_ids must be a comma-separated list of integers')
                instrument_ids = list(set(instrument_ids))

            if 'auto_report_stream_ids' in data:
                try:
                    stream_ids = [int(x) for x in data['auto_report_stream_ids']]
                    if isinstance(stream_ids, str):
                        stream_ids = [int(x) for x in stream_ids.split(",")]
                    else:
                        stream_ids = [int(x) for x in stream_ids]
                except ValueError:
                    return self.error('stream_ids must be a comma-separated list of integers')
                stream_ids = list(set(stream_ids))


        with self.Session() as session:
            try:
                tnsrobot = session.scalars(
                    TNSRobot.select(session.user_or_token).where(
                        TNSRobot.id == tnsrobot_id
                    )
                ).first()
                if tnsrobot is None:
                    return self.error(f'No TNS robot with ID {tnsrobot_id}')

                if (
                    len(data.get('auto_report_group_ids', [])) > 0
                    and data.get('auto_reporters', '') in [None, '']
                    and tnsrobot.auto_reporters in [None, '']
                ):
                    return self.error(
                        "TNS auto reporters must be a non-empty string when auto report group IDs are specified."
                    )

                auto_report_instrument_ids = data.pop('auto_report_instrument_ids', [])
                auto_report_stream_ids = data.pop('auto_report_stream_ids', [])

                for key, val in data.items():
                    setattr(tnsrobot, key, val)

                if len(auto_report_instrument_ids) > 0:
                    instruments = session.scalars(
                        Instrument.select(session.user_or_token).where(
                            Instrument.id.in_(instrument_ids)
                        )
                    ).all()
                    if len(instruments) != len(instrument_ids):
                        return self.error(f'One or more instruments not found: {instrument_ids}')
                    
                    for instrument in instruments:
                        if instrument.name not in TNS_INSTRUMENT_IDS:
                            return self.error(f'Instrument {instrument.name} not supported for TNS reporting')
                    tnsrobot.auto_report_instruments = instruments

                if len(auto_report_stream_ids) > 0:
                    streams = session.scalars(
                        Stream.select(session.user_or_token).where(
                            Stream.id.in_(stream_ids)
                        )
                    ).all()
                    if len(streams) != len(stream_ids):
                        return self.error(f'One or more streams not found: {stream_ids}')
                    tnsrobot.auto_report_streams = streams
                
                session.commit()
                self.push(
                    action='skyportal/REFRESH_TNSROBOTS',
                    payload={"group_id": tnsrobot.group_id},
                )
                return self.success()
            except Exception as e:
                raise e
                return self.error(f'Failed to update TNS robot: {e}')

    @permissions(['Manage tnsrobots'])
    def delete(self, tnsrobot_id):
        """
        ---
        description: Delete TNS robot.
        tags:
          - tnsrobots
        parameters:
          - in: path
            name: tnsrobot_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        try:
            tnsrobot_id = int(tnsrobot_id)
        except ValueError:
            return self.error("TNSRobot ID must be an integer.")

        with self.Session() as session:
            tnsrobot = session.scalars(
                TNSRobot.select(session.user_or_token, mode='delete').where(
                    TNSRobot.id == tnsrobot_id
                )
            ).first()
            if tnsrobot is None:
                return self.error(f'No TNS robot with ID {tnsrobot_id}')
            session.delete(tnsrobot)
            session.commit()
            self.push(
                action='skyportal/REFRESH_TNSROBOTS',
                payload={"group_id": tnsrobot.group_id},
            )
            return self.success()


class BulkTNSHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """
        ---
        description: Retrieve objects from TNS
        tags:
          - objs
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  tnsrobotID:
                    type: int
                    description: |
                      TNS Robot ID.
                  startDate:
                    type: string
                    description: |
                      Arrow-parseable date string (e.g. 2020-01-01).
                      Filter by public_timestamp >= startDate.
                      Defaults to one day ago.
                  groupIds:
                    type: array
                    items:
                      type: integer
                    description: |
                      List of IDs of groups to indicate labelling for
                required:
                  - tnsrobotID
                  - groupIds
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """

        data = self.get_json()
        group_ids = data.get("groupIds", None)
        if group_ids is None:
            return self.error('group_ids is required')
        elif type(group_ids) == str:
            group_ids = [int(x) for x in group_ids.split(",")]
        elif not type(group_ids) == list:
            return self.error('group_ids type not understood')

        start_date = data.get('startDate', None)
        if start_date is None:
            start_date = Time.now() - TimeDelta(1 * u.day)
        else:
            start_date = Time(arrow.get(start_date.strip()).datetime)

        tnsrobot_id = data.get("tnsrobotID", None)
        if tnsrobot_id is None:
            return self.error('tnsrobotID is required')

        include_photometry = data.get("includePhotometry", False)
        include_spectra = data.get("includeSpectra", False)

        with self.Session() as session:
            tnsrobot = session.scalars(
                TNSRobot.select(session.user_or_token).where(TNSRobot.id == tnsrobot_id)
            ).first()
            if tnsrobot is None:
                return self.error(f'No TNSRobot available with ID {tnsrobot_id}')

            altdata = tnsrobot.altdata
            if not altdata:
                return self.error('Missing TNS information.')
            if 'api_key' not in altdata:
                return self.error('Missing TNS API key.')

            try:
                loop = asyncio.get_event_loop()
            except Exception:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            IOLoop.current().run_in_executor(
                None,
                lambda: get_tns(
                    tnsrobot.id,
                    self.associated_user_object.id,
                    include_photometry=include_photometry,
                    include_spectra=include_spectra,
                    start_date=start_date.isot,
                    group_ids=group_ids,
                ),
            )

            return self.success()


class ObjTNSHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id):
        """
        ---
        description: Retrieve an Obj from TNS
        tags:
          - objs
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """

        tnsrobot_id = self.get_query_argument("tnsrobotID", None)
        if tnsrobot_id is None:
            return self.error('tnsrobotID is required')

        include_photometry = self.get_query_argument("includePhotometry", False)
        include_spectra = self.get_query_argument("includeSpectra", False)

        with self.Session() as session:
            obj = session.scalars(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            ).first()
            if obj is None:
                return self.error(f'No object available with ID {obj_id}')

            tnsrobot = session.scalars(
                TNSRobot.select(session.user_or_token).where(TNSRobot.id == tnsrobot_id)
            ).first()
            if tnsrobot is None:
                return self.error(f'No TNSRobot available with ID {tnsrobot_id}')

            altdata = tnsrobot.altdata
            if not altdata:
                return self.error('Missing TNS information.')
            if 'api_key' not in altdata:
                return self.error('Missing TNS API key.')

            try:
                loop = asyncio.get_event_loop()
            except Exception:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            IOLoop.current().run_in_executor(
                None,
                lambda: get_tns(
                    tnsrobot.id,
                    self.associated_user_object.id,
                    include_photometry=include_photometry,
                    include_spectra=include_spectra,
                    obj_id=obj.id,
                ),
            )

            return self.success()

    @auth_or_token
    def post(self, obj_id):
        """
        ---
        description: Post an Obj to TNS
        tags:
          - objs
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """

        with self.Session() as session:
            data = self.get_json()
            tnsrobotID = data.get('tnsrobotID')
            reporters = data.get('reporters', '')
            archival = data.get('archival', False)
            archival_comment = data.get('archivalComment', '')
            instrument_ids = data.get('instrument_ids', [])
            stream_ids = data.get('stream_ids', [])

            if tnsrobotID is None:
                return self.error('tnsrobotID is required')
            if reporters == '' or not isinstance(reporters, str):
                return self.error(
                    'reporters is required and must be a non-empty string'
                )
            if len(instrument_ids) > 0:
                try:
                    instrument_ids = [int(x) for x in instrument_ids]
                except ValueError:
                    return self.error('instrument_ids must be a comma-separated list of integers')
                instrument_ids = list(set(instrument_ids))
                instruments = session.scalars(
                    Instrument.select(session.user_or_token).where(
                        Instrument.id.in_(instrument_ids)
                    )
                ).all()
                if len(instruments) != len(instrument_ids):
                    return self.error(f'One or more instruments not found: {instrument_ids}')

                for instrument in instruments:
                    if instrument.name not in TNS_INSTRUMENT_IDS:
                        return self.error(f'Instrument {instrument.name} not supported for TNS reporting')
                
            if stream_ids is not None:
                try:
                    if isinstance(stream_ids, str):
                        stream_ids = [int(x) for x in stream_ids.split(",")]
                    else:
                        stream_ids = [int(x) for x in stream_ids]
                except ValueError:
                    return self.error('stream_ids must be a comma-separated list of integers')
                stream_ids = list(set(stream_ids))
                streams = session.scalars(
                    Stream.select(session.user_or_token).where(
                        Stream.id.in_(stream_ids)
                    )
                ).all()
                if len(streams) != len(stream_ids):
                    return self.error(f'One or more streams not found: {stream_ids}')

            obj = session.scalars(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            ).first()
            if obj is None:
                return self.error(f'No object available with ID {obj_id}')

            tnsrobot = session.scalars(
                TNSRobot.select(session.user_or_token).where(TNSRobot.id == tnsrobotID)
            ).first()
            if tnsrobot is None:
                return self.error(f'No TNSRobot available with ID {tnsrobotID}')

            if archival is True:
                if len(archival_comment) == 0:
                    return self.error(
                        'If source flagged as archival, archival_comment is required'
                    )

            altdata = tnsrobot.altdata
            if not altdata:
                return self.error('Missing TNS information.')
            if 'api_key' not in altdata:
                return self.error('Missing TNS API key.')

            try:
                loop = asyncio.get_event_loop()
            except Exception:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            IOLoop.current().run_in_executor(
                None,
                lambda: post_tns(
                    obj_ids=[obj.id],
                    tnsrobot_id=tnsrobot.id,
                    user_id=self.associated_user_object.id,
                    reporters=reporters,
                    archival=archival,
                    archival_comment=archival_comment,
                    instrument_ids=instrument_ids,
                    stream_ids=stream_ids,
                    timeout=30,
                ),
            )

            return self.success()


class SpectrumTNSHandler(BaseHandler):
    @auth_or_token
    def post(self, spectrum_id):
        """
        ---
        description: Submit a (classification) spectrum to TNS
        tags:
          - spectra
        parameters:
          - in: path
            name: spectrum_id
            required: true
            schema:
              type: integer
          - in: query
            name: tnsrobotID
            schema:
              type: int
            required: true
            description: |
                SkyPortal TNS Robot ID
          - in: query
            name: classificationID
            schema:
              type: string
            description: |
                Classification ID (see TNS documentation at
                https://www.wis-tns.org/content/tns-getting-started
                for options)
          - in: query
            name: classifiers
            schema:
              type: string
            description: |
                List of those performing classification.
          - in: query
            name: spectrumType
            schema:
              type: string
            description: |
                Type of spectrum that this is. Valid options are:
                ['object', 'host', 'sky', 'arcs', 'synthetic']
          - in: query
            name: spectrumComment
            schema:
              type: string
            description: |
                Comment on the spectrum.
          - in: query
            name: classificationComment
            schema:
              type: string
            description: |
                Comment on the classification.
        responses:
          200:
            content:
              application/json:
                schema: SingleSpectrum
          400:
            content:
              application/json:
                schema: Error
        """

        data = self.get_json()
        tnsrobotID = data.get('tnsrobotID')
        classificationID = data.get('classificationID', None)
        classifiers = data.get('classifiers', '')
        spectrum_type = data.get('spectrumType', '')
        spectrum_comment = data.get('spectrumComment', '')
        classification_comment = data.get('classificationComment', '')

        if tnsrobotID is None:
            return self.error('tnsrobotID is required')

        with self.Session() as session:
            tnsrobot = session.scalars(
                TNSRobot.select(session.user_or_token).where(TNSRobot.id == tnsrobotID)
            ).first()
            if tnsrobot is None:
                return self.error(f'No TNSRobot available with ID {tnsrobotID}')

            altdata = tnsrobot.altdata
            if not altdata:
                return self.error('Missing TNS information.')

            spectrum = session.scalars(
                Spectrum.select(session.user_or_token).where(Spectrum.id == spectrum_id)
            ).first()
            if spectrum is None:
                return self.error(f'No spectrum with ID {spectrum_id}')

            spec_dict = recursive_to_dict(spectrum)
            spec_dict["instrument_name"] = spectrum.instrument.name
            spec_dict["groups"] = spectrum.groups
            spec_dict["reducers"] = spectrum.reducers
            spec_dict["observers"] = spectrum.observers
            spec_dict["owner"] = spectrum.owner

            external_reducer = session.scalars(
                SpectrumReducer.select(session.user_or_token).where(
                    SpectrumReducer.spectr_id == spectrum_id
                )
            ).first()
            if external_reducer is not None:
                spec_dict["external_reducer"] = external_reducer.external_reducer

            external_observer = session.scalars(
                SpectrumObserver.select(session.user_or_token).where(
                    SpectrumObserver.spectr_id == spectrum_id
                )
            ).first()
            if external_observer is not None:
                spec_dict["external_observer"] = external_observer.external_observer

            tns_headers = {
                'User-Agent': f'tns_marker{{"tns_id":{tnsrobot.bot_id},"type":"bot", "name":"{tnsrobot.bot_name}"}}'
            }

            tns_prefix, tns_name = get_IAUname(
                spectrum.obj.id, altdata['api_key'], tns_headers
            )
            if tns_name is None:
                return self.error('TNS name missing... please first post to TNS.')

            if spectrum.obj.redshift:
                redshift = spectrum.obj.redshift

            spectype_id = ['object', 'host', 'sky', 'arcs', 'synthetic'].index(
                spectrum_type
            ) + 1

            if spec_dict["altdata"] is not None:
                header = spec_dict["altdata"]
                exposure_time = header['EXPTIME']
            else:
                exposure_time = None

            wav = spec_dict['wavelengths']
            flux = spec_dict['fluxes']
            err = spec_dict['errors']

            filename = f'{spectrum.instrument.name}.{spectrum_id}'
            filetype = 'ascii'

            with tempfile.NamedTemporaryFile(
                prefix=filename,
                suffix=f'.{filetype}',
                mode='w',
            ) as f:
                if err is not None:
                    for i in range(len(wav)):
                        f.write(f'{wav[i]} \t {flux[i]} \t {err[i]} \n')
                else:
                    for i in range(len(wav)):
                        f.write(f'{wav[i]} \t {flux[i]}\n')
                f.flush()

                data = {'api_key': altdata['api_key']}

                if filetype == 'ascii':
                    files = [('files[]', (filename, open(f.name), 'text/plain'))]
                elif filetype == 'fits':
                    files = [
                        ('files[0]', (filename, open(f.name, 'rb'), 'application/fits'))
                    ]

                r = requests.post(
                    upload_url, headers=tns_headers, data=data, files=files
                )
                if r.status_code != 200:
                    return self.error(f'{r.content}')

                spectrumdict = {
                    'instrumentid': spectrum.instrument.tns_id,
                    'observer': spec_dict["observers"],
                    'reducer': spec_dict["reducers"],
                    'spectypeid': spectype_id,
                    'ascii_file': filename,
                    'fits_file': '',
                    'remarks': spectrum_comment,
                    'spec_proprietary_period': 0.0,
                    'obsdate': spec_dict['observed_at'],
                }
                if exposure_time is not None:
                    spectrumdict['exptime'] = exposure_time

                classification_report = {
                    'name': tns_name,
                    'classifier': classifiers,
                    'objtypeid': classificationID,
                    'groupid': tnsrobot.source_group_id,
                    'remarks': classification_comment,
                    'spectra': {'spectra-group': {'0': spectrumdict}},
                }
                if redshift is not None:
                    classification_report['redshift'] = redshift

                classificationdict = {
                    'classification_report': {'0': classification_report}
                }

                data = {
                    'api_key': altdata['api_key'],
                    'data': json.dumps(classificationdict),
                }

                r = requests.post(report_url, headers=tns_headers, data=data)
                if r.status_code == 200:
                    tns_id = r.json()['data']['report_id']
                    return self.success(data={'tns_id': tns_id})
                else:
                    return self.error(f'{r.content}')
