import uuid
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
import numpy.testing as npt
import pytest
import requests
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.table import Table
from requests.exceptions import ConnectionError, HTTPError, Timeout

from skyportal.models import Photometry
from skyportal.tests import api
from skyportal.utils import offset
from skyportal.utils.offset import (
    IRSA_SEARCH_TIMEOUT,
    _calculate_best_position_for_offset_stars,
    get_finding_chart,
    get_nearby_offset_stars,
    get_ztfref_url,
)


def test_calculate_best_position_no_photometry():
    ra, dec = _calculate_best_position_for_offset_stars(
        [], fallback=(10.0, -20.0), how="snr2", max_offset=0.5, sigma_clip=4.0
    )
    npt.assert_almost_equal(ra, 10)
    npt.assert_almost_equal(dec, -20)


@pytest.mark.flaky(reruns=2)
def test_calculate_position_with_evil_inputs(
    upload_data_token, view_only_token, ztf_camera, public_group
):
    ra, dec = 10.5, -20.8
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={"id": obj_id, "ra": ra, "dec": dec, "group_ids": [public_group.id]},
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id

    n_phot = 10
    mjd = 58000.0 + np.arange(n_phot)
    flux = np.zeros_like(mjd)
    fluxerr = 1e-6 + np.random.random(n_phot)
    filters = ["ztfg"] * n_phot
    ras = ra + np.cos(np.radians(dec)) * np.random.randn(n_phot) / (10 * 3600)
    decs = dec + np.random.randn(n_phot) / (10 * 3600)
    dec_unc = np.zeros_like(mjd)

    med_ra, med_dec = np.median(ras), np.median(decs)

    # valid request with zero-flux sources and astrometry with zero uncertainty
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": obj_id,
            "mjd": list(mjd),
            "instrument_id": ztf_camera.id,
            "flux": list(flux),
            "fluxerr": list(fluxerr),
            "filter": list(filters),
            "ra": list(ras),
            "dec": list(decs),
            "magsys": "ab",
            "zp": 25.0,
            "dec_unc": list(dec_unc),
            "ra_unc": 0.2,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]["ids"]) == n_phot

    removed_kwargs = ["instrument_name", "groups", "magsys", "zp", "snr"]
    phot_list = []
    for photometry_id in data["data"]["ids"]:
        status, data = api(
            "GET", f"photometry/{photometry_id}?format=flux", token=upload_data_token
        )
        assert status == 200
        assert data["status"] == "success"
        for key in removed_kwargs:
            data["data"].pop(key)

        phot_list.append(Photometry(**data["data"]))

    ra_calc_snr, dec_calc_snr = _calculate_best_position_for_offset_stars(
        phot_list, fallback=(ra, dec), how="snr2", max_offset=0.5, sigma_clip=4.0
    )
    # make sure we get back a the median position
    npt.assert_almost_equal(ra_calc_snr, med_ra, decimal=10)
    npt.assert_almost_equal(dec_calc_snr, med_dec, decimal=10)

    ra_calc_err, dec_calc_err = _calculate_best_position_for_offset_stars(
        phot_list, fallback=(ra, dec), how="invvar", max_offset=0.5, sigma_clip=4.0
    )
    # make sure we get back a median position
    npt.assert_almost_equal(ra_calc_err, med_ra, decimal=10)
    npt.assert_almost_equal(dec_calc_err, med_dec, decimal=10)


