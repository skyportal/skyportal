from skyportal.tests import api


def test_super_user_post_allocation(
    sedm, public_group, public_group2, super_admin_token
):
    request_data = {
        "group_id": public_group.id,
        "instrument_id": sedm.id,
        "pi": "Shri Kulkarni",
        "hours_allocated": 200,
        "validity_ranges": [
            {
                "start_date": "2021-02-27T00:00:00.000Z",
                "end_date": "3021-07-20T00:00:00.000Z",
            }
        ],
        "proposal_id": "COO-2020A-P01",
        "default_share_group_ids": [public_group.id, public_group2.id],
    }

    status, data = api("POST", "allocation", data=request_data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    id = data["data"]["id"]

    status, data = api("GET", f"allocation/{id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    for key in request_data:
        assert data["data"]["allocation"][key] == request_data[key]


def test_super_user_modify_allocation(sedm, public_group, super_admin_token):
    request_data = {
        "group_id": public_group.id,
        "instrument_id": sedm.id,
        "pi": "Shri Kulkarni",
        "hours_allocated": 200,
        "validity_ranges": [
            {
                "start_date": "2021-02-27T00:00:00.000Z",
                "end_date": "3021-07-20T00:00:00.000Z",
            }
        ],
        "proposal_id": "COO-2020A-P01",
    }

    status, data = api("POST", "allocation", data=request_data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    id = data["data"]["id"]

    status, data = api("GET", f"allocation/{id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    for key in request_data:
        assert data["data"]["allocation"][key] == request_data[key]

    request2_data = {"proposal_id": "COO-2020A-P02"}

    status, data = api(
        "PUT", f"allocation/{id}", data=request2_data, token=super_admin_token
    )
    assert status == 200

    status, data = api("GET", f"allocation/{id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    request_data.update(request2_data)
    for key in request_data:
        assert data["data"]["allocation"][key] == request_data[key]


def test_read_only_user_cannot_get_unowned_allocation(
    view_only_token, super_admin_token, sedm, public_group2
):
    request_data = {
        "group_id": public_group2.id,
        "instrument_id": sedm.id,
        "pi": "Shri Kulkarni",
        "hours_allocated": 200,
        "validity_ranges": [
            {
                "start_date": "2021-02-27T00:00:00.000Z",
                "end_date": "3021-07-20T00:00:00.000Z",
            }
        ],
        "proposal_id": "COO-2020A-P01",
    }

    status, data = api("POST", "allocation", data=request_data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    id = data["data"]["id"]

    status, data = api("GET", f"allocation/{id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    for key in request_data:
        assert data["data"]["allocation"][key] == request_data[key]

    status, data = api("GET", f"allocation/{id}", token=view_only_token)
    assert status == 400
    assert data["status"] == "error"


def test_read_only_user_get_invalid_allocation_id(view_only_token):
    status, data = api("GET", f"allocation/{-1}", token=view_only_token)
    assert status == 400
    assert data["status"] == "error"


def test_delete_allocation_cascades_to_requests(
    public_group, public_source, super_admin_token, sedm
):
    request_data = {
        "group_id": public_group.id,
        "instrument_id": sedm.id,
        "pi": "Shri Kulkarni",
        "hours_allocated": 200,
        "validity_ranges": [
            {
                "start_date": "2021-02-27T00:00:00.000Z",
                "end_date": "3021-07-20T00:00:00.000Z",
            }
        ],
        "proposal_id": "COO-2020A-P01",
    }

    status, data = api("POST", "allocation", data=request_data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    allocation_id = data["data"]["id"]

    request_data = {
        "allocation_id": allocation_id,
        "obj_id": public_source.id,
        "payload": {
            "priority": 5,
            "start_date": "3010-09-01",
            "end_date": "3012-09-01",
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
    request_id = data["data"]["id"]

    status, data = api("GET", f"followup_request/{request_id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    status, data = api("DELETE", f"allocation/{allocation_id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"followup_request/{request_id}", token=super_admin_token)
    assert status == 400
    assert "Could not retrieve followup request" in data["message"]


def test_allocation_comment(public_group, public_source, super_admin_token, sedm):
    # Create an allocation
    request_data = {
        "group_id": public_group.id,
        "instrument_id": sedm.id,
        "pi": "Shri Kulkarni",
        "hours_allocated": 200,
        "validity_ranges": [
            {
                "start_date": "2021-02-27T00:00:00.000Z",
                "end_date": "3021-07-20T00:00:00.000Z",
            }
        ],
        "proposal_id": "COO-2020A-P01",
    }

    # Post the allocation
    status, data = api("POST", "allocation", data=request_data, token=super_admin_token)

    # Check that the allocation was created
    assert status == 200
    assert data["status"] == "success"
    allocation_id = data["data"]["id"]

    # Create a followup request with the allocation id
    request_data = {
        "allocation_id": allocation_id,
        "obj_id": public_source.id,
        "payload": {
            "priority": 5,
            "start_date": "3010-09-01",
            "end_date": "3012-09-01",
            "observation_type": "IFU",
            "exposure_time": 300,
            "maximum_airmass": 2,
            "maximum_fwhm": 1.2,
        },
    }

    # Post the followup request with no comment
    status, data = api(
        "POST", "followup_request", data=request_data, token=super_admin_token
    )
    # Check that the followup request was created and get the request id
    assert status == 200
    assert data["status"] == "success"
    request_id = data["data"]["id"]

    # Check that the comment on the followup request is empty
    status, data = api("GET", f"followup_request/{request_id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["comment"] is None

    # Create a comment to put on the followup request
    request_data = {"comment": "This is a test comment"}

    # Put a comment on the followup request
    status, data = api(
        "PUT",
        f"followup_request/{request_id}/comment",
        data=request_data,
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    # Check that the comment is now set
    status, data = api("GET", f"followup_request/{request_id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["comment"] == "This is a test comment"

    # Check if comment can be set to empty
    request_data = {"comment": ""}

    # Put an empty comment on the followup request
    status, data = api(
        "PUT",
        f"followup_request/{request_id}/comment",
        data=request_data,
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"

    # Check that the comment is now set to empty
    status, data = api("GET", f"followup_request/{request_id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["comment"] is None
