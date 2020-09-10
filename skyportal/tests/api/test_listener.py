from .. import api


def test_listener_acl_events(sedm):
    original_classname = sedm.listener_classname
    acl = sedm.listener_acl
    assert acl is not None
    sedm.listener_classname = None
    new_acl = sedm.listener_acl
    assert new_acl is None
    sedm.listener_classname = original_classname
    final_acl = sedm.listener_acl
    assert final_acl is acl


def test_post_status_update_to_sedm_request(
    public_source_followup_request, sedm_listener_token, view_only_token
):

    new_status = 'observed successfully'
    status, data = api(
        'POST',
        'facility',
        data={
            'followup_request_id': public_source_followup_request.id,
            'new_status': new_status,
        },
        token=sedm_listener_token,
    )

    assert status == 200

    status, data = api(
        'GET',
        f'followup_request/{public_source_followup_request.id}',
        token=view_only_token,
    )

    assert status == 200
    assert data['data']['status'] == new_status

    status, data = api(
        'POST',
        'facility',
        data={
            'followup_request_id': public_source_followup_request.id,
            'new_status': 'status that should be rejected due to lack of ACL',
        },
        token=sedm_listener_token,
    )

    assert status == 400

    status, data = api(
        'GET',
        f'followup_request/{public_source_followup_request.id}',
        token=view_only_token,
    )

    assert status == 200
    assert data['data']['status'] == new_status
