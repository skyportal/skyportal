import os

from skyportal.tests import api


def test_add_and_retrieve_comment_group_id(
    comment_token, upload_data_token, public_group, super_admin_token
):

    datafile = f'{os.path.dirname(__file__)}/../data/GW190425_initial.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    gcnevent_id = data['data']['gcnevent_id']

    status, data = api(
        'POST',
        f'gcn_event/{gcnevent_id}/comments',
        data={
            'text': 'Comment text',
            'group_ids': [public_group.id],
        },
        token=comment_token,
    )
    assert status == 200
    comment_id = data['data']['comment_id']

    status, data = api(
        'GET', f'gcn_event/{gcnevent_id}/comments/{comment_id}', token=comment_token
    )

    assert status == 200
    assert data['data']['text'] == 'Comment text'

    # delete the event
    status, data = api(
        'DELETE', 'gcn_event/2019-04-25T08:18:05', token=super_admin_token
    )


def test_delete_comment(comment_token, public_group, super_admin_token):

    datafile = f'{os.path.dirname(__file__)}/../data/GW190425_initial.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    gcnevent_id = data['data']['gcnevent_id']

    status, data = api(
        'POST',
        f'gcn_event/{gcnevent_id}/comments',
        data={'text': 'Comment text'},
        token=comment_token,
    )
    assert status == 200
    comment_id = data['data']['comment_id']

    status, data = api(
        'GET', f'gcn_event/{gcnevent_id}/comments/{comment_id}', token=comment_token
    )
    assert status == 200
    assert data['data']['text'] == 'Comment text'

    # try to delete using the wrong object ID
    status, data = api(
        'DELETE',
        f'gcn_event/{gcnevent_id}zzz/comments/{comment_id}',
        token=comment_token,
    )
    assert status == 400
    assert (
        "Comment resource ID does not match resource ID given in path"
        in data["message"]
    )

    status, data = api(
        'DELETE',
        f'gcn_event/{gcnevent_id}/comments/{comment_id}',
        token=comment_token,
    )
    assert status == 200

    status, data = api(
        'GET', f'gcn_event/{gcnevent_id}/comments/{comment_id}', token=comment_token
    )
    assert status == 403

    # delete the event
    status, data = api(
        'DELETE', 'gcn_event/2019-04-25T08:18:05', token=super_admin_token
    )
