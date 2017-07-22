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

    USERNAME = 'testuser@gmail.com'
    with status(f"Creating dummy user: {USERNAME}... "):
        u = models.User(username=USERNAME, email=USERNAME)
        models.DBSession().add(u)
        models.DBSession().commit()

    with status(f"Creating dummy source 14gqr"):
        s = models.Source(ra=353.36647, dec=33.646149, red_shift=0.063,
                          id='14gqr')
        s.comments = [models.Comment(text="No source at transient location to"
                                     "R>26 in LRIS imaging", user=u),
                      models.Comment(text="Strong calcium lines have emerged.",
                                     user=u)]

        t = models.Telescope(name='Palomar 1.5m', nickname='P60',
                             lat=33.3633675, lon=-116.8361345, elevation=1870,
                             diameter=1.5)
        i = models.Instrument(telescope=t, name='P60 Camera', type='phot',
                              band='optical')

        phot_file = os.path.join(os.path.dirname(__file__), 'tests', 'data',
                                 'phot.csv')
        phot_data = pd.read_csv(phot_file)
        s.photometry = [models.Photometry(instrument=i, **row)
                        for j, row in phot_data.iterrows()]

        spec_file = os.path.join(os.path.dirname(__file__), 'tests', 'data',
                                 'spec.csv')
        spec_data = np.loadtxt(spec_file)
        s.spectra = [models.Spectrum(instrument=i,
                                     observed_at=datetime.datetime(2014, 10, 24),
                                     wavelengths=spec_data[:, 0],
                                     fluxes=spec_data[:, 1], errors=None)]

        models.DBSession().add(s)
        models.DBSession().commit()
