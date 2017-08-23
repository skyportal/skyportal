import datetime
import os
import numpy as np
import pandas as pd

from baselayer.app.config import load_config
from baselayer.app.model_util import status, create_tables, drop_tables
from skyportal import models


if __name__ == "__main__":
    """Insert test data"""
    cfg = load_config()

    with status(f"Connecting to database {cfg['database']['database']}"):
        models.init_db(**cfg['database'])

    with status("Dropping all tables"):
        drop_tables()

    with status("Creating tables"):
        create_tables()

    for model in models.Base.metadata.tables:
        print('    -', model)

    with status(f"Creating permissions"):
        manage_users = models.ACL(id='Manage users')
        manage_sources = models.ACL(id='Manage sources')
        manage_groups = models.ACL(id='Manage groups')
        post_comments = models.ACL(id='Comment')

        super_admin = models.Role(id='Super admin', acls=[manage_users,
                                                          manage_groups,
                                                          manage_sources,
                                                          post_comments])
        group_admin = models.Role(id='Group admin', acls=[manage_sources,
                                                          post_comments])
        full = models.Role(id='Full user', acls=[post_comments])
        models.DBSession().add_all([super_admin, group_admin, full])

    with status(f"Creating dummy users"):
        g = models.Group(name='Stream A')
        super_admin_user = models.User(username='testuser@cesium-ml.org',
                                       roles=[super_admin])
        group_admin_user = models.User(username='groupadmin@cesium-ml.org',
                                       roles=[group_admin])
        models.DBSession().add_all(
            [models.GroupUser(group=g, user=super_admin_user, admin=True),
             models.GroupUser(group=g, user=group_admin_user, admin=True)]
        )
        full_user = models.User(username='fulluser@cesium-ml.org',
                                roles=[full], groups=[g])
        models.DBSession().add_all([super_admin_user, group_admin_user,
                                    full_user])

    with status("Creating dummy instruments"):
        t1 = models.Telescope(name='Palomar 1.5m', nickname='P60',
                             lat=33.3633675, lon=-116.8361345, elevation=1870,
                             diameter=1.5)
        i1 = models.Instrument(telescope=t1, name='P60 Camera', type='phot',
                              band='optical')

        t2 = models.Telescope(name='Nordic Optical Telescope', nickname='NOT',
                             lat=28.75, lon=17.88, elevation=2327,
                             diameter=2.56)
        i2 = models.Instrument(telescope=t2, name='ALFOSC', type='both',
                              band='optical')
        models.DBSession().add_all([i1, i2])

    with status("Creating dummy sources"):
        SOURCES = [{'id': '14gqr', 'ra': 353.36647, 'dec': 33.656149, 'red_shift': 0.063,
                    'comments': ["No source at transient location to R>26 in LRIS imaging",
                                 "Strong calcium lines have emerged."]},
                   {'id': '16fil', 'ra': 322.718872, 'dec': 27.574113, 'red_shift': 0.0,
                    'comments': ["Frogs in the pond", "The eagle has landed"]}]

        for source_info in SOURCES:
            comments = source_info.pop('comments')

            s = models.Source(**source_info, groups=[g])
            s.comments = [models.Comment(text=comment, user=group_admin_user)
                          for comment in comments]

            phot_file = os.path.join(os.path.dirname(__file__), 'tests', 'data',
                                     'phot.csv')
            phot_data = pd.read_csv(phot_file)
            s.photometry = [models.Photometry(instrument=i1, **row)
                            for j, row in phot_data.iterrows()]

            spec_file = os.path.join(os.path.dirname(__file__), 'tests', 'data',
                                     'spec.csv')
            spec_data = pd.read_csv(spec_file)
            s.spectra = [models.Spectrum(instrument_id=int(i),
                                         observed_at=datetime.datetime(2014, 10, 24),
                                         wavelengths=df.wavelength,
                                         fluxes=df.flux, errors=None)
                         for i, df in spec_data.groupby('instrument_id')]

            models.DBSession().add(s)
