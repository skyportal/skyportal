import astropy.time
import json
import requests
import tempfile
import urllib

from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from baselayer.app.model_util import recursive_to_dict
from baselayer.app.env import load_env

from .photometry import serialize
from ..base import BaseHandler
from ...models import (
    DBSession,
    Group,
    Obj,
    Photometry,
    Spectrum,
    SpectrumReducer,
    SpectrumObserver,
    TNSRobot,
)


_, cfg = load_env()


TNS_URL = cfg['app.tns_endpoint']
upload_url = urllib.parse.urljoin(TNS_URL, 'api/file-upload')
report_url = urllib.parse.urljoin(TNS_URL, 'api/bulk-report')
reply_url = urllib.parse.urljoin(TNS_URL, 'api/bulk-report-reply')
search_url = urllib.parse.urljoin(TNS_URL, 'api/get/search')


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

        # get owned tnsrobots
        tnsrobots = TNSRobot.query_records_accessible_by(self.current_user)

        if tnsrobot_id is not None:
            try:
                tnsrobot_id = int(tnsrobot_id)
            except ValueError:
                return self.error("TNSRobot ID must be an integer.")
            tnsrobots = tnsrobots.filter(TNSRobot.id == tnsrobot_id).all()
            if len(tnsrobots) == 0:
                return self.error("Could not retrieve tnsrobot.")
            return self.success(data=tnsrobots[0])

        tnsrobots = tnsrobots.all()
        self.verify_and_commit()
        return self.success(data=tnsrobots)

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
        try:
            tnsrobot = TNSRobot.__schema__().load(data=data)
        except ValidationError as e:
            return self.error(
                f'Error parsing posted tnsrobot: "{e.normalized_messages()}"'
            )

        group = Group.get_if_accessible_by(tnsrobot.group_id, self.current_user)
        if group is None:
            return self.error(f'No group with specified ID: {tnsrobot.group_id}')

        DBSession().add(tnsrobot)
        self.verify_and_commit()
        return self.success(data={"id": tnsrobot.id})

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
        tnsrobot = TNSRobot.get_if_accessible_by(
            tnsrobot_id, self.current_user, mode='delete'
        )
        if tnsrobot is None:
            return self.error(f'No TNS robot with ID {tnsrobot_id}')
        DBSession().delete(tnsrobot)
        self.verify_and_commit()
        return self.success()