@pytest.mark.flaky(reruns=2)
def test_calculate_best_position_with_photometry(
    upload_data_token, view_only_token, ztf_camera, public_group
):
    ra, dec = 10.5, -20.8
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={"id": obj_id, "ra": ra, "dec": dec, "group_ids": [public_group.id]},
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id

    n_phot = 10
    mjd = 58000.0 + np.arange(n_phot)
    flux = float(n_phot) + np.random.random(n_phot) * 100
    fluxerr = 1e-6 + np.random.random(n_phot)
    filters = ["ztfg"] * n_phot
    ras = ra + np.cos(np.radians(dec)) * np.random.randn(n_phot) / (10 * 3600)
    decs = dec + np.random.randn(n_phot) / (10 * 3600)

    # valid request
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": obj_id,
            "mjd": list(mjd),
            "instrument_id": ztf_camera.id,
            "flux": list(flux),
            "fluxerr": list(fluxerr),
            "filter": list(filters),
            "ra": list(ras),
            "dec": list(decs),
            "magsys": "ab",
            "zp": 25.0,
            "dec_unc": 0.2,
            "ra_unc": 0.2,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]["ids"]) == n_phot

    removed_kwargs = ["instrument_name", "groups", "magsys", "zp", "snr"]
    phot_list = []
    for photometry_id in data["data"]["ids"]:
        status, data = api(
            "GET", f"photometry/{photometry_id}?format=flux", token=upload_data_token
        )
        assert status == 200
        assert data["status"] == "success"
        for key in removed_kwargs:
            data["data"].pop(key)

        phot_list.append(Photometry(**data["data"]))

    ra_calc_snr, dec_calc_snr = _calculate_best_position_for_offset_stars(
        phot_list, fallback=(ra, dec), how="snr2", max_offset=0.5, sigma_clip=4.0
    )
    # make sure we get back a slightly different position than the true center
    with pytest.raises(AssertionError):
        npt.assert_almost_equal(ra_calc_snr, ra, decimal=10)
    with pytest.raises(AssertionError):
        npt.assert_almost_equal(dec_calc_snr, dec, decimal=10)

    ra_calc_err, dec_calc_err = _calculate_best_position_for_offset_stars(
        phot_list, fallback=(ra, dec), how="invvar", max_offset=0.5, sigma_clip=4.0
    )
    # make sure we get back a slightly different position for two different
    # methods
    with pytest.raises(AssertionError):
        npt.assert_almost_equal(ra_calc_snr, ra_calc_err, decimal=10)

    with pytest.raises(AssertionError):
        npt.assert_almost_equal(dec_calc_snr, dec_calc_err, decimal=10)


def test_get_ztfref_url():
    url = get_ztfref_url(123.0, 33.3, 2)
    if url == "":
        pytest.skip("IRSA server down")

    assert isinstance(url, str)
    assert url.find("irsa") != -1


def test_get_nearby_offset_stars():
    how_many = 3
    rez = get_nearby_offset_stars(
        123.0, 33.3, "testSource", how_many=how_many, radius_degrees=3 / 60.0
    )
    # expecting 6 parameters:
    #   a list of the source+offset stars,
    #   What query was used against Gaia,
    #   number of queries_issued,
    #   number of offset stars
    #   whether ZTF ref was used for astrometry
    #   whether Gaia was reachable (proper motion could be applied)
    assert len(rez) == 6
    assert isinstance(rez[0], list)
    assert len(rez[0]) == how_many + 1

    with pytest.raises(Exception):
        rez = get_nearby_offset_stars(
            123.0,
            33.3,
            "testSource",
            how_many=how_many,
            radius_degrees=3 / 60.0,
            allowed_queries=1,
            queries_issued=2,
        )


DESI_URL = (
    "http://legacysurvey.org/viewer/fits-cutout/"
    "?ra=123.0&dec=33.0&layer=dr8&pixscale=2.0&bands=r"
)


def test_get_desi_finding_chart():
    try:
        requests.get(DESI_URL, timeout=10).raise_for_status()
    except (HTTPError, Timeout, ConnectionError):
        pytest.skip("DESI server down")

    rez = get_finding_chart(
        123.0, 33.3, "testSource", image_source="desi", output_format="pdf"
    )

    assert isinstance(rez, dict)
    assert rez["success"]
    assert rez["name"].find("testSource") != -1
    assert rez["data"].find(bytes("PDF", encoding="utf8")) != -1


