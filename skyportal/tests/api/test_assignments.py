from skyportal.tests import api


def test_token_user_post_classical_followup_request(
    red_transients_run, public_source, upload_data_token
):
    request_data = {
        'run_id': red_transients_run.id,
        'obj_id': public_source.id,
        'priority': '5',
        'comment': 'Please take spectrum only below airmass 1.5',
    }

    status, data = api('POST', 'assignment', data=request_data, token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    id = data['data']['id']

    status, data = api('GET', f'assignment/{id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'

    for key in request_data:
        assert data['data'][key] == request_data[key]


def test_token_user_delete_owned_assignment(
    red_transients_run, public_source, upload_data_token
):

    request_data = {
        'run_id': red_transients_run.id,
        'obj_id': public_source.id,
        'priority': '5',
        'comment': 'Please take spectrum only below airmass 1.5',
    }

    status, data = api('POST', 'assignment', data=request_data, token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    id = data['data']['id']

    status, data = api('DELETE', f'assignment/{id}', token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'


def test_regular_user_delete_super_admin_assignment(
    red_transients_run, public_source, upload_data_token, super_admin_token
):

    request_data = {
        'run_id': red_transients_run.id,
        'obj_id': public_source.id,
        'priority': '5',
        'comment': 'Please take spectrum only below airmass 1.5',
    }

    status, data = api('POST', 'assignment', data=request_data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    id = data['data']['id']

    status, data = api('DELETE', f'assignment/{id}', token=upload_data_token)
    assert status == 400
    assert data['status'] == 'error'


def test_group1_user_cannot_see_group2_assignment(
    red_transients_run,
    public_source_group2,
    public_source,
    super_admin_token,
    view_only_token,
):

    request_data = {
        'run_id': red_transients_run.id,
        'obj_id': public_source_group2.id,
        'priority': '5',
        'comment': 'Please take spectrum only below airmass 1.5',
    }

    status, data = api('POST', 'assignment', data=request_data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    id = data['data']['id']

    request_data = {
        'run_id': red_transients_run.id,
        'obj_id': public_source.id,
        'priority': '5',
        'comment': 'Please take spectrum only below airmass 1.5',
    }

    status, data = api('POST', 'assignment', data=request_data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    status, data = api('GET', f'assignment/{id}', token=view_only_token)
    assert status == 400
    assert data['status'] == 'error'

    status, data = api('GET', f'assignment/', token=view_only_token)
    assert status == 200
    assert public_source_group2.id not in [a['id'] for a in data['data']]
