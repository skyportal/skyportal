import pytest

from skyportal.tests import api

# Offset / guide stars are pulled from external catalogs by
# skyportal/utils/offset.py -- primarily Gaia (via its TAP service), with the
# IRSA ZTF reference catalog as a backup. The `/offsets` endpoint degrades
# gracefully (it still returns 200/"success" with noffsets=0 when those services
# are unreachable or return nothing), so this test lives under tests/external and
# skips -- rather than fails -- when the catalogs are unavailable, matching the
# other external catalog/offset tests (e.g. test_ztf_gaia_backup.py).

OFFSETS_UNAVAILABLE = "Gaia/ZTF offset-star catalog service unavailable"


def test_starlist(super_admin_token, upload_data_token, public_source):
    status, data = api(
        "PATCH",
        f"sources/{public_source.id}",
        data={"ra": 234.22, "dec": 22.33},
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "GET",
        f"sources/{public_source.id}/offsets",
        params={"facility": "P200", "num_offset_stars": "1"},
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    if data["data"]["noffsets"] < 1:
        pytest.skip(OFFSETS_UNAVAILABLE)
    assert data["data"]["noffsets"] == 1
    assert data["data"]["queries_issued"] == 1
    assert data["data"]["facility"] == "P200"
    assert "starlist_str" in data["data"]
    assert isinstance(data["data"]["starlist_info"][0]["ra"], float)

    status, data = api(
        "GET",
        f"sources/{public_source.id}/offsets",
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    if data["data"]["noffsets"] < 3:
        pytest.skip(OFFSETS_UNAVAILABLE)
    assert data["data"]["noffsets"] == 3
    assert data["data"]["facility"] == "Keck"
    assert "starlist_str" in data["data"]
    assert isinstance(data["data"]["starlist_info"][2]["dec"], float)

    # use DR3 for offsets ... it should not be identical position as DR3
    status, data = api(
        "GET",
        f"sources/{public_source.id}/offsets",
        params={"use_ztfref": "false"},
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    if data["data"]["noffsets"] < 3:
        pytest.skip(OFFSETS_UNAVAILABLE)
    assert isinstance(data["data"]["starlist_info"][2]["dec"], float)
