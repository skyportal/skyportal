from skyportal.tests import api


def test_bulk_delete_photometry(upload_data_token, public_source, public_group):
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": [58000.0, 58001.0, 58002.0],
            "instrument_id": 1,
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
    bulk_upload_id = data["data"]["bulk_upload_id"]

    status, data = api(
        "DELETE", f"photometry/bulk_delete/{bulk_upload_id}", token=upload_data_token
    )
    assert status == 200
    assert data["data"] == "Deleted 3 photometry points."
