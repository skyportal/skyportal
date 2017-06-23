import os
import numpy as np
import pandas as pd

from baselayer.app import cfg
from baselayer.app.model_util import status, create_tables, drop_tables
from skyportal import models


if __name__ == "__main__":
    """Insert test data"""
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
                          name='14gqr')
        s.comments = [models.Comment(text="No source at transient location to"
                                     "R>26 in LRIS imaging", user=u),
                      models.Comment(text="Strong calcium lines have emerged.",
                                     user=u)]
        phot_file = os.path.join(os.path.dirname(__file__), 'tests', 'data',
                                 'phot.csv')
        phot_data = pd.read_csv(phot_file)
        s.photometry = [models.Photometry(**row)
                        for i, row in phot_data.iterrows()]
                        
        models.DBSession().add(s)
        models.DBSession().commit()
