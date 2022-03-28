from skyportal.tests import api
from datetime import date, timedelta
import uuid


def test_shift(public_group, super_admin_token, view_only_token, super_admin_user):

    name = str(uuid.uuid4())
    start_date = date.today().strftime("%Y-%m-%dT%H:%M:%S")
    end_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
    request_data = {
        'name': name,
        'group_id': public_group.id,
        'start_date': start_date,
        'end_date': end_date,
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

    assert any([request_data['name'] == s['name'] for s in data["data"]])
    assert any([request_data['start_date'] == s['start_date'] for s in data["data"]])
    assert any([request_data['end_date'] == s['end_date'] for s in data["data"]])

    assert any(
        [
            len([s for s in s['users'] if s['id'] == super_admin_user.id]) == 1
            for s in data['data']
        ]
    )
