from astropy import cosmology
from astropy import units as u

from skyportal.utils.cosmology import establish_cosmology

fallback_cosmology = cosmology.Planck18_arXiv_v2


def test_default_cosmology():
    cosmo = establish_cosmology(cfg={}, fallback_cosmology=fallback_cosmology)
    assert cosmo.name == fallback_cosmology.name


def test_named_cosmology():
    cfg = {"misc": {"cosmology": "WMAP9"}}
    cosmo = establish_cosmology(cfg=cfg, fallback_cosmology=fallback_cosmology)
    assert cosmo.name == "WMAP9"


def test_user_define_cosmology():
    cfg = {
        "misc": {
            "cosmology": {"H0": 65.0, "Om0": 0.3, "Ode0": 0.7, "name": 'test_cosmo'}
        }
    }
    cosmo = establish_cosmology(cfg=cfg, fallback_cosmology=fallback_cosmology)
    assert cosmo.name == 'test_cosmo'
    assert cosmo.H0 == 65.0 * u.km / (u.s * u.Mpc)


def test_bad_cosmology():
    # missing H0 and Om0
    cfg = {"misc": {"cosmology": {"Ode0": 1.0, "name": 'test_cosmo'}}}

    cosmo = establish_cosmology(cfg=cfg, fallback_cosmology=fallback_cosmology)
    assert cosmo.name == fallback_cosmology.name
