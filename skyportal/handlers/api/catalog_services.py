import arrow
from astropy.time import Time
from astropy.table import Table
import base64
import functools
import glob
from marshmallow.exceptions import ValidationError
import numpy as np
import pandas as pd
from sqlalchemy.orm import sessionmaker, scoped_session
import sqlalchemy as sa
import swifttools.ukssdc.query as uq
import tempfile
import time
from tornado.ioloop import IOLoop

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from baselayer.log import make_log

try:
    from .alert import post_alert

    alert_available = True
except Exception:
    alert_available = False

from .source import post_source
from .photometry import add_external_photometry

from ..base import BaseHandler
from ...models import (
    Allocation,
    CatalogQuery,
    Comment,
    DBSession,
    Group,
    Instrument,
    Localization,
    Obj,
    Telescope,
    User,
)
from ...models.schema import CatalogQueryPost
from ...utils.catalog import get_conesearch_centers, query_kowalski, query_fink

_, cfg = load_env()


log = make_log('api/catalogs')

Session = scoped_session(sessionmaker(bind=DBSession.session_factory.kw["bind"]))


class CatalogQueryHandler(BaseHandler):
    @auth_or_token
    async def post(self):
        """
        ---
        description: Submit catalog queries
        tags:
          - catalog_queries
        requestBody:
          content:
            application/json:
              schema: CatalogQueryPost
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
          400:
            content:
              application/json:
                schema: Error
        """

        data = self.get_json()

        try:
            data = CatalogQueryPost.load(data)
        except ValidationError as e:
            return self.error(
                f'Invalid / missing parameters: {e.normalized_messages()}'
            )

        data["requester_id"] = self.associated_user_object.id
        data['allocation_id'] = int(data['allocation_id'])

        if 'catalogName' not in data['payload']:
            return self.error('catalogName required in query payload')

        with self.Session():

            if 'target_group_ids' in data and len(data['target_group_ids']) > 0:
                group_ids = data['target_group_ids']
            else:
                group_ids = [g.id for g in self.current_user.accessible_groups]

            fetch_tr = functools.partial(
                fetch_transients,
                data['allocation_id'],
                self.associated_user_object.id,
                group_ids,
                data['payload'],
            )

            IOLoop.current().run_in_executor(None, fetch_tr)

            return self.success()


