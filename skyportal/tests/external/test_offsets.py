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


def test_ngps_starlist_magnitude_skips_non_detections(
    super_admin_token, upload_data_token, public_source, public_group, ztf_camera
):
    """The newest NGPS-band point can be a NaN-flux non-detection, which has no
    magnitude; the target must still carry the latest one that does."""
    status, data = api(
        "PATCH",
        f"sources/{public_source.id}",
        data={"ra": 234.22, "dec": 22.33},
        token=super_admin_token,
    )
    assert status == 200

    for point in (
        {"mjd": 61254.4, "mag": 18.9, "magerr": 0.07, "filter": "ztfg"},
        # Newer, and a non-detection: stored with NaN flux.
        {"mjd": 61258.9, "mag": None, "magerr": None, "filter": "ztfr"},
    ):
        status, data = api(
            "POST",
            "photometry",
            data={
                "obj_id": str(public_source.id),
                "instrument_id": ztf_camera.id,
                "limiting_mag": 22.3,
                "magsys": "ab",
                "group_ids": [public_group.id],
                **point,
            },
            token=upload_data_token,
        )
        assert status == 200, data

    status, data = api(
        "GET",
        f"sources/{public_source.id}/offsets",
        params={"facility": "P200-NGPS", "num_offset_stars": "1"},
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    # The target row carries a position but no offsets; the offset stars do.
    target = next(
        row
        for row in data["data"]["starlist_info"]
        if "ra" in row and "dras" not in row
    )
    # ngps_defaults() ends the row with ...,{mag},{magfilter},SNR 5,1
    mag, magfilter = target["str"].split(",")[-4:-2]
    assert mag != "", "target exported with no magnitude"
    assert float(mag) == 18.9
    assert magfilter == "G"
