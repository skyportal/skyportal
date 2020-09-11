from skyportal.tests import api


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
        token=view_only_token,
    )

    assert status == 400

    status, data = api(
        'GET',
        f'followup_request/{public_source_followup_request.id}',
        token=view_only_token,
    )

    assert status == 200
    assert data['data']['status'] == new_status


def test_post_poorly_formatted_sedm_message(
    public_source_followup_request, sedm_listener_token
):

    new_status = 'observed successfully'
    status, data = api(
        'POST',
        'facility',
        data={
            'followup_request_id': public_source_followup_request.id,
            'new_status': new_status,
            'superfluous_field': 'abcd',
        },
        token=sedm_listener_token,
    )

    assert status == 400