def fetch_transients(allocation_id, user_id, group_ids, payload):
    """Fetch catalog transients.
    allocation_id : int
        ID of the allocation
    user_id : int
        ID of the User
    payload : dict
        Payload for the catalog query
    """

    session = Session()
    obj_ids = []

    try:
        user = session.scalar(sa.select(User).where(User.id == user_id))
        allocation = session.scalar(
            sa.select(Allocation).where(Allocation.id == allocation_id)
        )

        groups = session.scalars(
            Group.select(user).where(Group.id.in_(group_ids))
        ).all()

        catalog_query = CatalogQuery(
            requester_id=user_id,
            allocation_id=allocation_id,
            payload=payload,
            target_groups=groups,
        )
        session.add(catalog_query)
        session.commit()

        localization = session.scalars(
            sa.select(Localization).where(
                Localization.dateobs == payload['localizationDateobs'],
                Localization.localization_name == payload['localizationName'],
            )
        ).first()

        healpix = localization.flat_2d
        ra_center, dec_center = get_conesearch_centers(
            healpix, level=payload['localizationCumprob']
        )

        start_date = Time(arrow.get(payload['startDate'].strip()).datetime)
        end_date = Time(arrow.get(payload['endDate'].strip()).datetime)

        jd_trigger = start_date.jd
        dt = end_date.jd - start_date.jd

        if payload['catalogName'] == 'ZTF-Kowalski':
            altdata = allocation.altdata
            if not altdata:
                raise ValueError('Missing allocation information.')

            # allow access to public data only by default
            program_id_selector = {1}

            for stream in user.streams:
                if "ztf" in stream.name.lower():
                    program_id_selector.update(set(stream.altdata.get("selector", [])))

            program_id_selector = list(program_id_selector)

            log("Querying kowalski for sources")
            # Query kowalski
            sources = query_kowalski(
                altdata['access_token'],
                jd_trigger,
                ra_center,
                dec_center,
                max_days=dt,
                within_days=dt,
            )
            obj_ids = []
            log("Looping over sources")
            for source in sources:
                log(f"Retrieving {source['id']}")
                s = session.scalars(
                    Obj.select(user).where(Obj.id == source['id'])
                ).first()
                if s is None:
                    obj_id = post_source(source, user_id, session)
                    obj_ids.append(obj_id)

                if alert_available:
                    post_alert(
                        source['id'],
                        None,
                        group_ids,
                        program_id_selector,
                        user.id,
                        session,
                    )
            log("Finished querying Kowalski for sources")

        elif payload['catalogName'] == 'ZTF-Fink':

            instrument = session.scalars(
                Instrument.select(user).where(Instrument.name == 'ZTF')
            ).first()
            if instrument is None:
                raise ValueError('Expected an Instrument named ZTF')

            log("Querying Fink for sources")
            sources = query_fink(
                jd_trigger, ra_center, dec_center, max_days=dt, within_days=dt
            )

            obj_ids = []
            log("Looping over sources")
            for source in sources:
                df = source.pop('data')
                log(f"Retrieving {source['id']}")

                data_out = {
                    'obj_id': source['id'],
                    'instrument_id': instrument.id,
                    'group_ids': [g.id for g in groups],
                    **df.to_dict(orient='list'),
                }

                s = session.scalars(
                    Obj.select(user).where(Obj.id == source['id'])
                ).first()
                if s is None:
                    obj_id = post_source(source, user_id, session)
                    obj_ids.append(obj_id)

                if len(df.index) > 0:
                    add_external_photometry(data_out, user)
                    log(f"Photometry committed to database for {source['id']}")
                else:
                    log(f"No photometry to commit to database for {source['id']}")
            log("Finished querying Fink for sources")

        elif payload['catalogName'] == 'LSXPS':
            telescope_name = 'Swift'
            telescope = session.scalars(
                Telescope.select(user).where(Telescope.nickname == 'Swift')
            ).first()
            if telescope is None:
                raise AttributeError(f'Expected a Telescope named {telescope_name}')
            instrument = telescope.instruments[0]
            log("Querying Swift for sources")
            obj_ids = fetch_swift_transients(instrument.id, user_id)
            log("Finished querying Swift for sources")

        elif payload['catalogName'] == 'Gaia':
            telescope_name = 'Gaia'
            telescope = session.scalars(
                Telescope.select(user).where(Telescope.nickname == 'Gaia')
            ).first()
            if telescope is None:
                raise AttributeError(f'Expected a Telescope named {telescope_name}')
            instrument = telescope.instruments[0]
            log("Querying Gaia for sources")
            obj_ids = fetch_gaia_transients(
                instrument.id, user_id, {'start_date': start_date, 'end_date': end_date}
            )
            log("Finished querying fink for sources")
        else:
            return AttributeError(f"Catalog name {payload['catalogName']} unknown")

        if len(obj_ids) == 0:
            catalog_query.status = 'completed: No new objects'
        else:
            catalog_query.status = f'completed: Added {",".join(obj_ids)}'
        session.commit()

    except Exception as e:
        return log(f"Unable to commit transient catalog: {e}")


class SwiftLSXPSQueryHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """
        ---
        description: |
            Get Swift LSXPS objects and post them as sources.
            Repeated posting will skip the existing source.
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  telescope_name:
                    required: false
                    type: integer
                    description: |
                      Name of telescope to assign this catalog to.
                      Use the same name as your nickname
                      for the Neil Gehrels Swift Observatory.
                      Defaults to Swift.

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

        telescope_name = data.get('telescope_name', 'Swift')

        with self.Session() as session:
            telescope = session.scalars(
                Telescope.select(session.user_or_token).where(
                    Telescope.nickname == telescope_name
                )
            ).first()
            if telescope is None:
                return self.error(f'Expected a Telescope named {telescope_name}')
            instrument = telescope.instruments[0]

            fetch_tr = functools.partial(
                fetch_swift_transients, instrument.id, self.associated_user_object.id
            )

            IOLoop.current().run_in_executor(None, fetch_tr)

            return self.success()


def fetch_swift_transients(instrument_id, user_id):
    """Fetch Swift XRT transients.
    instrument_id : int
        ID of the instrument
    user_id : int
        ID of the User
    """

    session = Session()
    obj_ids = []

    try:
        user = session.scalar(sa.select(User).where(User.id == user_id))

        group_ids = [g.id for g in user.accessible_groups]
        groups = session.scalars(
            Group.select(user).where(Group.id.in_(group_ids))
        ).all()

        with tempfile.TemporaryDirectory() as tmpdirname:
            q = uq.SXPSQuery(silent=True, cat='LSXPS', table='transients')
            q.addFilter(('Classification', '=', 1))
            q.submit()
            q.getDetails(byName=True)
            q.getLightCurves(byName=True, timeFormat='MJD', binning='obs')
            q.getSpectra(byName=True, specType='Discovery')
            q.saveSpectra(destDir=tmpdirname)

            obj_ids = []
            for transient in q.transientDetails.keys():
                ra = q.transientDetails[transient].pop('RA')
                dec = q.transientDetails[transient].pop('Decl')
                obj_name = (
                    q.transientDetails[transient].pop('IAUName').replace(" ", "-")
                )
                data = {'ra': ra, 'dec': dec, 'id': obj_name}
                s = session.scalars(Obj.select(user).where(Obj.id == obj_name)).first()
                if s is None:
                    obj_id = post_source(data, user_id, session)
                    obj_ids.append(obj_id)
                else:
                    obj_id = s.id

                if transient in q.lightCurves:
                    dfs = []
                    if 'PC_incbad' in q.lightCurves[transient]:
                        df1 = q.lightCurves[transient]['PC_incbad']
                        df1.rename(
                            columns={
                                'Time': 'mjd',
                                'Rate': 'flux',
                                'RatePos': 'fluxerr',
                            },
                            inplace=True,
                        )
                        drop_columns = list(
                            set(df1.columns.values)
                            - {
                                'mjd',
                                'ra',
                                'dec',
                                'flux',
                                'fluxerr',
                                'limiting_mag',
                                'filter',
                            }
                        )
                        df1.drop(
                            columns=drop_columns,
                            inplace=True,
                        )
                        dfs.append(df1)

                    if 'PCUL_incbad' in q.lightCurves[transient]:
                        df2 = q.lightCurves[transient]['PCUL_incbad']
                        df2.rename(
                            columns={'Time': 'mjd', 'Rate': 'fluxerr'}, inplace=True
                        )
                        drop_columns = list(
                            set(df2.columns.values)
                            - {
                                'mjd',
                                'ra',
                                'dec',
                                'flux',
                                'fluxerr',
                                'limiting_mag',
                                'filter',
                            }
                        )
                        df2.drop(
                            columns=drop_columns,
                            inplace=True,
                        )
                        dfs.append(df2)

                    df = pd.concat(dfs)
                    df['ra'] = ra
                    df['dec'] = dec
                    df['filter'] = 'swiftxrt'
                    df['magsys'] = 'ab'
                    df['zp'] = 0.0
                    df = df.replace({np.nan: None})

                    data_out = {
                        'obj_id': obj_id,
                        'instrument_id': instrument_id,
                        'group_ids': [g.id for g in user.accessible_groups],
                        **df.to_dict(orient='list'),
                    }

                    if len(df.index) > 0:
                        add_external_photometry(data_out, user)
                        log(f"Photometry committed to database for {obj_id}")
                    else:
                        log(f"No photometry to commit to database for {obj_id}")

                if transient in q.spectra:
                    filenames = glob.glob(f'{tmpdirname}/{transient}/interval*')
                    for filename in filenames:
                        attachment_name = filename.split("/")[-1]
                        with open(filename, 'rb') as f:
                            attachment_bytes = base64.b64encode(f.read())
                        comment = Comment(
                            text='Swift Detection Spectrum',
                            obj_id=obj_id,
                            attachment_bytes=attachment_bytes,
                            attachment_name=attachment_name,
                            author=user,
                            groups=groups,
                            bot=False,
                        )
                        session.add(comment)

            session.commit()
        return obj_ids

    except Exception as e:
        return log(f"Unable to commit Swift XRT transient catalog: {e}")


class GaiaPhotometricAlertsQueryHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """
        ---
        description: |
            Get Gaia Photometric Alert objects and post them as sources.
            Repeated posting will skip the existing source.
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  telescope_name:
                    required: false
                    type: string
                    description: |
                      Name of telescope to assign this catalog to.
                      Use the same name as your nickname
                      for Gaia. Defaults to Gaia.
                  startDate:
                    required: false
                    type: str
                    description: Arrow parsable string. Filter by start date.
                  endDate:
                    required: false
                    type: str
                    description: Arrow parsable string. Filter by end date.
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

        telescope_name = data.get('telescope_name', 'Gaia')
        start_date = data.get('startDate', None)
        end_date = data.get('endDate', None)

        if start_date is not None:
            start_date = Time(arrow.get(start_date.strip()).datetime)
        if end_date is not None:
            end_date = Time(arrow.get(end_date.strip()).datetime)

        payload = {'start_date': start_date, 'end_date': end_date}

        with self.Session() as session:
            telescope = session.scalars(
                Telescope.select(session.user_or_token).where(
                    Telescope.nickname == telescope_name
                )
            ).first()
            if telescope is None:
                return self.error(f'Expected a Telescope named {telescope_name}')
            instrument = telescope.instruments[0]

            fetch_tr = functools.partial(
                fetch_gaia_transients,
                instrument.id,
                self.associated_user_object.id,
                payload,
            )

            IOLoop.current().run_in_executor(None, fetch_tr)

            return self.success()


