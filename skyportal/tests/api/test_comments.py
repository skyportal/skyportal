from skyportal.tests import api


def test_add_and_retrieve_comment(comment_token, public_source):
    status, data = api('POST', 'comment', data={'source_id': public_source.id,
                                                'text': 'Comment text'},
                       token=comment_token)
    assert status == 200
    comment_id = data['data']['comment_id']

    status, data = api('GET', f'comment/{comment_id}', token=comment_token)

    assert status == 200
    assert data['data']['comment']['text'] == 'Comment text'
