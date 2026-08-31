"""What another group has scheduled on a source, before any data exists.

`data_availability` describes what has already been taken. This describes what
is about to be, so two groups do not spend the same night on the same target.
Like that endpoint it reads past the access controls, so these pin what it may
say (instrument, who to ask, the state of the request) and what it may not
(the payload: exposure times, airmass limits, the science being attempted).
"""

from skyportal.tests import api

PAYLOAD = {
    "priority": 5,
    "start_date": "3010-09-01",
    "end_date": "3012-09-01",
    "observation_type": "IFU",
    "exposure_time": 300,
    "maximum_airmass": 2,
    "maximum_fwhm": 1.2,
}


def scheduled(obj_id, token):
    status, data = api("GET", f"sources/{obj_id}/scheduled_observations", token=token)
    assert status == 200, data
    return data["data"]["followup_requests"]


def request_followup(obj_id, allocation_id, token, payload=None):
    status, data = api(
        "POST",
        "followup_request",
        data={
            "allocation_id": allocation_id,
            "obj_id": obj_id,
            "payload": payload or PAYLOAD,
        },
        token=token,
    )
    assert status == 200, data
    return data["data"]["id"]


def test_another_groups_request_is_advertised_without_its_payload(
    public_source_two_groups,
    public_group2,
    public_group2_sedm_allocation,
    upload_data_token_two_groups,
    view_only_token,
):
    obj_id = public_source_two_groups.id
    assert scheduled(obj_id, view_only_token) == []

    request_followup(
        obj_id, public_group2_sedm_allocation.id, upload_data_token_two_groups
    )

    requests = scheduled(obj_id, view_only_token)
    assert len(requests) == 1, requests
    request = requests[0]
    # Enough to avoid duplicating the night, and to know who to talk to.
    assert request["group_name"] == public_group2.name
    assert request["instrument_name"]
    assert request["requester"]["username"]
    assert request["status"]
    # Nothing about what they intend to do with the time.
    assert "payload" not in request
    for field in ("exposure_time", "observation_type", "priority"):
        assert field not in request


def test_a_group_that_does_not_advertise_its_data_does_not_advertise_its_plans(
    public_source_two_groups,
    public_group2,
    public_group2_sedm_allocation,
    upload_data_token_two_groups,
    view_only_token,
    super_admin_token,
):
    obj_id = public_source_two_groups.id
    request_followup(
        obj_id, public_group2_sedm_allocation.id, upload_data_token_two_groups
    )
    assert len(scheduled(obj_id, view_only_token)) == 1

    status, data = api(
        "PUT",
        f"groups/{public_group2.id}",
        data={"name": public_group2.name, "discoverable_data": False},
        token=super_admin_token,
    )
    assert status == 200, data

    assert scheduled(obj_id, view_only_token) == []


def test_a_request_you_can_already_read_is_not_repeated_back_to_you(
    public_source_two_groups,
    public_group2_sedm_allocation,
    upload_data_token_two_groups,
):
    """The endpoint describes only what the caller cannot already see."""
    obj_id = public_source_two_groups.id
    request_followup(
        obj_id, public_group2_sedm_allocation.id, upload_data_token_two_groups
    )

    assert scheduled(obj_id, upload_data_token_two_groups) == []


def duplicates(token):
    status, data = api("GET", "duplicate_scheduling", token=token)
    assert status == 200, data
    return data["data"]


def test_a_collision_with_another_groups_request_is_reported(
    public_source_two_groups,
    public_group,
    public_group2,
    public_group_sedm_allocation,
    public_group2_sedm_allocation,
    upload_data_token,
    upload_data_token_two_groups,
):
    """Two groups scheduling the same object is the waste this is meant to
    catch, and it has to be caught before the night, not after."""
    obj_id = public_source_two_groups.id

    request_followup(obj_id, public_group_sedm_allocation.id, upload_data_token)
    assert duplicates(upload_data_token) == []

    # Another group schedules the same object.
    request_followup(
        obj_id, public_group2_sedm_allocation.id, upload_data_token_two_groups
    )

    collisions = duplicates(upload_data_token)
    assert len(collisions) == 1, collisions
    assert collisions[0]["obj_id"] == obj_id
    assert collisions[0]["group_name"] == public_group2.name
    assert collisions[0]["instrument_name"]


def test_your_own_second_request_is_not_a_collision(
    public_source_two_groups,
    public_group_sedm_allocation,
    upload_data_token,
):
    """Scheduling the same object twice yourself is a choice, not a clash."""
    obj_id = public_source_two_groups.id
    request_followup(obj_id, public_group_sedm_allocation.id, upload_data_token)
    request_followup(obj_id, public_group_sedm_allocation.id, upload_data_token)

    assert duplicates(upload_data_token) == []


def test_requests_months_apart_are_not_a_collision(
    public_source_two_groups,
    public_group_sedm_allocation,
    public_group2_sedm_allocation,
    upload_data_token,
    upload_data_token_two_groups,
):
    """Both groups hold the object, but not on the same nights: nothing to
    reconcile, and a false alarm here trains people to ignore the real ones."""
    obj_id = public_source_two_groups.id

    request_followup(
        obj_id,
        public_group_sedm_allocation.id,
        upload_data_token,
        payload={**PAYLOAD, "start_date": "3010-01-01", "end_date": "3010-02-01"},
    )
    request_followup(
        obj_id,
        public_group2_sedm_allocation.id,
        upload_data_token_two_groups,
        payload={**PAYLOAD, "start_date": "3011-06-01", "end_date": "3011-07-01"},
    )

    assert duplicates(upload_data_token) == []


def test_overlapping_windows_are_a_collision(
    public_source_two_groups,
    public_group2,
    public_group_sedm_allocation,
    public_group2_sedm_allocation,
    upload_data_token,
    upload_data_token_two_groups,
):
    obj_id = public_source_two_groups.id

    request_followup(
        obj_id,
        public_group_sedm_allocation.id,
        upload_data_token,
        payload={**PAYLOAD, "start_date": "3010-01-01", "end_date": "3010-03-01"},
    )
    request_followup(
        obj_id,
        public_group2_sedm_allocation.id,
        upload_data_token_two_groups,
        payload={**PAYLOAD, "start_date": "3010-02-01", "end_date": "3010-04-01"},
    )

    collisions = duplicates(upload_data_token)
    assert len(collisions) == 1, collisions
    assert collisions[0]["group_name"] == public_group2.name
