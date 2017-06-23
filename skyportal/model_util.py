import numpy as np
import pandas as pd
from baselayer.app.model_util import status, create_tables, drop_tables
from skyportal import models


def insert_test_data():
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

    s = models.Source(ra=353.36647, dec=33.646149, red_shift=0.063,
                      name='14gqr')
    s.comments = [models.Comment(text="No source at transient location to R>26"
                                 "in LRIS imaging", user=u),
                  models.Comment(text="Strong calcium lines have emerged.",
                                 user=u)]
    start = pd.Timestamp('2015-07-01')
    end = pd.Timestamp('2015-08-01')
    times = pd.to_datetime(np.linspace(start.value, end.value, 100))
    s.photometry = [models.Photometry(obs_time=t, mag=np.random.uniform(19, 22),
                                      e_mag=np.random.uniform(0, 0.5),
                                      lim_mag=np.random.uniform(22, 25),
                                      filter=np.random.choice(['R', 'G']))
                    for t in times]
    models.DBSession().add(s)
    models.DBSession().commit()

if __name__ == "__main__":
    insert_test_data()
