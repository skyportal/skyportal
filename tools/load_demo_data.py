import datetime
import os
import subprocess
import base64
from pathlib import Path
import shutil
import pandas as pd
import signal

from baselayer.app.env import load_env
from baselayer.app.model_util import status, create_tables, drop_tables
from social_tornado.models import TornadoStorage
from skyportal.models import init_db, Base, DBSession, Source, User
from skyportal.model_util import setup_permissions, create_token
from skyportal.tests import api
from baselayer.tools.test_frontend import verify_server_availability


if __name__ == "__main__":
    """Insert test data"""
    env, cfg = load_env()
    basedir = Path(os.path.dirname(__file__))/'..'

    with status(f"Connecting to database {cfg['database']['database']}"):
        init_db(**cfg['database'])

    with status("Dropping all tables"):
        drop_tables()

    with status("Creating tables"):
        create_tables()

    for model in Base.metadata.tables:
        print('    -', model)

    with status(f"Creating permissions"):
        setup_permissions()

    with status(f"Creating dummy users"):
        super_admin_user = User(username='testuser@cesium-ml.org',
                                role_ids=['Super admin'])
        group_admin_user = User(username='groupadmin@cesium-ml.org',
                                role_ids=['Super admin'])
        full_user = User(username='fulluser@cesium-ml.org',
                         role_ids=['Full user'])
        view_only_user = User(username='viewonlyuser@cesium-ml.org',
                              role_ids=['View only'])
        DBSession().add_all([super_admin_user, group_admin_user,
                             full_user, view_only_user])

        for u in [super_admin_user, group_admin_user, full_user, view_only_user]:
            DBSession().add(TornadoStorage.user.create_social_auth(u, u.username,
                                                                   'google-oauth2'))

    with status("Launching web app & executing API calls"):
        web_client = subprocess.Popen(['make', 'run'],
                                      cwd=basedir, preexec_fn=os.setsid)

        server_url = f"http://localhost:{cfg['ports.app']}"
        print()
        print(f'Waiting for server to appear at {server_url}...')

        try:
            verify_server_availability(server_url)
            print('App running - continuing with API calls')
            with status("Creating token"):
                token = create_token(['Manage groups', 'Manage sources', 'Upload data',
                                      'Comment', 'Manage users'],
                                     super_admin_user.id,
                                     'load_demo_data token')

            with status("Creating dummy group & adding users"):
                response_status, data = api(
                    'POST',
                    'groups',
                    data={'name': 'Stream A',
                          'group_admins': [super_admin_user.username,
                                           group_admin_user.username]},
                    token=token)
                assert response_status == 200
                assert data['status'] == 'success'
                group_id = data['data']['id']

                for u in [view_only_user, full_user]:
                    response_status, data = api(
                        'POST',
                        f'groups/{group_id}/users/{u.username}',
                        data={'admin': False},
                        token=token)
                    assert response_status == 200
                    assert data['status'] == 'success'

            with status("Creating dummy instruments"):
                response_status, data = api('POST', 'telescope',
                                            data={'name': 'Palomar 1.5m',
                                                  'nickname': 'P60',
                                                  'lat': 33.3633675,
                                                  'lon': -116.8361345,
                                                  'elevation': 1870,
                                                  'diameter': 1.5,
                                                  'group_ids': [group_id]
                                            },
                                            token=token)
                assert response_status == 200
                assert data['status'] == 'success'
                telescope1_id = data['data']['id']

                response_status, data = api('POST', 'instrument',
                                            data={'name': 'P60 Camera',
                                                  'type': 'phot',
                                                  'band': 'optical',
                                                  'telescope_id': telescope1_id
                                            },
                                            token=token)
                assert response_status == 200
                assert data['status'] == 'success'
                instrument1_id = data['data']['id']

                response_status, data = api('POST', 'telescope',
                                            data={'name': 'Nordic Optical Telescope',
                                                  'nickname': 'NOT',
                                                  'lat': 28.75,
                                                  'lon': 17.88,
                                                  'elevation': 1870,
                                                  'diameter': 2.56,
                                                  'group_ids': [group_id]
                                            },
                                            token=token)
                assert response_status == 200
                assert data['status'] == 'success'
                telescope2_id = data['data']['id']

                response_status, data = api('POST', 'instrument',
                                            data={'name': 'ALFOSC',
                                                  'type': 'both',
                                                  'band': 'optical',
                                                  'telescope_id': telescope2_id
                                            },
                                            token=token)
                assert response_status == 200
                assert data['status'] == 'success'

            with status("Creating dummy sources"):
                SOURCES = [{'id': '14gqr', 'ra': 353.36647, 'dec': 33.646149,
                            'redshift': 0.063, 'group_ids': [group_id],
                            'comments': ["No source at transient location to R>26 in LRIS imaging",
                                         "Strong calcium lines have emerged."]},
                           {'id': '16fil', 'ra': 322.718872, 'dec': 27.574113,
                            'redshift': 0.0, 'group_ids': [group_id],
                            'comments': ["Frogs in the pond", "The eagle has landed"]}]

                (basedir/'static/thumbnails').mkdir(parents=True, exist_ok=True)
                for source_info in SOURCES:
                    comments = source_info.pop('comments')

                    response_status, data = api('POST', 'sources',
                                                data=source_info,
                                                token=token)
                    assert response_status == 200
                    assert data['data']['id'] == source_info['id']

                    for comment in comments:
                        response_status, data = api('POST', 'comment',
                                                    data={'source_id': source_info['id'],
                                                          'text': comment},
                                                    token=token)
                        assert response_status == 200

                    phot_file = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                             'skyportal', 'tests', 'data',
                                             'phot.csv')
                    phot_data = pd.read_csv(phot_file)
                    for j, row in phot_data.iterrows():
                        response_status, data = api('POST', 'photometry',
                                                    data={'source_id': source_info['id'],
                                                          'time_format': 'iso',
                                                          'time_scale': 'utc',
                                                          'instrument_id': instrument1_id,
                                                          **row
                                                    },
                                                    token=token)
                        assert response_status == 200
                        assert data['status'] == 'success'

                    spec_file = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                             'skyportal', 'tests', 'data',
                                             'spec.csv')
                    spec_data = pd.read_csv(spec_file)
                    for i, df in spec_data.groupby('instrument_id'):
                        response_status, data = api(
                            'POST', 'spectrum',
                            data={'source_id': source_info['id'],
                                  'observed_at': str(datetime.datetime(2014, 10, 24)),
                                  'instrument_id': 1,
                                  'wavelengths': df.wavelength.tolist(),
                                  'fluxes': df.flux.tolist()
                            },
                            token=token)
                        assert response_status == 200
                        assert data['status'] == 'success'

                    for ttype in ['new', 'ref', 'sub']:
                        fname = f'{source_info["id"]}_{ttype}.png'
                        fpath = basedir/f'skyportal/tests/data/{fname}'
                        thumbnail_data = base64.b64encode(
                            open(os.path.abspath(fpath), 'rb').read())
                        response_status, data = api('POST', 'thumbnail',
                                                    data={'source_id': source_info['id'],
                                                          'data': thumbnail_data,
                                                          'ttype': ttype
                                                    },
                                                    token=token)
                        assert response_status == 200
                        assert data['status'] == 'success'

                    source = Source.query.get(source_info['id'])
                    source.add_linked_thumbnails()
        except Exception as e:
            print(e)
            raise
        finally:
            print('Terminating web app')
            os.killpg(os.getpgid(web_client.pid), signal.SIGTERM)
