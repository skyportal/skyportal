from skyportal.tests import api


def test_add_and_retrieve_comment_group_id(
    comment_token,
    public_group,
):

    status, data = api(
        'POST',
        'comments',
        data={
            'text': 'Comment text',
            'group_ids': [public_group.id],
        },
        token=comment_token,
    )
    assert status == 200
    comment_id = data['data']['comment_id']

    status, data = api('GET', f'comments/{comment_id}', token=comment_token)
    assert status == 200
    assert data['data']['text'] == 'Comment text'


def test_delete_comment(comment_token, public_group, super_admin_token):

    status, data = api(
        'POST',
        'comments',
        data={'text': 'Comment text to delete'},
        token=comment_token,
    )
    assert status == 200
    comment_id = data['data']['comment_id']

    status, data = api('GET', f'comments/{comment_id}', token=comment_token)
    assert status == 200
    assert data['data']['text'] == 'Comment text to delete'

    print('comment_id', comment_id)

    # try to delete using the wrong comment ID
    status, data = api(
        'DELETE',
        f'comments/{comment_id}1212',
        token=comment_token,
    )
    assert status == 403
    assert "Could not find any accessible comments." in data["message"]

    status, data = api(
        'DELETE',
        f'comments/{comment_id}',
        token=comment_token,
    )
    assert status == 200
    assert len(data['data']) == 0

    status, data = api('GET', 'comments', token=comment_token)
    print('data', data)
    assert status == 200
    assert data['data'] == []
