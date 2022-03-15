from skyportal.tests import api


def test_shift(public_group, super_admin_token, view_only_token, super_admin_user):

    request_data = {
        'name': 'night shift',
        'group_id': public_group.id,
        'start_date': '3021-02-27T00:00:00',
        'end_date': '3021-07-20T00:00:00',
        'description': 'the Night Shift',
        'shift_admins': [super_admin_user.id],
    }
    status, data = api('POST', 'shifts', data=request_data, token=view_only_token)
    assert status == 401
    assert data['status'] == 'error'

    status, data = api('POST', 'shifts', data=request_data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    status, data = api('GET', f'shifts/{public_group.id}', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    assert any([request_data['start_date'] == s['start_date'] for s in data["data"]])

    assert any([request_data['end_date'] == s['end_date'] for s in data["data"]])
