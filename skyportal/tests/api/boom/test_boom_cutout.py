import pytest

from skyportal.tests import api

SURVEY = "ZTF"

# Placeholders used by error-path tests that fail validation *before*
# hitting BOOM. The actual values don't matter as long as parsing succeeds.
_PLACEHOLDER_CANDID = 1105522281015015000
_PLACEHOLDER_OID = "ZTF99zzzzzz"


def _cutout_url(query: str) -> str:
    return f"boom/surveys/{SURVEY}/alerts/cutouts?{query}"


# ── Happy paths (need real alert in BOOM mongo) ─────────────────────────────


@pytest.mark.requires_boom_data
def test_get_cutout_fits_by_candid(view_only_token, boom_seed_candid):
    status, data = api(
        "GET",
        _cutout_url(f"candid={boom_seed_candid}&file_format=fits"),
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert isinstance(data["data"], dict)
    for key in ("cutoutScience", "cutoutTemplate", "cutoutDifference"):
        assert key in data["data"]


@pytest.mark.requires_boom_data
def test_get_cutout_fits_by_object_id(view_only_token, boom_seed_oid):
    status, data = api(
        "GET",
        _cutout_url(f"objectId={boom_seed_oid}&which=last&file_format=fits"),
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert isinstance(data["data"], dict)


@pytest.mark.requires_boom_data
def test_get_cutout_png_all_types(view_only_token, boom_seed_candid):
    for cutout in ("science", "template", "difference"):
        response = api(
            "GET",
            _cutout_url(f"candid={boom_seed_candid}&file_format=png&cutout={cutout}"),
            token=view_only_token,
            raw_response=True,
        )
        assert response.status_code == 200
        assert response.headers.get("Content-Type") == "image/png"
        assert len(response.content) > 0


# ── Error paths (validate before hitting BOOM, no seed needed) ──────────────


def test_get_cutout_no_identifier_errors(view_only_token):
    status, data = api("GET", _cutout_url("file_format=fits"), token=view_only_token)
    assert status == 400
    assert data["status"] == "error"


def test_get_cutout_both_identifiers_errors(view_only_token):
    status, data = api(
        "GET",
        _cutout_url(
            f"candid={_PLACEHOLDER_CANDID}&objectId={_PLACEHOLDER_OID}&file_format=fits"
        ),
        token=view_only_token,
    )
    assert status == 400
    assert data["status"] == "error"


def test_get_cutout_png_without_cutout_param_errors(view_only_token):
    status, data = api(
        "GET",
        _cutout_url(f"candid={_PLACEHOLDER_CANDID}&file_format=png"),
        token=view_only_token,
    )
    assert status == 400
    assert data["status"] == "error"


def test_get_cutout_invalid_cutout_errors(view_only_token):
    status, data = api(
        "GET",
        _cutout_url(f"candid={_PLACEHOLDER_CANDID}&file_format=png&cutout=bogus"),
        token=view_only_token,
    )
    assert status == 400
    assert data["status"] == "error"


def test_get_cutout_invalid_candid_errors(view_only_token):
    status, data = api(
        "GET",
        _cutout_url("candid=not_an_int&file_format=fits"),
        token=view_only_token,
    )
    assert status == 400
    assert data["status"] == "error"


def test_get_cutout_invalid_file_format_errors(view_only_token):
    status, data = api(
        "GET",
        _cutout_url(f"candid={_PLACEHOLDER_CANDID}&file_format=jpeg"),
        token=view_only_token,
    )
    assert status == 400
    assert data["status"] == "error"


def test_get_cutout_invalid_which_errors(view_only_token):
    status, data = api(
        "GET",
        _cutout_url(f"objectId={_PLACEHOLDER_OID}&which=middle&file_format=fits"),
        token=view_only_token,
    )
    assert status == 400
    assert data["status"] == "error"


def test_post_cutout_requires_object_id(upload_data_token):
    status, data = api(
        "POST",
        f"boom/surveys/{SURVEY}/alerts/cutouts",
        data={},
        token=upload_data_token,
    )
    assert status == 400
    assert data["status"] == "error"


def test_post_cutout_unknown_object_errors(upload_data_token):
    status, data = api(
        "POST",
        f"boom/surveys/{SURVEY}/alerts/cutouts",
        data={"objectId": _PLACEHOLDER_OID, "which": "last"},
        token=upload_data_token,
    )
    assert status == 400
    assert data["status"] == "error"
    # Handler returns "Object 'X' not found. Save it as a source first."
    assert "not found" in (data.get("message") or "").lower()