# test for failure on a too-small image size
def test_get_finding_chart():
    rez = get_finding_chart(
        123.0, 33.3, "testSource", imsize=1.0, image_source="dss", use_cache=False
    )
    assert not rez["success"]

    rez = get_finding_chart(
        123.0, 33.3, "testSource", image_source="zomg_telescope", use_cache=False
    )
    assert isinstance(rez, dict)
    assert not rez["success"]


def _fake_response(status_code=200, body=b""):
    return SimpleNamespace(status_code=status_code, content=body)


# A real CSV reply, trimmed to the columns get_ztfref_url reads.
_IRSA_CSV = b"field,filtercode,qid,ccdid\n600,zr,2,10\n"


def _fresh_position():
    """Coordinates unused by any earlier run.

    _ztfref_url_and_epoch is memoised to disk on (ra, dec, imsize), so a fixed
    position would be answered from a previous run's cache and the test would
    never exercise the code it is checking.
    """
    return float(np.random.uniform(0, 360)), float(np.random.uniform(-20, 60))


def test_ztfref_outage_is_not_cached():
    """An IRSA outage must not be remembered as 'no reference image here'.

    The lookup is disk-memoised, so caching a transient failure would hide the
    reference for that position long after IRSA recovered.
    """
    ra, dec = _fresh_position()
    calls = []

    def flaky(url, **kwargs):
        calls.append(url)
        if len(calls) == 1:
            return _fake_response(status_code=502, body=b"<html>Bad Gateway</html>")
        return _fake_response(body=_IRSA_CSV)

    with patch("skyportal.utils.offset.get_url", side_effect=flaky):
        first = get_ztfref_url(ra, dec, 2)
        assert first == "", "an errored lookup should yield no url"
        second = get_ztfref_url(ra, dec, 2)

    assert len(calls) == 2, "the failure was cached instead of being retried"
    assert "irsa" in second and second.endswith("_refimg.fits"), second


def test_ztfref_absent_reference_is_reported_without_error():
    """IRSA answering 'nothing here' is a real answer, not a failure."""
    ra, dec = _fresh_position()
    empty_csv = _fake_response(body=b"nothing\n")
    with patch("skyportal.utils.offset.get_url", return_value=empty_csv):
        assert get_ztfref_url(ra, dec, 2) == ""
        url, epoch = get_ztfref_url(ra, dec, 2, return_epoch=True)
    assert url == "" and epoch is None


def test_ztfref_lookup_does_not_retry_an_unanswered_position_right_away():
    """The lookup sits on a worker thread, so a silent IRSA must not stall every request."""
    ra, dec = _fresh_position()
    timeouts = []

    def silent(url, **kwargs):
        timeouts.append(kwargs.get("timeout"))
        return None

    with patch("skyportal.utils.offset.get_url", side_effect=silent):
        assert get_ztfref_url(ra, dec, 2) == ""
        assert get_ztfref_url(ra, dec, 2) == ""

    assert timeouts == [IRSA_SEARCH_TIMEOUT]


def test_finding_chart_without_an_image_still_renders():
    """The last survey in the fallback chain returning nothing is not an error.

    The chart is drawn over a blank frame, so the starlist is still usable.
    """
    with patch("skyportal.utils.offset.fits_image", return_value=None):
        rez = get_finding_chart(
            123.0,
            33.3,
            "testSource",
            image_source="dss",
            fallback_image_source=None,
            use_cache=False,
        )

    assert rez["success"], rez.get("reason")
    assert rez["data"].find(bytes("PDF", encoding="utf8")) != -1


def _gaia_stars_around(ra, dec, n=40):
    rng = np.random.default_rng(0)
    return [
        {
            "_id": 4000000000000000000 + i,
            "ra": ra + rng.uniform(-1.5, 1.5) / 60,
            "dec": dec + rng.uniform(-1.5, 1.5) / 60,
            "phot_rp_mean_mag": rng.uniform(11, 17),
            "pmra": rng.uniform(-20, 20),
            "pmdec": rng.uniform(-20, 20),
            "parallax": rng.uniform(0.1, 5),
        }
        for i in range(n)
    ]


