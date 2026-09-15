from types import SimpleNamespace

import astropy.units as u
from astropy.coordinates import SkyCoord

from skyportal.facility_apis.soar import SOAR_GHTS_Request, SOAR_TripleSpec_Request

SOURCE_RA, SOURCE_DEC = 9.7139, -16.1090


def _request(**payload):
    base = {
        "observation_mode": "NORMAL",
        "instrument_type": "SOAR_GHTS_REDCAM",
        "instrument_mode": ["GHTS_R_400m2_2x2"],
        "exposure_time": 300.0,
        "exposure_counts": 1,
        "maximum_airmass": 2.0,
        "minimum_lunar_distance": 30.0,
        "priority": 1.0,
        "start_date": "2026-09-28T00:00:00",
        "end_date": "2026-09-30T00:00:00",
    }
    return SimpleNamespace(
        obj=SimpleNamespace(id="ZTF26ablnnlb", ra=SOURCE_RA, dec=SOURCE_DEC),
        payload={**base, **payload},
        allocation=SimpleNamespace(altdata={"PROPOSAL_ID": "SOAR-2026B-001"}),
    )


def _offset_star(dra_arcsec, ddec_arcsec):
    """A star that sits `dra`/`ddec` away from the source, as the finder reports it."""
    source = SkyCoord(SOURCE_RA, SOURCE_DEC, unit="deg")
    star = source.spherical_offsets_by(-dra_arcsec * u.arcsec, -ddec_arcsec * u.arcsec)
    return {
        "name": "ZTF26ablnnlb_g1",
        "ra": star.ra.deg,
        "dec": star.dec.deg,
        "dra_arcsec": dra_arcsec,
        "ddec_arcsec": ddec_arcsec,
    }


def _configs(requestgroup):
    return requestgroup["requests"][0]["configurations"]


def test_without_an_offset_star_the_source_is_the_target():
    groups = SOAR_GHTS_Request(_request()).requestgroup
    config = _configs(groups)[0]
    assert config["target"]["ra"] == SOURCE_RA
    assert config["target"]["dec"] == SOURCE_DEC
    extra = config["instrument_configs"][0]["extra_params"]
    assert extra["offset_ra"] == 0 and extra["offset_dec"] == 0


def test_the_offsets_carry_the_slit_from_the_star_onto_the_source():
    """The whole point: acquire the star, offset, land on the source."""
    star = _offset_star(dra_arcsec=12.5, ddec_arcsec=-7.25)
    config = _configs(SOAR_GHTS_Request(_request(), offset_star=star).requestgroup)[0]

    assert config["target"]["name"] == star["name"]
    assert config["target"]["ra"] == star["ra"]

    extra = config["instrument_configs"][0]["extra_params"]
    landed = SkyCoord(star["ra"], star["dec"], unit="deg").spherical_offsets_by(
        extra["offset_ra"] * u.arcsec, extra["offset_dec"] * u.arcsec
    )
    source = SkyCoord(SOURCE_RA, SOURCE_DEC, unit="deg")
    assert landed.separation(source).arcsec < 0.01


def test_calibrations_are_taken_at_the_science_pointing():
    star = _offset_star(dra_arcsec=12.5, ddec_arcsec=-7.25)
    configs = _configs(
        SOAR_GHTS_Request(
            _request(include_calibrations=True), offset_star=star
        ).requestgroup
    )
    science = next(c for c in configs if c["type"] == "SPECTRUM")
    arcs = [c for c in configs if c["type"] == "ARC"]
    assert arcs
    for arc in arcs:
        assert (
            arc["instrument_configs"][0]["extra_params"]
            == science["instrument_configs"][0]["extra_params"]
        )


def test_triplespec_keeps_its_rotator_angle_when_offsetting():
    star = _offset_star(dra_arcsec=3.0, ddec_arcsec=4.0)
    request = _request(instrument_mode="fowler16_coadds1")
    config = _configs(SOAR_TripleSpec_Request(request, offset_star=star).requestgroup)[
        0
    ]
    extra = config["instrument_configs"][0]["extra_params"]
    assert extra["rotator_angle"] == 90
    assert extra["offset_ra"] == 3.0 and extra["offset_dec"] == 4.0
