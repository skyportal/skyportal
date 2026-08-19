import pytest
from skyportal_py import SkyPortalError

from skyportal.tests import client


def test_post_status_update_to_sedm_request(
    public_source_followup_request, sedm_listener_token, view_only_token
):
    new_status = "observed successfully"
    client(sedm_listener_token).post_facility_message(
        public_source_followup_request.id, {"new_status": new_status}
    )

    followup_request = client(view_only_token).fetch_followup_request(
        public_source_followup_request.id
    )
    assert followup_request.status == new_status


def test_post_status_update_to_request_without_listener_acl(
    public_source_followup_request, view_only_token
):
    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).post_facility_message(
            public_source_followup_request.id,
            {"new_status": "status that should be rejected due to lack of ACL"},
        )
    assert err.value.status_code == 400

    followup_request = client(view_only_token).fetch_followup_request(
        public_source_followup_request.id
    )
    assert followup_request.status == public_source_followup_request.status


def test_post_poorly_formatted_sedm_message(
    public_source_followup_request, sedm_listener_token
):
    new_status = "observed successfully"
    with pytest.raises(SkyPortalError) as err:
        client(sedm_listener_token).post_facility_message(
            public_source_followup_request.id,
            {"new_status": new_status, "superfluous_field": "abcd"},
        )
    assert err.value.status_code == 500


def test_post_message_about_unowned_request(
    public_source_group2_followup_request, sedm_listener_token, super_admin_token
):
    client(sedm_listener_token).post_facility_message(
        public_source_group2_followup_request.id, {"new_status": "ok"}
    )

    followup_request = client(super_admin_token).fetch_followup_request(
        public_source_group2_followup_request.id
    )
    assert followup_request.status == "ok"
