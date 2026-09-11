import uuid

from skyportal.tests import api


def test_obj_photometry(upload_data_token, public_source):
    status, data = api(
        "GET",
        f"sources/{public_source.id}/photometry",
        token=upload_data_token,
    )
    assert status == 200

    obj_id = str(uuid.uuid4())

    # try a non-existent source
    status, data = api(
        "GET",
        f"sources/{obj_id}/photometry",
        token=upload_data_token,
    )
    assert status == 403
    assert (
        f"Insufficient permissions for User {upload_data_token} to read Obj {obj_id}"
        in data["message"]
    )


def test_xray_point_does_not_break_a_vega_light_curve(
    upload_data_token, super_admin_token, public_group, public_source
):
    """An X-ray bandpass has no Vega magnitude, but must not fail the request."""
    name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "telescope",
        data={
            "name": name,
            "nickname": name,
            "lat": 0.0,
            "lon": 0.0,
            "elevation": 0.0,
            "diameter": 1.0,
        },
        token=super_admin_token,
    )
    assert status == 200
    telescope_id = data["data"]["id"]

    status, data = api(
        "POST",
        "instrument",
        data={
            "name": name,
            "type": "imager",
            "band": "X-ray",
            "telescope_id": telescope_id,
            "filters": ["epfxt"],
        },
        token=super_admin_token,
    )
    assert status == 200
    instrument_id = data["data"]["id"]

    status, _ = api(
        "POST",
        "photometry",
        data={
            "obj_id": public_source.id,
            "mjd": 60000.5,
            "instrument_id": instrument_id,
            "filter": "epfxt",
            "flux": 0.042,
            "fluxerr": 0.0085,
            "zp": 23.9,
            "magsys": "ab",
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200

    status, data = api(
        "GET",
        f"sources/{public_source.id}/photometry?format=mag&magsys=vega",
        token=upload_data_token,
    )
    assert status == 200
    xray = [p for p in data["data"] if p["filter"] == "epfxt"]
    assert len(xray) == 1
    # Reported in AB, and saying so, rather than raising.
    assert xray[0]["magsys"] == "ab"


def test_deleting_an_obj_reports_why_rather_than_erroring(
    super_admin_token, public_source
):
    """The config key gating this is optional, and reading it must not 500."""
    status, data = api("DELETE", f"objs/{public_source.id}", token=super_admin_token)
    assert status == 400
    assert "before removing" in data["message"]
