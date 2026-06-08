from skyportal.tests import api


def test_token_user_add_new_observing_run(
    lris, observing_run_token, red_transients_group
):
    run_details = {
        "instrument_id": lris.id,
        "pi": "Danny Goldstein",
        "observers": "D. Goldstein, P. Nugent",
        "group_id": red_transients_group.id,
        "calendar_date": "2020-02-16",
    }

    status, data = api(
        "POST", "observing_run", data=run_details, token=observing_run_token
    )
    assert status == 200
    assert data["status"] == "success"
    run_id = data["data"]["id"]

    status, data = api("GET", f"observing_run/{run_id}", token=observing_run_token)

    assert status == 200
    assert data["status"] == "success"
    for key in run_details:
        assert data["data"][key] == run_details[key]


def test_super_admin_user_delete_nonowned_observing_run(
    lris, observing_run_token, super_admin_token, red_transients_group
):
    run_details = {
        "instrument_id": lris.id,
        "pi": "Danny Goldstein",
        "observers": "D. Goldstein, P. Nugent",
        "group_id": red_transients_group.id,
        "calendar_date": "2020-02-16",
    }

    status, data = api(
        "POST", "observing_run", data=run_details, token=observing_run_token
    )
    assert status == 200
    assert data["status"] == "success"
    run_id = data["data"]["id"]

    status, data = api("DELETE", f"observing_run/{run_id}", token=super_admin_token)

    assert status == 200
    assert data["status"] == "success"


def test_unauthorized_user_delete_nonowned_observing_run(
    lris, observing_run_token, manage_sources_token, red_transients_group
):
    run_details = {
        "instrument_id": lris.id,
        "pi": "Danny Goldstein",
        "observers": "D. Goldstein, P. Nugent",
        "group_id": red_transients_group.id,
        "calendar_date": "2020-02-16",
    }

    status, data = api(
        "POST", "observing_run", data=run_details, token=observing_run_token
    )
    assert status == 200
    assert data["status"] == "success"
    run_id = data["data"]["id"]

    status, data = api("DELETE", f"observing_run/{run_id}", token=manage_sources_token)

    assert status == 400
    assert data["status"] == "error"


def test_authorized_user_modify_owned_observing_run(
    lris, observing_run_token, red_transients_group
):
    run_details = {
        "instrument_id": lris.id,
        "pi": "Danny Goldstein",
        "observers": "D. Goldstein, P. Nugent",
        "group_id": red_transients_group.id,
        "calendar_date": "2020-02-16",
    }

    status, data = api(
        "POST", "observing_run", data=run_details, token=observing_run_token
    )
    assert status == 200
    assert data["status"] == "success"
    run_id = data["data"]["id"]

    new_date = {"calendar_date": "2020-02-17"}
    run_details.update(new_date)

    status, data = api(
        "PUT", f"observing_run/{run_id}", data=new_date, token=observing_run_token
    )

    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"observing_run/{run_id}", token=observing_run_token)

    assert status == 200
    assert data["status"] == "success"
    for key in run_details:
        assert data["data"][key] == run_details[key]


def test_unauthorized_user_modify_unowned_observing_run(
    lris, observing_run_token, manage_sources_token, red_transients_group
):
    run_details = {
        "instrument_id": lris.id,
        "pi": "Danny Goldstein",
        "observers": "D. Goldstein, P. Nugent",
        "group_id": red_transients_group.id,
        "calendar_date": "2020-02-16",
    }

    status, data = api(
        "POST", "observing_run", data=run_details, token=observing_run_token
    )
    assert status == 200
    assert data["status"] == "success"
    run_id = data["data"]["id"]

    new_date = {"calendar_date": "2020-02-17"}
    run_details.update(new_date)

    status, data = api(
        "PUT", f"observing_run/{run_id}", data=new_date, token=manage_sources_token
    )

    assert status == 401
    assert data["status"] == "error"


def test_observing_run_assignment_group_names(
    public_assignment,
    public_source,
    view_only_token,
    public_group,
    public_group2,
    upload_data_token_two_groups,
):
    # Save the obj associated with the public_assignment to a group the run
    # owner is not a part of
    status, data = api(
        "POST",
        "sources",
        data={
            "id": public_source.id,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "group_ids": [public_group2.id],
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data["status"] == "success"

    # Get the observing run and associated assignments and check that public_group2
    # is not in the accessible_group_ids
    status, data = api(
        "GET", f"observing_run/{public_assignment.run.id}", token=view_only_token
    )

    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]["assignments"]) == 1
    assert (
        public_group2.name
        not in data["data"]["assignments"][0]["accessible_group_names"]
    )
