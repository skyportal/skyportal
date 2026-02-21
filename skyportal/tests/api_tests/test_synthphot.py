import datetime
import uuid

from skyportal.tests import api


def test_synthetic_photometry(super_admin_token, public_source, public_group):
    telescope_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "telescope",
        data={
            "name": telescope_name,
            "nickname": telescope_name,
            "lat": 0.0,
            "lon": 0.0,
            "elevation": 0.0,
            "diameter": 10.0,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    telescope_id = data["data"]["id"]

    instrument_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "instrument",
        data={
            "name": instrument_name,
            "type": "spectrograph",
            "telescope_id": telescope_id,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    instrument_id = data["data"]["id"]

    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": public_source.id,
            "observed_at": str(datetime.datetime.now()),
            "instrument_id": instrument_id,
            "wavelengths": [1000, 3000, 5000, 7000, 9000],
            "fluxes": [232.1, 234.2, 232.1, 235.3, 232.1],
            "units": "erg/s/cm/cm/AA",
            "group_ids": [public_group.id],
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    spectrum_id = data["data"]["id"]

    filters = ["ztfg", "ztfr", "ztfi"]
    status, data = api(
        "POST",
        f"spectra/synthphot/{spectrum_id}",
        data={
            "filters": filters,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    # Check for single GET call as well
    status, data = api(
        "GET",
        f"sources/{public_source.id}",
        params={"includePhotometry": "true"},
        token=super_admin_token,
    )
    assert status == 200
    assert data["data"]["id"] == public_source.id
    for filt in filters:
        assert any(p["filter"] == filt for p in data["data"]["photometry"])

    filters = ["f140w", "f153m", "f160w"]
    status, data = api(
        "POST",
        f"spectra/synthphot/{spectrum_id}",
        data={
            "filters": filters,
        },
        token=super_admin_token,
    )
    assert status == 400
    data["status"] == "error"
    assert "outside spectral range" in data["message"]
