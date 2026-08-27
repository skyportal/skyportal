"""End-to-end: does an assignment now carry run + requester, and nothing else?"""

import datetime

from skyportal.tests import api


def test_assignment_carries_its_run_and_requester(
    public_source, lris, observing_run_token, red_transients_group, super_admin_token
):
    status, data = api(
        "POST",
        "observing_run",
        data={
            "instrument_id": lris.id,
            "pi": "D. Goldstein",
            "observers": "D. Goldstein",
            "group_id": red_transients_group.id,
            "calendar_date": str(datetime.date.today() + datetime.timedelta(days=10)),
        },
        token=observing_run_token,
    )
    assert status == 200, data
    run_id = data["data"]["id"]

    status, data = api(
        "POST",
        "assignment",
        data={"obj_id": public_source.id, "run_id": run_id, "priority": "1"},
        token=super_admin_token,
    )
    assert status == 200, data

    status, data = api("GET", f"sources/{public_source.id}", token=super_admin_token)
    assert status == 200, data
    assignments = data["data"]["assignments"]
    assert len(assignments) == 1, assignments
    a = assignments[0]

    assert a["run"]["id"] == run_id, "the run must travel with the assignment"
    assert a["run"]["calendar_date"], a["run"]
    assert a["requester"]["username"], "the requester's name must travel with it"
    # The whole point: no contact details or preferences on a readable page.
    for leaked in ("contact_email", "contact_phone", "oauth_uid", "preferences"):
        assert leaked not in a["requester"], f"{leaked} leaked: {a['requester']}"
