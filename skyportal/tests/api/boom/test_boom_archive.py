import pytest

from skyportal.tests import api


def test_get_archive_catalogs(view_only_token):
    status, data = api("GET", "boom/archive/catalogs", token=view_only_token)
    assert status == 200
    assert data["status"] == "success"
    assert isinstance(data["data"], list)
    # Reference catalogs only — survey collections must be stripped out.
    for name in data["data"]:
        assert not name.startswith(("ZTF_", "LSST_", "PTF_", "PGIR_", "WNTR_"))


@pytest.mark.requires_boom_data
def test_cross_match_happy_path(view_only_token):
    # The cross-match endpoint fans out over BOOM's reference catalogs.
    # In CI we seed a `test_catalog` collection with 1000 fake sources
    # in a 0.01 deg box around (RA=0, Dec=80). The wider search radius
    # here (1 deg) is generous enough that we should always get matches
    # given the fake catalog density, while still exercising the real
    # cone-search code path. Defensive skip kept so the test degrades
    # gracefully if the catalog seeding step is removed/skipped.
    status, catalogs_data = api("GET", "boom/archive/catalogs", token=view_only_token)
    if status != 200 or not catalogs_data.get("data"):
        pytest.skip("BOOM has no reference catalogs ingested; skipping cross-match")

    ra, dec = 0.005, 80.0  # inside the fake_source_* spread
    status, data = api(
        "GET",
        f"boom/archive/cross_match?ra={ra}&dec={dec}&radius=1&radius_units=deg",
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert isinstance(data["data"], dict)
    # The fake catalog should have produced at least one hit.
    assert "test_catalog" in data["data"]
    assert len(data["data"]["test_catalog"]) > 0


def test_cross_match_missing_params_errors(view_only_token):
    status, data = api("GET", "boom/archive/cross_match?ra=10", token=view_only_token)
    assert status == 400
    assert data["status"] == "error"


def test_cross_match_invalid_radius_units_errors(view_only_token):
    status, data = api(
        "GET",
        "boom/archive/cross_match?ra=10&dec=20&radius=1&radius_units=parsecs",
        token=view_only_token,
    )
    assert status == 400
    assert data["status"] == "error"


def test_cross_match_non_float_errors(view_only_token):
    status, data = api(
        "GET",
        "boom/archive/cross_match?ra=abc&dec=20&radius=1&radius_units=arcsec",
        token=view_only_token,
    )
    assert status == 400
    assert data["status"] == "error"


def test_cross_match_ra_out_of_range_errors(view_only_token):
    status, data = api(
        "GET",
        "boom/archive/cross_match?ra=400&dec=20&radius=1&radius_units=arcsec",
        token=view_only_token,
    )
    assert status == 400
    assert data["status"] == "error"


def test_cross_match_dec_out_of_range_errors(view_only_token):
    status, data = api(
        "GET",
        "boom/archive/cross_match?ra=10&dec=120&radius=1&radius_units=arcsec",
        token=view_only_token,
    )
    assert status == 400
    assert data["status"] == "error"


def test_cross_match_radius_too_large_errors(view_only_token):
    status, data = api(
        "GET",
        "boom/archive/cross_match?ra=10&dec=20&radius=2&radius_units=deg",
        token=view_only_token,
    )
    assert status == 400
    assert data["status"] == "error"
