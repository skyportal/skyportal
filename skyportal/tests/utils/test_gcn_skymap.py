import ligo.skymap.moc
import numpy as np

from skyportal.utils.gcn import from_cone, from_ellipse, from_polygon


def _arrays(skymap):
    return (
        np.array(skymap["uniq"], dtype=np.int64),
        np.array(skymap["probdensity"], dtype=float),
    )


def _integral(skymap):
    # the probability density integrated over the sphere should be ~1
    uniq, prob = _arrays(skymap)
    return float(np.sum(prob * ligo.skymap.moc.uniq2pixarea(uniq)))


def _assert_valid_skymap(skymap, name):
    assert skymap["localization_name"] == name
    uniq, prob = _arrays(skymap)
    assert len(uniq) == len(prob) > 0
    assert np.all(np.isfinite(prob)) and np.all(prob > 0)
    assert np.all(np.diff(uniq) > 0)  # uniq sorted ascending and unique
    assert abs(_integral(skymap) - 1.0) < 1e-6


def test_from_cone():
    skymap = from_cone(197.45, -23.38, 2.0)
    _assert_valid_skymap(skymap, "197.45000_-23.38000_2.00000")
    # a Gaussian cone is peaked, so the density spans a meaningful range
    _, prob = _arrays(skymap)
    assert prob.max() > prob.min() * 2


def test_from_polygon():
    # a ~2 deg square around (10, 10)
    polygon = [(9.0, 9.0), (11.0, 9.0), (11.0, 11.0), (9.0, 11.0)]
    skymap = from_polygon("square", polygon)
    _assert_valid_skymap(skymap, "square")
    # density is uniform across the polygon
    _, prob = _arrays(skymap)
    np.testing.assert_allclose(prob, prob[0])


def test_from_ellipse():
    skymap = from_ellipse("ellipse", 30.0, -10.0, 3.0, 1.5, 45.0)
    _assert_valid_skymap(skymap, "ellipse")
    _, prob = _arrays(skymap)
    np.testing.assert_allclose(prob, prob[0])
