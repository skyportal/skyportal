import datetime
import os
from pathlib import Path
import shutil
import numpy as np
import pandas as pd
from sqlalchemy.exc import IntegrityError

from baselayer.app.env import load_env
from baselayer.app.model_util import status, create_tables, drop_tables
from social_tornado.models import TornadoStorage
from skyportal.models import (init_db, Base, DBSession, ACL, Comment,
                              Instrument, Group, GroupUser, Photometry, Role,
                              Source, Spectrum, Telescope, Thumbnail, User,
                              Token)


def add_super_user(username):
    """Initializes a super user with full permissions."""
    setup_permissions()  # make sure permissions already exist
    super_user = User.query.filter(User.username == username).first()
    if super_user is None:
        super_user = User(username=username)
        social = TornadoStorage.user.create_social_auth(super_user,
                                                        super_user.username,
                                                        'google-oauth2')
    admin_role = Role.query.get('Super admin')
    if admin_role not in super_user.roles:
        super_user.roles.append(admin_role)
    DBSession().add(super_user)
    DBSession().commit()


def setup_permissions():
    """Create default ACLs/Roles needed by application.

    If a given ACL or Role already exists, it will be skipped."""
    all_acl_ids = ['Become user', 'Comment', 'Manage users', 'Manage sources',
                   'Manage groups', 'Upload data', 'System admin']
    all_acls = [ACL.create_or_get(a) for a in all_acl_ids]
    DBSession().add_all(all_acls)
    DBSession().commit()

    role_acls = {
        'Super admin': all_acl_ids,
        'Group admin': ['Comment', 'Manage sources', 'Upload data'],
        'Full user': ['Comment', 'Upload data'],
        'View only': []
    }

    for r, acl_ids in role_acls.items():
        role = Role.create_or_get(r)
        role.acls = [ACL.query.get(a) for a in acl_ids]
        DBSession().add(role)
    DBSession().commit()


def create_token(group_id, permissions=[], created_by_id=None, name=None):
    group = Group.query.get(group_id)
    t = Token(permissions=permissions, created_by_id=created_by_id,
              name=name)
    t.groups.append(group)
    if created_by_id:
        u = User.query.get(created_by_id)
        u.tokens.append(t)
        t.created_by = u
        DBSession().add(u)
    DBSession().add(t)
    DBSession().commit()
    return t.id


def load_demo_data(cfg, clear=False):
    '''Populate DB with demo data.

    Parameters
    ----------
    cfg : dict
        Config dict from baselayer.app.config.load_config
    '''
    basedir = Path(os.path.dirname(__file__))/'..'

    with status(f"Connecting to database {cfg['database']['database']}"):
        init_db(**cfg['database'])

    if clear:
        with status("Dropping all tables"):
            drop_tables()

        with status("Creating tables"):
            create_tables()

        for model in Base.metadata.tables:
            print('    -', model)

        with status(f"Creating permissions"):
            setup_permissions()

    with status(f"Creating dummy users"):
        g = Group.query.filter(Group.name == 'Stream A').first()
        if not g:
            g = Group(name='Stream A')
        super_admin_user = User.query.filter(User.username == 'testuser@cesium-ml.org').first()
        group_admin_user = User.query.filter(User.username == 'groupadmin@cesium-ml.org').first()
        if not super_admin_user: # Dummy users not yet added to DB
            super_admin_user = User(username='testuser@cesium-ml.org',
                                    role_ids=['Super admin'])
            DBSession.add(super_admin_user)
            DBSession().add(GroupUser(group=g, user=super_admin_user, admin=True))
            DBSession.commit()
        if not group_admin_user:
            group_admin_user = User(username='groupadmin@cesium-ml.org',
                                    role_ids=['Super admin'])
            DBSession.add(group_admin_user)
            DBSession.add(GroupUser(group=g, user=group_admin_user, admin=True))
            DBSession.commit()
            full_user = User(username='fulluser@cesium-ml.org',
                             role_ids=['Full user'], groups=[g])
            view_only_user = User(username='viewonlyuser@cesium-ml.org',
                                  role_ids=['View only'], groups=[g])
            DBSession().add_all([super_admin_user, group_admin_user,
                                 full_user, view_only_user])

            for u in [super_admin_user, group_admin_user, full_user, view_only_user]:
                DBSession().add(TornadoStorage.user.create_social_auth(u, u.username,
                                                                       'google-oauth2'))
            DBSession.commit()

    with status("Creating dummy instruments"):
        t1 = Telescope.query.filter(Telescope.name == 'Palomar 1.5m').first()
        if not t1:
            t1 = Telescope(name='Palomar 1.5m', nickname='P60',
                           lat=33.3633675, lon=-116.8361345, elevation=1870,
                           diameter=1.5)
            i1 = Instrument(telescope=t1, name='P60 Camera', type='phot',
                            band='optical')

            t2 = Telescope(name='Nordic Optical Telescope', nickname='NOT',
                           lat=28.75, lon=17.88, elevation=2327,
                           diameter=2.56)
            i2 = Instrument(telescope=t2, name='ALFOSC', type='both',
                            band='optical')
            DBSession().add_all([i1, i2])
            try:
                DBSession.commit()
            except IntegrityError:
                print('Dummy instruments already in DB... rolling back.')
                DBSession.rollback()
        else:
            print('Dummy instruments already added to DB.')

    with status("Creating dummy sources"):
        if not Source.query.get('14gqr'):
            SOURCES = [{'id': '14gqr', 'ra': 353.36647, 'dec': 33.646149, 'redshift': 0.063,
                        'comments': ["No source at transient location to R>26 in LRIS imaging",
                                     "Strong calcium lines have emerged."]},
                       {'id': '16fil', 'ra': 322.718872, 'dec': 27.574113, 'redshift': 0.0,
                        'comments': ["Frogs in the pond", "The eagle has landed"]}]

            (basedir/'static/thumbnails').mkdir(parents=True, exist_ok=True)
            for source_info in SOURCES:
                comments = source_info.pop('comments')

                s = Source(**source_info, groups=[g])
                s.comments = [Comment(text=comment, author=group_admin_user.username)
                              for comment in comments]

                phot_file = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                         'skyportal', 'tests', 'data',
                                         'phot.csv')
                phot_data = pd.read_csv(phot_file)
                s.photometry = [Photometry(instrument=i1, **row)
                                for j, row in phot_data.iterrows()]

                spec_file = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                         'skyportal', 'tests', 'data',
                                         'spec.csv')
                spec_data = pd.read_csv(spec_file)
                s.spectra = [Spectrum(instrument_id=int(i),
                                      observed_at=datetime.datetime(2014, 10, 24),
                                      wavelengths=df.wavelength,
                                      fluxes=df.flux, errors=None)
                             for i, df in spec_data.groupby('instrument_id')]
                DBSession().add(s)
                try:
                    DBSession.commit()
                except IntegrityError:
                    print('Dummy users already in DB... rolling back.')
                    DBSession.rollback()
                    break

                for ttype in ['new', 'ref', 'sub']:
                    fname = f'{s.id}_{ttype}.png'
                    t = Thumbnail(type=ttype, photometry_id=s.photometry[0].id,
                                  file_uri=f'static/thumbnails/{fname}',
                                  public_url=f'/static/thumbnails/{fname}')
                    DBSession().add(t)
                    shutil.copy(basedir/f'skyportal/tests/data/{fname}', basedir/'static/thumbnails/')

                s.add_linked_thumbnails()
        else:
            print('Dummy sources already added to DB.')
