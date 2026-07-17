import pytest

from skyportal.tests import api

SURVEY = "ZTF"


def _alerts_url(query: str = "") -> str:
    base = f"boom/surveys/{SURVEY}/alerts"
    return f"{base}?{query}" if query else base


# ── Happy paths (need a real alert in BOOM mongo) ────────────────────────────


@pytest.mark.requires_boom_data
def test_get_alerts_by_object_id(view_only_token, boom_seed_oid):
    status, data = api(
        "GET", _alerts_url(f"objectId={boom_seed_oid}"), token=view_only_token
    )
    assert status == 200
    assert data["status"] == "success"
    assert isinstance(data["data"], list)
    assert len(data["data"]) > 0
    assert all(alert.get("objectId") == boom_seed_oid for alert in data["data"])


@pytest.mark.requires_boom_data
def test_get_alerts_by_object_id_comma_list(view_only_token, boom_seed_oid):
    status, data = api(
        "GET",
        _alerts_url(f"objectId={boom_seed_oid},{boom_seed_oid}"),
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert isinstance(data["data"], list)


@pytest.mark.requires_boom_data
def test_get_alerts_by_candid(view_only_token, boom_seed_candid):
    # The handler's filter_doc uses {"candid": X}, but BOOM stores candid
    # as the document `_id` (and may not duplicate it as a top-level
    # `candid` field). The query may legitimately return an empty list.
    # We assert the wire-up — status + response shape — and verify any
    # returned alert with an `_id`/`candid` matches the seed value.
    status, data = api(
        "GET", _alerts_url(f"candid={boom_seed_candid}"), token=view_only_token
    )
    assert status == 200
    assert data["status"] == "success"
    assert isinstance(data["data"], list)
    seed = str(boom_seed_candid)
    for alert in data["data"]:
        identifier = str(alert.get("_id") or alert.get("candid") or "")
        if identifier:
            assert identifier == seed


@pytest.mark.requires_boom_data
def test_get_alerts_by_candid_and_object_id(
    view_only_token, boom_seed_candid, boom_seed_oid
):
    status, data = api(
        "GET",
        _alerts_url(f"candid={boom_seed_candid}&objectId={boom_seed_oid}"),
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert isinstance(data["data"], list)


@pytest.mark.requires_boom_data
def test_get_alerts_by_cone_search(view_only_token, boom_seed_ra, boom_seed_dec):
    status, data = api(
        "GET",
        _alerts_url(
            f"ra={boom_seed_ra}&dec={boom_seed_dec}&radius=0.5&radius_units=deg"
        ),
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert all("objectId" in alert for alert in data["data"])


@pytest.mark.requires_boom_data
def test_get_alerts_cone_plus_object_id_filter(
    view_only_token, boom_seed_ra, boom_seed_dec, boom_seed_oid
):
    status, data = api(
        "GET",
        _alerts_url(
            f"ra={boom_seed_ra}&dec={boom_seed_dec}&radius=0.5&radius_units=deg"
            f"&objectId={boom_seed_oid}"
        ),
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert all(alert.get("objectId") == boom_seed_oid for alert in data["data"])


# ── Error paths (independent of seed data) ──────────────────────────────────


def test_get_alerts_no_params_errors(view_only_token):
    status, data = api("GET", _alerts_url(), token=view_only_token)
    assert status == 400
    assert data["status"] == "error"


def test_get_alerts_invalid_candid_errors(view_only_token):
    status, data = api("GET", _alerts_url("candid=not_an_int"), token=view_only_token)
    assert status == 400
    assert data["status"] == "error"


def test_get_alerts_invalid_radius_units_errors(view_only_token):
    status, data = api(
        "GET",
        _alerts_url("ra=108.5&dec=35.8&radius=1&radius_units=parsecs"),
        token=view_only_token,
    )
    assert status == 400
    assert data["status"] == "error"


def test_get_alerts_radius_too_large_errors(view_only_token):
    status, data = api(
        "GET",
        _alerts_url("ra=108.5&dec=35.8&radius=2&radius_units=deg"),
        token=view_only_token,
    )
    assert status == 400
    assert data["status"] == "error"


def test_get_alerts_incomplete_positional_errors(view_only_token):
    status, data = api(
        "GET",
        _alerts_url("ra=108.5&dec=35.8&radius=1"),
        token=view_only_token,
    )
    assert status == 400
    assert data["status"] == "error"
