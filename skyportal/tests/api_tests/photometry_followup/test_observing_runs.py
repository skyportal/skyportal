import datetime

import pytest

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


def test_observing_run_assignment_last_detection(
    public_assignment,
    public_source,
    public_group,
    view_only_token,
    upload_data_token,
    ztf_camera,
):
    """Facilities size exposures from the target's brightness, so the run
    payload carries the last detection alongside each assignment."""
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": str(public_source.id),
            "mjd": 61254.4,
            "instrument_id": ztf_camera.id,
            "mag": 18.9,
            "magerr": 0.07,
            "limiting_mag": 22.3,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200, data

    status, data = api(
        "GET", f"observing_run/{public_assignment.run.id}", token=view_only_token
    )
    assert status == 200
    assignment = data["data"]["assignments"][0]
    assert assignment["last_detected_mag"] == pytest.approx(18.9, abs=0.01)
    assert assignment["last_detected_filter"] == "ztfg"
    assert assignment["last_detected_mjd"] == pytest.approx(61254.4)


def test_upcoming_only_excludes_finished_runs(
    lris, observing_run_token, red_transients_group
):
    """The source page offers runs to assign a target to, and a target cannot be
    assigned to a run that is over. Filtering server-side keeps the whole run
    history (megabytes of it) off that page."""
    base = {
        "instrument_id": lris.id,
        "pi": "Danny Goldstein",
        "observers": "D. Goldstein, P. Nugent",
        "group_id": red_transients_group.id,
    }

    past = dict(base, calendar_date="2020-02-16")
    future = dict(
        base, calendar_date=str(datetime.date.today() + datetime.timedelta(days=30))
    )

    status, data = api("POST", "observing_run", data=past, token=observing_run_token)
    assert status == 200, data
    past_id = data["data"]["id"]

    status, data = api("POST", "observing_run", data=future, token=observing_run_token)
    assert status == 200, data
    future_id = data["data"]["id"]

    status, data = api("GET", "observing_run", token=observing_run_token)
    assert status == 200, data
    all_ids = {run["id"] for run in data["data"]}
    assert {past_id, future_id} <= all_ids

    status, data = api(
        "GET", "observing_run?upcomingOnly=true", token=observing_run_token
    )
    assert status == 200, data
    upcoming_ids = {run["id"] for run in data["data"]}
    assert future_id in upcoming_ids
    assert past_id not in upcoming_ids


def test_an_unknown_query_parameter_is_rejected(observing_run_token):
    """extra="forbid" on the query model: a typo should say so, not silently
    return everything."""
    status, data = api("GET", "observing_run?upcoming=true", token=observing_run_token)
    assert status == 400, data


def test_a_run_is_visible_to_everyone_by_default(
    lris, observing_run_token, red_transients_group, view_only_token
):
    """Runs default to the sitewide group, which is what they were visible to
    before they became group-scoped."""
    status, data = api(
        "POST",
        "observing_run",
        data={
            "instrument_id": lris.id,
            "pi": "D. Goldstein",
            "observers": "D. Goldstein",
            "group_id": red_transients_group.id,
            "calendar_date": "2020-02-16",
        },
        token=observing_run_token,
    )
    assert status == 200, data
    run_id = data["data"]["id"]

    status, data = api("GET", f"observing_run/{run_id}", token=view_only_token)
    assert status == 200, data


def test_a_run_can_be_kept_to_one_group(
    lris,
    super_admin_token,
    public_group2,
    upload_data_token_two_groups,
    view_only_token,
):
    """A group that does not want its plans read across the instance narrows
    the run to itself; everyone else stops seeing it, target list included.

    view_only_token's user is not in public_group2; the two-groups user is.
    """
    status, data = api(
        "POST",
        "observing_run",
        data={
            "instrument_id": lris.id,
            "pi": "D. Goldstein",
            "observers": "D. Goldstein",
            "group_id": public_group2.id,
            "group_ids": [public_group2.id],
            "calendar_date": "2020-02-16",
        },
        token=super_admin_token,
    )
    assert status == 200, data
    run_id = data["data"]["id"]

    # A member of the group it was shared with still sees it ...
    status, data = api(
        "GET", f"observing_run/{run_id}", token=upload_data_token_two_groups
    )
    assert status == 200, data

    # ... and it no longer appears for anyone else.
    status, data = api("GET", f"observing_run/{run_id}", token=view_only_token)
    assert status == 400, data

    status, data = api("GET", "observing_run", token=view_only_token)
    assert status == 200, data
    assert run_id not in [run["id"] for run in data["data"]]
