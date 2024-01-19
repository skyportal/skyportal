from skyportal.tests import api


def test_post_and_delete_tns_robot(public_group, super_admin_token):
    request_data = {
        'group_id': public_group.id,
        'bot_name': 'test_bot',
        'bot_id': 10,
        'source_group_id': 200,
        '_altdata': '{"api_key": "test_key"}',
    }

    status, data = api('POST', 'tns_robot', data=request_data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    id = data['data']['id']

    status, data = api('GET', f'tns_robot/{id}', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    for key in request_data:
        if key == '_altdata':
            continue
        assert data['data'][key] == request_data[key]

    status, data = api("DELETE", f"tns_robot/{id}", token=super_admin_token)
    assert status == 200
    assert data['status'] == "success"
