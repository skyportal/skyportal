from skyportal.tests import api
from datetime import date, timedelta
import uuid


def test_add_and_retrieve_comment_on_shift(
    public_group, super_admin_token, comment_token, super_admin_user
):
    name = str(uuid.uuid4())
    start_date = date.today().strftime("%Y-%m-%dT%H:%M:%S")
    end_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
    request_data = {
        'name': name,
        'group_id': public_group.id,
        'start_date': start_date,
        'end_date': end_date,
        'description': 'the Test Shift',
        'shift_admins': [super_admin_user.id],
    }

    status, data = api('POST', 'shifts', data=request_data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    shift_id = data['data']['id']

    status, data = api(
        'POST',
        f'shift/{shift_id}/comments',
        data={
            'text': 'Comment on shift text',
            'group_ids': [public_group.id],
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data['status'] == 'success'
    comment_id = data['data']['comment_id']

    status, data = api(
        'GET', f'shift/{shift_id}/comments/{comment_id}', token=comment_token
    )

    assert status == 200
    assert data['data']['text'] == 'Comment on shift text'


def test_delete_comment_on_shift(
    comment_token, public_group, super_admin_token, super_admin_user
):
    name = str(uuid.uuid4())
    start_date = date.today().strftime("%Y-%m-%dT%H:%M:%S")
    end_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
    request_data = {
        'name': name,
        'group_id': public_group.id,
        'start_date': start_date,
        'end_date': end_date,
        'description': 'the Test Shift',
        'shift_admins': [super_admin_user.id],
    }

    status, data = api('POST', 'shifts', data=request_data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    shift_id = data['data']['id']

    status, data = api(
        'POST',
        f'shift/{shift_id}/comments',
        data={
            'text': 'Comment on shift text',
            'group_ids': [public_group.id],
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data['status'] == 'success'
    comment_id = data['data']['comment_id']

    # try to delete using the wrong object ID
    status, data = api(
        'DELETE',
        f'shift/{shift_id}zzz/comments/{comment_id}',
        token=comment_token,
    )
    assert status == 403
    assert "Could not find any accessible comments." in data["message"]

    status, data = api(
        'DELETE',
        f'shift/{shift_id}/comments/{comment_id}',
        token=super_admin_token,
    )
    assert status == 200

    status, data = api(
        'GET', f'shift/{shift_id}/comments/{comment_id}', token=comment_token
    )
    assert status == 403
