from skyportal.tests import api


def test_bulk_delete_photometry(
    super_admin_token, upload_data_token, public_source, public_group, ztf_camera
):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": [58000.0, 58001.0, 58002.0],
            "instrument_id": ztf_camera.id,
            "flux": [12.24, 12.52, 12.70],
            "fluxerr": [0.031, 0.029, 0.030],
            "filter": ["ztfg", "ztfg", "ztfg"],
            "zp": [25.0, 25.0, 25.0],
            "magsys": ["ab", "ab", "ab"],
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    upload_id = data["data"]["upload_id"]

    status, data = api(
        "DELETE", f"photometry/bulk_delete/{upload_id}", token=super_admin_token
    )
    assert status == 200
    assert data["data"] == "Deleted 3 photometry point(s)."