class ObjTNSHandler(BaseHandler):
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

        obj = Obj.get_if_accessible_by(
            obj_id,
            self.current_user,
            mode='read',
            raise_if_none=True,
        )

        photometry = (
            Photometry.query_records_accessible_by(self.current_user)
            .filter(Photometry.obj_id == obj_id)
            .all()
        )
        photometry = [serialize(phot, 'ab', 'mag') for phot in photometry]

        data = self.get_json()
        tnsrobotID = data.get('tnsrobotID')
        reporters = data.get('reporters', '')

        if tnsrobotID is None:
            return self.error('tnsrobotID is required')

        tnsrobot = DBSession().query(TNSRobot).filter(TNSRobot.id == tnsrobotID).one()

        altdata = tnsrobot.altdata
        if not altdata:
            raise ValueError('Missing TNS information.')

        tns_headers = {
            'User-Agent': f'tns_marker{"tns_id":{tnsrobot.bot_id},"type":"bot", "name":"{tnsrobot.bot_name}"}'
        }

        time_first = mag_first = magerr_first = filt_first = instrument_first = None
        time_last = mag_last = magerr_last = filt_last = instrument_last = None
        time_last_nondetection = (
            limmag_last_nondetection
        ) = filt_last_nondetection = instrument_last_nondetection = None

        for phot in photometry:
            if phot['mag'] is None:
                if (
                    time_last_nondetection is None
                    or phot['mjd'] > time_last_nondetection
                ):
                    time_last_nondetection = phot['mjd']
                    limmag_last_nondetection = phot['limiting_mag']
                    filt_last_nondetection = phot['filter']
                    instrument_last_nondetection = phot['instrument_name']
            else:
                if time_first is None or phot['mjd'] < time_first:
                    time_first = phot['mjd']
                    mag_first = phot['mag']
                    magerr_first = phot['magerr']
                    filt_first = phot['filter']
                    instrument_first = phot['instrument_name']
                if time_last is None or phot['mjd'] > time_last:
                    time_last = phot['mjd']
                    mag_last = phot['mag']
                    magerr_last = phot['magerr']
                    filt_last = phot['filter']
                    instrument_last = phot['instrument_name']
        if time_last_nondetection is None:
            return self.error('Need last non-detection for TNS report')

        tns_prefix, tns_name = get_IAUname(obj.id, altdata['api_key'], tns_headers)
        if tns_name is not None:
            return self.error(f'Already posted to TNS as {tns_name}.')

        proprietary_period = {
            "proprietary_period_value": 0,
            "proprietary_period_units": "years",
        }
        non_detection = {
            "obsdate": astropy.time.Time(time_last_nondetection, format='mjd').jd,
            "limiting_flux": limmag_last_nondetection,
            "flux_units": "1",
            "filter_value": filt_last_nondetection,
            "instrument_value": instrument_last_nondetection,
        }
        phot_first = {
            "obsdate": astropy.time.Time(time_first, format='mjd').jd,
            "flux": mag_first,
            "flux_err": magerr_first,
            "flux_units": "1",
            "filter_value": filt_first,
            "instrument_value": instrument_first,
        }
        phot_last = {
            "obsdate": astropy.time.Time(time_last, format='mjd').jd,
            "flux": mag_last,
            "flux_err": magerr_last,
            "flux_units": "1",
            "filter_value": filt_last,
            "instrument_value": instrument_last,
        }

        at_report = {
            "ra": {"value": obj.ra},
            "dec": {"value": obj.dec},
            "groupid": tnsrobot.source_group_id,
            "internal_name_format": {
                "prefix": instrument_first,
                "year_format": "YY",
                "postfix": "",
            },
            "internal_name": obj.id,
            "reporter": reporters,
            "discovery_datetime": astropy.time.Time(time_first, format='mjd').datetime,
            "at_type": 1,  # allow other options?
            "proprietary_period_groups": [tnsrobot.source_group_id],
            "proprietary_period": proprietary_period,
            "non_detection": non_detection,
            "photometry": {"photometry_group": {"0": phot_first, "1": phot_last}},
        }
        report = {"at_report": {"0": at_report}}

        data = {
            'api_key': altdata['api_key'],
            'data': json.dumps(report),
        }

        r = requests.post(report_url, headers=tns_headers, data=data)
        if r.status_code == 200:
            tns_id = r.json()['data']['report_id']
            return self.success(data={'tns_id': tns_id})
        else:
            return self.error(f'{r.content}')

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

        tnsrobot = DBSession().query(TNSRobot).filter(TNSRobot.id == tnsrobotID).one()

        altdata = tnsrobot.altdata
        if not altdata:
            raise ValueError('Missing TNS information.')

        spectrum = Spectrum.get_if_accessible_by(
            spectrum_id,
            self.current_user,
        )
        if spectrum is None:
            return self.error(f'No spectrum with ID {spectrum_id}')

        spec_dict = recursive_to_dict(spectrum)
        spec_dict["instrument_name"] = spectrum.instrument.name
        spec_dict["groups"] = spectrum.groups
        spec_dict["reducers"] = spectrum.reducers
        spec_dict["observers"] = spectrum.observers
        spec_dict["owner"] = spectrum.owner

        external_reducer = (
            DBSession()
            .query(SpectrumReducer.external_reducer)
            .filter(SpectrumReducer.spectr_id == spectrum_id)
            .first()
        )
        if external_reducer is not None:
            spec_dict["external_reducer"] = external_reducer[0]

        external_observer = (
            DBSession()
            .query(SpectrumObserver.external_observer)
            .filter(SpectrumObserver.spectr_id == spectrum_id)
            .first()
        )
        if external_observer is not None:
            spec_dict["external_observer"] = external_observer[0]

        tns_headers = {
            'User-Agent': f'tns_marker{"tns_id":{tnsrobot.bot_id},"type":"bot", "name":"{tnsrobot.bot_name}"}'
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

            r = requests.post(upload_url, headers=tns_headers, data=data, files=files)
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

            classificationdict = {'classification_report': {'0': classification_report}}

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


def get_IAUname(objname, api_key, headers):
    """Query TNS to get IAU name (if exists)
    Parameters
    ----------
    objname : str
        Name of the object to query TNS for
    Returns
    -------
    list
        IAU prefix, IAU name
    """

    req_data = {
        "ra": "",
        "dec": "",
        "radius": "",
        "units": "",
        "objname": "",
        "objname_exact_match": 0,
        "internal_name": objname.replace('_', ' '),
        "internal_name_exact_match": 0,
        "objid": "",
    }

    data = {'api_key': api_key, 'data': json.dumps(req_data)}
    r = requests.post(search_url, headers=headers, data=data)
    json_response = json.loads(r.text)
    reply = json_response['data']['reply']

    if len(reply) > 0:
        return reply[0]['prefix'], reply[0]['objname']
    else:
        return None, None
