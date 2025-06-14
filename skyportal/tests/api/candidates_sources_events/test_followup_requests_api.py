from datetime import datetime

from skyportal.tests import api


def test_token_user_post_robotic_followup_request(
    public_group_sedm_allocation, public_source, upload_data_token
):
    request_data = {
        "allocation_id": public_group_sedm_allocation.id,
        "obj_id": public_source.id,
        "payload": {
            "priority": 5,
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

    status, data = api("GET", f"followup_request/{id}", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"

    for key in request_data:
        assert data["data"][key] == request_data[key]


def test_token_user_delete_owned_followup_request(
    public_group_generic_allocation, public_source, upload_data_token
):
    request_data = {
        "allocation_id": public_group_generic_allocation.id,
        "obj_id": public_source.id,
        "payload": {
            "priority": 5,
            "start_date": "3020-09-01",
            "end_date": "3022-09-01",
            "observation_choices": public_group_generic_allocation.instrument.to_dict()[
                "filters"
            ],
            "exposure_time": 300,
            "exposure_counts": 1,
            "maximum_airmass": 2,
            "minimum_lunar_distance": 30,
        },
    }

    status, data = api(
        "POST", "followup_request", data=request_data, token=upload_data_token
    )
    assert status == 200
    assert data["status"] == "success"
    id = data["data"]["id"]

    status, data = api("DELETE", f"followup_request/{id}", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"


def test_token_user_modify_owned_followup_request(
    public_group_sedm_allocation, public_source, upload_data_token
):
    request_data = {
        "allocation_id": public_group_sedm_allocation.id,
        "obj_id": public_source.id,
        "payload": {
            "priority": 5,
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
        "allocation_id": public_group_sedm_allocation.id,
        "obj_id": public_source.id,
        "payload": {
            "priority": 4,
            "start_date": "3020-09-01",
            "end_date": "3022-09-01",
            "observation_type": "IFU",
            "exposure_time": 300,
            "maximum_airmass": 2,
            "maximum_fwhm": 1.2,
        },
    }

    status, data = api(
        "PUT", f"followup_request/{id}", data=new_request_data, token=upload_data_token
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"followup_request/{id}", token=upload_data_token)
    assert status == 200

    for k in new_request_data:
        assert data["data"][k] == new_request_data[k]


def test_regular_user_delete_super_admin_followup_request(
    public_group_generic_allocation,
    public_source,
    upload_data_token,
    super_admin_token,
):
    request_data = {
        "allocation_id": public_group_generic_allocation.id,
        "obj_id": public_source.id,
        "payload": {
            "priority": 5,
            "start_date": "3020-09-01",
            "end_date": "3022-09-01",
            "observation_choices": public_group_generic_allocation.instrument.to_dict()[
                "filters"
            ],
            "exposure_time": 300,
            "exposure_counts": 1,
            "maximum_airmass": 2,
            "minimum_lunar_distance": 30,
        },
    }

    status, data = api(
        "POST", "followup_request", data=request_data, token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"
    id = data["data"]["id"]

    status, data = api("DELETE", f"followup_request/{id}", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"


def test_group1_user_cannot_see_group2_followup_request(
    public_group2_sedm_allocation,
    public_source_group2,
    super_admin_token,
    view_only_token,
):
    request_data = {
        "allocation_id": public_group2_sedm_allocation.id,
        "obj_id": public_source_group2.id,
        "payload": {
            "priority": 5,
            "start_date": "3020-09-01",
            "end_date": "3022-09-01",
            "observation_type": "IFU",
            "exposure_time": 300,
            "maximum_airmass": 2,
            "maximum_fwhm": 1.2,
        },
    }

    status, data = api(
        "POST", "followup_request", data=request_data, token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"
    id = data["data"]["id"]

    status, data = api("GET", f"followup_request/{id}", token=view_only_token)
    assert status == 400
    assert data["status"] == "error"

    status, data = api("GET", "followup_request/", token=view_only_token)
    assert status == 200
    assert id not in [a["id"] for a in data["data"]["followup_requests"]]


def test_filter_followup_request(
    public_group_sedm_allocation,
    public_source,
    upload_data_token,
    view_only_token,
):
    request_data = {
        "allocation_id": public_group_sedm_allocation.id,
        "obj_id": public_source.id,
        "payload": {
            "priority": 5,
            "start_date": "3020-09-01",
            "end_date": "3022-09-01",
            "observation_type": "IFU",
            "exposure_time": 300,
            "maximum_airmass": 2,
            "maximum_fwhm": 1.2,
        },
    }

    time_before_post = datetime.utcnow().isoformat()
    status, data = api(
        "POST", "followup_request", data=request_data, token=upload_data_token
    )
    assert status == 200
    assert data["status"] == "success"

    params = {"startDate": time_before_post}

    status, data = api(
        "GET",
        "followup_request",
        params=params,
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert any(
        s["obj_id"] == public_source.id for s in data["data"]["followup_requests"]
    )

    time_after_post = datetime.utcnow().isoformat()

    params = {"startDate": time_after_post}

    status, data = api(
        "GET",
        "followup_request",
        params=params,
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert not any(
        s["obj_id"] == public_source.id for s in data["data"]["followup_requests"]
    )

    params = {"sourceID": public_source.id}

    status, data = api(
        "GET",
        "followup_request",
        params=params,
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"
    assert any(
        s["obj_id"] == public_source.id for s in data["data"]["followup_requests"]
    )
