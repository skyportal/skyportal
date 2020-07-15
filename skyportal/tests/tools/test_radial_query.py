import numpy as np
import pytest
from uuid import uuid4
from astropy.utils.misc import NumpyRNGContext
from astropy.coordinates import SkyCoord
from astropy import units as u
from skyportal.models import Obj, DBSession
from healpix_alchemy.point import Point


@pytest.mark.parametrize('n', [100, 1000, 10000])
def test_radial_query(n):

    # generate the points
    with NumpyRNGContext(8675309):  # /Jenny
        ras = np.random.uniform(0, 360, n)
        decs = np.rad2deg(np.arcsin(np.random.uniform(-1, 1, n)))
    ids = np.asarray([uuid4().hex for _ in range(n)])

    # save them to the database
    point_cloud = [Obj(id=id, ra=r, dec=d) for id, r, d in zip(ids, ras, decs)]
    DBSession().add_all(point_cloud)
    DBSession().commit()

    # generate the truth
    coord = SkyCoord(ra=ras, dec=decs, unit='deg')

    # take the test point to be the first point
    sep = coord.separation(coord[0])

    # find the coordinates where the separation is less than 1 degree
    indices = np.argwhere(sep <= 1 * u.degree)
    indices = indices.reshape(indices.size)

    # the answer
    matching_ids = set(ids[indices])

    # issue the query on the db
    db_ids = DBSession().query(Obj.id).filter(
        Obj.point.within(Point(ra=coord[0].ra.deg, dec=coord[0].dec.deg), 1.)
    ).all()

    db_ids = [i[0] for i in db_ids]
    db_ids = set(filter(lambda i: i in ids, db_ids))

    assert matching_ids == db_ids
