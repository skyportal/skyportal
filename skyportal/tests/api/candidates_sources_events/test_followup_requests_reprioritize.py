from skyportal.tests import api


def test_reprioritize_followup_request(
    public_group_sedm_allocation,
    public_source,
    upload_data_token,
    super_admin_token,
    gcn_GW190425,
):
    localization_id = gcn_GW190425.localizations[0].id

    request_data = {
        "allocation_id": public_group_sedm_allocation.id,
        "obj_id": public_source.id,
        "payload": {
            "priority": 1,
            "start_date": "3020-09-01",
            "end_date": "3022-09-01",
            "observation_type": "IFU",
            "exposure_time": 300,
            "maximum_airmass": 2,
            "maximum_fwhm": 1.2,
        },
    }

    status, data = api(
        "POST", "followup_request", data=request_data, token=upload_data_token
    )
    assert status == 200
    assert data["status"] == "success"
    id = data["data"]["id"]

    new_request_data = {
        "localizationId": localization_id,
        "requestIds": [id],
        "priorityType": "localization",
    }

    status, data = api(
        "PUT",
        "followup_request/prioritization",
        data=new_request_data,
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"followup_request/{id}", token=upload_data_token)
    assert status == 200

    assert data["data"]["payload"]["priority"] == 5
