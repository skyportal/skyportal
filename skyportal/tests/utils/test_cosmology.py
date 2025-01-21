import pytest
from astropy import cosmology
from astropy import units as u

from skyportal.utils.cosmology import establish_cosmology


def test_default_cosmology_planck18():
    cosmo = establish_cosmology()
    assert cosmo.name == cosmology.Planck18.name


def test_named_cosmology():
    cfg = {"misc": {"cosmology": "WMAP9"}}
    cosmo = establish_cosmology(cfg=cfg)
    assert cosmo.name == "WMAP9"


def test_user_define_cosmology():
    cfg = {
        "misc": {
            "cosmology": {"H0": 65.0, "Om0": 0.3, "Ode0": 0.7, "name": "test_cosmo"}
        }
    }
    cosmo = establish_cosmology(cfg=cfg)
    assert cosmo.name == "test_cosmo"
    assert cosmo.H0 == 65.0 * u.km / (u.s * u.Mpc)


def test_bad_cosmology():
    # missing H0 and Om0
    cfg = {"misc": {"cosmology": {"Ode0": 1.0, "name": "test_cosmo"}}}

    with pytest.raises(RuntimeError):
        establish_cosmology(cfg=cfg)
