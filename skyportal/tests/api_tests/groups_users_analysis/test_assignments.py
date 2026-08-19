from skyportal_py.assignments import AssignmentPost

from skyportal.tests import client


def test_token_user_post_classical_followup_request(
    red_transients_run, public_source, upload_data_token
):
    request_data = {
        "run_id": red_transients_run.id,
        "obj_id": public_source.id,
        "priority": "5",
        "comment": "Please take spectrum only below airmass 1.5",
    }

    sp = client(upload_data_token)
    id = sp.post_assignment(AssignmentPost(**request_data)).id

    assignment = sp.fetch_assignment(id)
    for key in request_data:
        assert getattr(assignment, key) == request_data[key]


def test_token_user_delete_owned_assignment(
    red_transients_run, public_source, upload_data_token
):
    request_data = {
        "run_id": red_transients_run.id,
        "obj_id": public_source.id,
        "priority": "5",
        "comment": "Please take spectrum only below airmass 1.5",
    }

    sp = client(upload_data_token)
    id = sp.post_assignment(AssignmentPost(**request_data)).id

    sp.delete_assignment(id)


def test_regular_user_can_delete_super_admin_assignment(
    red_transients_run, public_source, upload_data_token, super_admin_token
):
    request_data = {
        "run_id": red_transients_run.id,
        "obj_id": public_source.id,
        "priority": "5",
        "comment": "Please take spectrum only below airmass 1.5",
    }

    id = client(super_admin_token).post_assignment(AssignmentPost(**request_data)).id

    client(upload_data_token).delete_assignment(id)


def test_regular_user_can_modify_super_admin_assignment(
    red_transients_run,
    public_source,
    upload_data_token,
    super_admin_token,
    user,
    super_admin_user,
):
    request_data = {
        "run_id": red_transients_run.id,
        "obj_id": public_source.id,
        "priority": "5",
        "comment": "Please take spectrum only below airmass 1.5",
    }

    id = client(super_admin_token).post_assignment(AssignmentPost(**request_data)).id

    sp = client(upload_data_token)
    sp.update_assignment(
        id,
        priority="4",
        comment="Please take spectrum only below airmass 1.5",
    )

    assignment = sp.fetch_assignment(id)
    assert assignment.last_modified_by_id == user.id
    assert assignment.requester_id == super_admin_user.id


def test_group1_user_can_see_group2_assignment(
    red_transients_run,
    public_source_group2,
    public_source,
    super_admin_token,
    view_only_token,
):
    request_data = {
        "run_id": red_transients_run.id,
        "obj_id": public_source_group2.id,
        "priority": "5",
        "comment": "Please take spectrum only below airmass 1.5",
    }

    sp_admin = client(super_admin_token)
    id = sp_admin.post_assignment(AssignmentPost(**request_data)).id

    request_data = {
        "run_id": red_transients_run.id,
        "obj_id": public_source.id,
        "priority": "5",
        "comment": "Please take spectrum only below airmass 1.5",
    }

    sp_admin.post_assignment(AssignmentPost(**request_data))

    client(view_only_token).fetch_assignment(id)
