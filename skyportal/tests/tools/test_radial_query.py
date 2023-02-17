import numpy as np
import pytest
from uuid import uuid4
from astropy import coordinates as ap_coord
from astropy import units as u
from skyportal import models as sp_models
import conesearch_alchemy as ca


@pytest.mark.parametrize('n', [100, 1000, 10000])
@pytest.mark.flaky(reruns=3)
def test_radial_query(n):

    # generate the points
    rng = np.random.RandomState(8675309)  # /Jenny
    ras = rng.uniform(0, 360, n)
    decs = np.rad2deg(np.arcsin(rng.uniform(-1, 1, n)))
    ids = np.asarray([uuid4().hex for _ in range(n)])

    # save them to the database
    point_cloud = [
        sp_models.Obj(id=id, ra=r, dec=d) for id, r, d in zip(ids, ras, decs)
    ]
    sp_models.DBSession().add_all(point_cloud)
    sp_models.DBSession().commit()

    # generate the truth
    coord = ap_coord.SkyCoord(ra=ras, dec=decs, unit='deg')

    # take the test point to be the first point
    sep = coord.separation(coord[0])

    # find the coordinates where the separation is less than 1 degree
    indices = np.argwhere(sep <= 1 * u.degree)
    indices = indices.reshape(indices.size)

    # the answer
    matching_ids = set(ids[indices])

    # issue the query on the db
    db_ids = (
        sp_models.DBSession()
        .query(sp_models.Obj.id)
        .filter(
            sp_models.Obj.within(
                ca.Point(ra=coord[0].ra.deg, dec=coord[0].dec.deg), 1.0
            )
        )
    )

    db_ids = {i[0] for i in db_ids}
    db_ids &= set(ids)

    assert matching_ids == db_ids
