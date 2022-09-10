import base64
import functools
import glob
import numpy as np
import pandas as pd
from sqlalchemy.orm import sessionmaker, scoped_session
import sqlalchemy as sa
import swifttools.ukssdc.query as uq
import tempfile
from tornado.ioloop import IOLoop

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from baselayer.log import make_log

from .source import post_source
from .photometry import add_external_photometry
from ..base import BaseHandler
from ...models import (
    Comment,
    DBSession,
    Group,
    Obj,
    Telescope,
    User,
)

_, cfg = load_env()


log = make_log('api/catalogs')

Session = scoped_session(sessionmaker(bind=DBSession.session_factory.kw["bind"]))


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
                fetch_transients, instrument.id, self.associated_user_object.id
            )

            IOLoop.current().run_in_executor(None, fetch_tr)

            return self.success()


def fetch_transients(instrument_id, user_id):
    """Fetch Swift XRT transients.
    instrument_id : int
        ID of the instrument
    user_id : int
        ID of the User
    """

    session = Session()

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

    except Exception as e:
        return log(f"Unable to commit Swift XRT transient catalog: {e}")
