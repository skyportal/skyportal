from skyportal.tests import api


def test_shift(public_group, super_admin_token, super_admin_user):

    request_data = {
        'group_id': public_group.id,
        'start_date': '3021-02-27T00:00:00',
        'end_date': '3021-07-20T00:00:00',
    }

    status, data = api('POST', 'shift', data=request_data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    status, data = api('GET', f'shift/{public_group.id}', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    assert any([request_data['start_date'] == s['start_date'] for s in data["data"]])

    assert any([request_data['end_date'] == s['end_date'] for s in data["data"]])
