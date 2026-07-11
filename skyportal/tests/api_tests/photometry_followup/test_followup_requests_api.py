import uuid

from skyportal.tests import api

from ....utils.naive_datetime import utcnow_naive


def test_token_user_post_robotic_followup_request(
    public_group_sedm_allocation, public_source, upload_data_token
):
    request_data = {
        "allocation_id": public_group_sedm_allocation.id,
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


def test_gemini_followup_blank_note_title(
    public_group_gemini_allocation, public_source, upload_data_token
):
    # Regression guard: a blank note title must not crash the Gemini submit.
    # An unset optional param became None and yarl rejected it in `params=`.
    request_data = {
        "allocation_id": public_group_gemini_allocation.id,
        "obj_id": public_source.id,
        "payload": {
            "template_ids": "21",
            "start_date": "2026-05-08 04:00:00",
            "end_date": "2026-05-08 05:00:00",
            "l_exptime": 0,
            "l_elmin": 1.0,
            "l_elmax": 1.6,
            "note_title": "",
        },
    }

    status, data = api(
        "POST", "followup_request", data=request_data, token=upload_data_token
    )
    assert status == 200, data
    assert data["status"] == "success"


def test_token_user_delete_owned_followup_request(
    public_group_generic_allocation, public_source, upload_data_token
):
    request_data = {
        "allocation_id": public_group_generic_allocation.id,
        "obj_id": public_source.id,
        "payload": {
            "priority": 5,
            "start_date": "3010-09-01",
            "end_date": "3012-09-01",
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
            "start_date": "3010-09-01",
            "end_date": "3012-09-01",
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
            "start_date": "3010-09-01",
            "end_date": "3012-09-01",
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
            "start_date": "3010-09-01",
            "end_date": "3012-09-01",
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
            "start_date": "3010-09-01",
            "end_date": "3012-09-01",
            "observation_type": "IFU",
            "exposure_time": 300,
            "maximum_airmass": 2,
            "maximum_fwhm": 1.2,
        },
    }

    time_before_post = utcnow_naive().isoformat()
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

    time_after_post = utcnow_naive().isoformat()

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


def _default_followup_payload(public_group, allocation, **extra):
    data = {
        "allocation_id": allocation.id,
        "default_followup_name": str(uuid.uuid4()),
        "source_filter": {"name": ".*", "group_id": public_group.id},
        "target_group_ids": [public_group.id],
        "payload": {
            "priority": 5,
            "observation_type": "IFU",
            "exposure_time": 300,
            "maximum_airmass": 2,
            "maximum_fwhm": 1.2,
        },
    }
    data.update(extra)
    return data


def test_default_followup_request_stores_constraints(
    public_group, public_group_sedm_allocation, super_admin_token
):
    request_data = _default_followup_payload(
        public_group,
        public_group_sedm_allocation,
        not_if_classified=True,
        not_if_duplicates=True,
        radius=2.0,
        priority_order="desc",
        validity_days=3,
        comment="auto-trigger test",
        implements_update=False,
    )

    status, data = api(
        "POST",
        "default_followup_request",
        data=request_data,
        token=super_admin_token,
    )
    assert status == 200, data
    new_id = data["data"]["id"]

    status, data = api("GET", "default_followup_request", token=super_admin_token)
    assert status == 200
    match = next(r for r in data["data"] if r["id"] == new_id)
    constraints = match["constraints"]
    assert constraints is not None
    assert constraints["not_if_classified"] is True
    assert constraints["not_if_duplicates"] is True
    # radius is always added alongside any other constraint
    assert constraints["radius"] == 2.0
    # constraints not supplied are absent (not defaulted)
    assert "not_if_spectra_exist" not in constraints
    # priority_order / validity_days / comment are stored for the auto-trigger path
    assert match["priority_order"] == "desc"
    assert match["validity_days"] == 3
    assert match["comment"] == "auto-trigger test"
    assert match["implements_update"] is False


def test_default_followup_request_without_constraints_is_null(
    public_group, public_group_sedm_allocation, super_admin_token
):
    request_data = _default_followup_payload(public_group, public_group_sedm_allocation)

    status, data = api(
        "POST",
        "default_followup_request",
        data=request_data,
        token=super_admin_token,
    )
    assert status == 200, data
    new_id = data["data"]["id"]

    status, data = api("GET", "default_followup_request", token=super_admin_token)
    assert status == 200
    match = next(r for r in data["data"] if r["id"] == new_id)
    # no constraint keys supplied -> stored as null (always submit)
    assert match["constraints"] is None