def _gaia_tap_table(stars, ra, dec):
    coords = SkyCoord([s["ra"] for s in stars], [s["dec"] for s in stars], unit="deg")
    table = Table(
        {
            "dist": coords.separation(SkyCoord(ra, dec, unit="deg")).deg,
            "source_id": np.array([s["_id"] for s in stars], dtype=np.int64),
            "ra": [s["ra"] for s in stars],
            "dec": [s["dec"] for s in stars],
            "ref_epoch": np.full(len(stars), 2016.0),
            "phot_rp_mean_mag": [s["phot_rp_mean_mag"] for s in stars],
            "pmra": [s["pmra"] for s in stars],
            "pmdec": [s["pmdec"] for s in stars],
            "parallax": [s["parallax"] for s in stars],
        }
    )
    table["dist"].unit = u.deg
    table["ref_epoch"].unit = u.yr
    for name in offset.OFFSET_STAR_COLUMNS:
        table[name].unit = offset.GAIA_UNITS[name]
    return table


def _offset_stars(ra, dec, broker, obstime="2026-10-05T00:00:00"):
    return get_nearby_offset_stars(
        ra,
        dec,
        "testSource",
        radius_degrees=2 / 60.0,
        obstime=obstime,
        use_ztfref=False,
        gaia_broker=broker,
    )


def _broker(**cone_search):
    gaia_cone_search = Mock(**cone_search)
    return SimpleNamespace(
        name="BOOM", broker_class=SimpleNamespace(gaia_cone_search=gaia_cone_search)
    )


def test_offset_stars_from_the_broker_match_the_gaia_tap():
    ra, dec = _fresh_position()
    stars = _gaia_stars_around(ra, dec)
    from_broker = _offset_stars(ra, dec, broker=_broker(return_value=stars))
    offset.offsets_memory.clear(warn=False)
    with patch.object(
        offset.gaia, "query", return_value=_gaia_tap_table(stars, ra, dec)
    ):
        from_tap = _offset_stars(ra, dec, broker=None)

    assert from_broker[0] == from_tap[0]
    assert len(from_broker[0]) > 1
    assert from_broker[5] is True


def test_gaia_stars_are_cached():
    ra, dec = _fresh_position()
    broker = _broker(return_value=_gaia_stars_around(ra, dec))
    first = _offset_stars(ra, dec, broker=broker)
    later = _offset_stars(ra, dec, broker=broker, obstime="2026-10-06T00:00:00")

    assert broker.broker_class.gaia_cone_search.call_count == 1
    assert len(first[0]) > 1 and len(later[0]) == len(first[0])


def test_broker_failure_falls_back_to_the_gaia_tap():
    ra, dec = _fresh_position()
    stars = _gaia_stars_around(ra, dec)
    broker = _broker(side_effect=requests.exceptions.HTTPError("502"))
    with patch.object(
        offset.gaia, "query", return_value=_gaia_tap_table(stars, ra, dec)
    ) as tap:
        result = _offset_stars(ra, dec, broker=broker)

    assert tap.call_count == 1
    assert len(result[0]) > 1
    assert result[5] is True


def test_without_a_broker_the_gaia_tap_is_used():
    ra, dec = _fresh_position()
    stars = _gaia_stars_around(ra, dec)
    with patch.object(
        offset.gaia, "query", return_value=_gaia_tap_table(stars, ra, dec)
    ) as tap:
        _offset_stars(ra, dec, broker=None)

    assert tap.call_count == 1


def test_gaia_outage_is_not_cached():
    ra, dec = _fresh_position()
    with patch.object(offset.gaia, "query", return_value=None) as tap:
        first = _offset_stars(ra, dec, broker=None)
        _offset_stars(ra, dec, broker=None, obstime="2026-10-06T00:00:00")

    assert tap.call_count == 2
    assert first[5] is False
