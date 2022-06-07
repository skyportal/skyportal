from skyportal.tests import api


def test_super_user_post_allocation(
    sedm, public_group, public_group2, super_admin_token
):

    request_data = {
        'group_id': public_group.id,
        'instrument_id': sedm.id,
        'pi': 'Shri Kulkarni',
        'hours_allocated': 200,
        'start_date': '3021-02-27T00:00:00',
        'end_date': '3021-07-20T00:00:00',
        'proposal_id': 'COO-2020A-P01',
        'default_share_group_ids': [public_group.id, public_group2.id],
    }

    status, data = api('POST', 'allocation', data=request_data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    id = data['data']['id']

    status, data = api('GET', f'allocation/{id}', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    for key in request_data:
        assert data['data'][key] == request_data[key]


def test_super_user_modify_allocation(sedm, public_group, super_admin_token):

    request_data = {
        'group_id': public_group.id,
        'instrument_id': sedm.id,
        'pi': 'Shri Kulkarni',
        'hours_allocated': 200,
        'start_date': '3021-02-27T00:00:00',
        'end_date': '3021-07-20T00:00:00',
        'proposal_id': 'COO-2020A-P01',
    }

    status, data = api('POST', 'allocation', data=request_data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    id = data['data']['id']

    status, data = api('GET', f'allocation/{id}', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    for key in request_data:
        assert data['data'][key] == request_data[key]

    request2_data = {'proposal_id': 'COO-2020A-P02'}

    status, data = api(
        'PUT', f'allocation/{id}', data=request2_data, token=super_admin_token
    )
    assert status == 200

    status, data = api('GET', f'allocation/{id}', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    request_data.update(request2_data)
    for key in request_data:
        assert data['data'][key] == request_data[key]


def test_read_only_user_cannot_get_unowned_allocation(
    view_only_token, super_admin_token, sedm, public_group2
):

    request_data = {
        'group_id': public_group2.id,
        'instrument_id': sedm.id,
        'pi': 'Shri Kulkarni',
        'hours_allocated': 200,
        'start_date': '3021-02-27T00:00:00',
        'end_date': '3021-07-20T00:00:00',
        'proposal_id': 'COO-2020A-P01',
    }

    status, data = api('POST', 'allocation', data=request_data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    id = data['data']['id']

    status, data = api('GET', f'allocation/{id}', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    for key in request_data:
        assert data['data'][key] == request_data[key]

    status, data = api('GET', f'allocation/{id}', token=view_only_token)
    assert status == 400
    assert data['status'] == 'error'


def test_read_only_user_get_invalid_allocation_id(view_only_token):

    status, data = api('GET', f'allocation/{-1}', token=view_only_token)
    assert status == 400
    assert data['status'] == 'error'


def test_delete_allocation_cascades_to_requests(
    public_group, public_source, super_admin_token, sedm
):
    request_data = {
        'group_id': public_group.id,
        'instrument_id': sedm.id,
        'pi': 'Shri Kulkarni',
        'hours_allocated': 200,
        'start_date': '3021-02-27T00:00:00',
        'end_date': '3021-07-20T00:00:00',
        'proposal_id': 'COO-2020A-P01',
    }

    status, data = api('POST', 'allocation', data=request_data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    allocation_id = data['data']['id']

    request_data = {
        'allocation_id': allocation_id,
        'obj_id': public_source.id,
        'payload': {
            'priority': 5,
            'start_date': '3020-09-01',
            'end_date': '3022-09-01',
            'observation_type': 'IFU',
        },
    }

    status, data = api(
        'POST', 'followup_request', data=request_data, token=super_admin_token
    )
    assert status == 200
    assert data['status'] == 'success'
    request_id = data['data']['id']

    status, data = api('GET', f'followup_request/{request_id}', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    status, data = api("DELETE", f"allocation/{allocation_id}", token=super_admin_token)
    assert status == 200
    assert data['status'] == "success"

    status, data = api('GET', f'followup_request/{request_id}', token=super_admin_token)
    assert status == 400
    assert "Could not retrieve followup request" in data['message']
