import uuid

from skyportal.tests import api


def _spectrum_ids(obj_id, token):
    status, data = api("GET", "spectra", params={"objID": obj_id}, token=token)
    assert status == 200
    return sorted(s["id"] for s in data["data"])


def test_identical_ascii_spectrum_is_not_duplicated(
    upload_data_token, public_source, public_group, lris
):
    data = {
        "obj_id": str(public_source.id),
        "observed_at": "2020-02-01T00:00:00",
        "instrument_id": lris.id,
        "group_ids": [public_group.id],
        "ascii": "4000 0.01\n4500 0.02\n5000 0.005\n",
        "filename": f"{uuid.uuid4()}.ascii",
    }
    existing = _spectrum_ids(public_source.id, upload_data_token)
    ids = []
    for _ in range(2):
        status, response = api(
            "POST", "spectrum/ascii", data=data, token=upload_data_token
        )
        assert status == 200
        ids.append(response["data"]["id"])
    assert ids[0] == ids[1]

    data["ascii"] = "4000 0.01\n4500 0.03\n5000 0.005\n"
    status, response = api("POST", "spectrum/ascii", data=data, token=upload_data_token)
    assert status == 200
    assert _spectrum_ids(public_source.id, upload_data_token) == sorted(
        [*existing, ids[0], response["data"]["id"]]
    )


def test_identical_spectrum_is_not_duplicated(
    upload_data_token, public_source, public_group, lris
):
    data = {
        "obj_id": str(public_source.id),
        "observed_at": "2020-02-01T00:00:00",
        "instrument_id": lris.id,
        "wavelengths": [664, 665, 666],
        "fluxes": [234.2, 232.1, 235.3],
        "group_ids": [public_group.id],
    }
    existing = _spectrum_ids(public_source.id, upload_data_token)
    ids = []
    for _ in range(2):
        status, response = api("POST", "spectrum", data=data, token=upload_data_token)
        assert status == 200
        ids.append(response["data"]["id"])

    assert ids[0] == ids[1]
    assert _spectrum_ids(public_source.id, upload_data_token) == sorted(
        [*existing, ids[0]]
    )