def fetch_gaia_transients(instrument_id, user_id, payload):
    """Fetch Gaia Photometric Alert transients.
    instrument_id : int
        ID of the instrument
    user_id : int
        ID of the User
    payload : dict
        Dictionary containing filtering parameters
    """

    session = Session()
    obj_ids = []

    lightcurve_url = "https://gsaweb.ast.cam.ac.uk/alerts/alert"
    alert_url = "http://gsaweb.ast.cam.ac.uk/alerts/alerts.csv"

    try:
        file_read = False
        nretries = 0

        while not file_read and nretries < 10:
            try:
                table = Table.read(alert_url, format='csv')
                file_read = True
            except FileNotFoundError:
                nretries = nretries + 1
                time.sleep(10)
        if not file_read:
            log('Failed to read Gaia alert catalog')
            return

        start_date = payload.get('start_date', None)
        end_date = payload.get('end_date', None)

        user = session.scalar(sa.select(User).where(User.id == user_id))

        group_ids = [g.id for g in user.accessible_groups]
        for row in table:
            name = row['#Name']
            ra, dec = row['RaDeg'], row['DecDeg']
            date = Time(row['Date'], format='iso')

            if start_date is not None:
                if date < start_date:
                    continue
            if end_date is not None:
                if date > end_date:
                    continue

            data = {'ra': ra, 'dec': dec, 'id': name}
            s = session.scalars(Obj.select(user).where(Obj.id == name)).first()
            if s is None:
                obj_id = post_source(data, user_id, session)
                obj_ids.append(obj_id)
            else:
                obj_id = s.id

            try:
                lc = Table.read(
                    f"{lightcurve_url}/{name}/lightcurve.csv/",
                    format='csv',
                    header_start=1,
                )
            except FileNotFoundError:
                log(f"Gaia alert {name} not found.")
                continue

            lc['mjd'] = Time(lc['JD(TCB)'], format='jd').mjd
            lc['ra'] = ra
            lc['dec'] = dec
            lc['limiting_mag'] = 20.7
            lc['filter'] = 'gaia::g'
            lc['magsys'] = 'ab'

            df = lc.to_pandas()
            df.rename(
                columns={
                    'averagemag': 'mag',
                },
                inplace=True,
            )
            df = df.replace({'null': np.nan})
            df = df.replace({'untrusted': np.nan})
            df = df.astype({"mag": float})
            df['magerr'] = (
                3.43779
                - (df['mag'] / 1.13759)
                + (df['mag'] / 3.44123) ** 2
                - (df['mag'] / 6.51996) ** 3
                + (df['mag'] / 11.45922) ** 4
            )
            drop_columns = list(
                set(df.columns.values)
                - {
                    'mjd',
                    'ra',
                    'dec',
                    'mag',
                    'magerr',
                    'limiting_mag',
                    'filter',
                    'magsys',
                }
            )
            df.drop(
                columns=drop_columns,
                inplace=True,
            )

            data_out = {
                'obj_id': obj_id,
                'instrument_id': instrument_id,
                'group_ids': group_ids,
                **df.to_dict(orient='list'),
            }

            if len(df.index) > 0:
                add_external_photometry(data_out, user)
                log(f"Photometry committed to database for {obj_id}")
            else:
                log(f"No photometry to commit to database for {obj_id}")

        return obj_ids
    except Exception as e:
        return log(f"Unable to commit Gaia Photometric Alert catalog: {e}")
