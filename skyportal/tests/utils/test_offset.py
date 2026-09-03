import astropy.units as u
from astropy.coordinates import SkyCoord

from skyportal.utils.offset import format_hmsdms, ngps_defaults


def test_format_hmsdms_scalar():
    sc = SkyCoord(ra=10 * u.deg, dec=20 * u.deg)
    assert format_hmsdms(sc, ":", " ") == "00:40:00.00 +20:00:00.00"
    # custom coordinate/column separators
    assert format_hmsdms(sc, "_", "|") == "00_40_00.00|+20_00_00.00"


def test_format_hmsdms_list():
    sc = SkyCoord(ra=[10, 200] * u.deg, dec=[20, -30] * u.deg)
    assert format_hmsdms(sc, ":", " ") == [
        "+00:40:00.00 +20:00:00.00",
        "+13:20:00.00 -30:00:00.00",
    ]


def test_ngps_defaults_numeric_mag_formatted():
    assert ngps_defaults(18.5, "R") == "2,3,PA,1.5,2.5,650,680,R,18.50,R,SNR 5,1"
    assert ngps_defaults(9, "g") == "2,3,PA,1.5,2.5,650,680,R,9.00,g,SNR 5,1"


def test_ngps_defaults_non_numeric_mag_passthrough():
    assert ngps_defaults("faint", "i") == "2,3,PA,1.5,2.5,650,680,R,faint,i,SNR 5,1"
