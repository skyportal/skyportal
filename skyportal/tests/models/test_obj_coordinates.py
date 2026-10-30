import pytest

from skyportal import models as sp_models


def test_galactic_coordinates_of_an_obj_without_a_position():
    """A positionless Obj serializes as null rather than raising.

    Candidate and source listings read these for every row, so one such Obj
    would otherwise take down the whole response.
    """
    obj = sp_models.Obj(id="no_position", ra=None, dec=None)
    assert obj.gal_lat_deg is None
    assert obj.gal_lon_deg is None


def test_galactic_coordinates_of_a_positioned_obj():
    obj = sp_models.Obj(id="positioned", ra=53.25295902434293, dec=-27.12756521722272)
    assert obj.gal_lon_deg == pytest.approx(222.4529, abs=1e-3)
    assert obj.gal_lat_deg == pytest.approx(-54.2111, abs=1e-3)
