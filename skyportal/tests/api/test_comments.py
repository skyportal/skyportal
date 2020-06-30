from skyportal.tests import api


def test_add_and_retrieve_comment_group_id(comment_token, public_source, public_group):
    status, data = api('POST', 'comment', data={'obj_id': public_source.id,
                                                'text': 'Comment text',
                                                'group_ids': [public_group.id]},
                       token=comment_token)
    assert status == 200
    comment_id = data['data']['comment_id']

    status, data = api('GET', f'comment/{comment_id}', token=comment_token)

    assert status == 200
    assert data['data']['text'] == 'Comment text'


def test_add_and_retrieve_comment_no_group_id(comment_token, public_source):
    status, data = api('POST', 'comment', data={'obj_id': public_source.id,
                                                'text': 'Comment text'},
                       token=comment_token)
    assert status == 200
    comment_id = data['data']['comment_id']

    status, data = api('GET', f'comment/{comment_id}', token=comment_token)

    assert status == 200
    assert data['data']['text'] == 'Comment text'


def test_add_and_retrieve_comment_group_access(comment_token_two_groups,
                                               public_source_two_groups,
                                               public_group2, public_group,
                                               comment_token):
    status, data = api('POST', 'comment', data={'obj_id': public_source_two_groups.id,
                                                'text': 'Comment text',
                                                'group_ids': [public_group2.id]},
                       token=comment_token_two_groups)
    assert status == 200
    comment_id = data['data']['comment_id']

    # This token belongs to public_group2
    status, data = api('GET', f'comment/{comment_id}', token=comment_token_two_groups)
    assert status == 200
    assert data['data']['text'] == 'Comment text'

    # This token does not belnog to public_group2
    status, data = api('GET', f'comment/{comment_id}', token=comment_token)
    assert status == 400
    assert data["message"] == "Insufficient permissions."

    # Both tokens should be able to view this comment
    status, data = api('POST', 'comment', data={'obj_id': public_source_two_groups.id,
                                                'text': 'Comment text',
                                                'group_ids': [public_group.id,
                                                              public_group2.id]},
                       token=comment_token_two_groups)
    assert status == 200
    comment_id = data['data']['comment_id']

    status, data = api('GET', f'comment/{comment_id}', token=comment_token_two_groups)
    assert status == 200
    assert data['data']['text'] == 'Comment text'

    status, data = api('GET', f'comment/{comment_id}', token=comment_token)
    assert status == 200
    assert data['data']['text'] == 'Comment text'


def test_update_comment_group_list(comment_token_two_groups,
                                   public_source_two_groups,
                                   public_group2, public_group,
                                   comment_token):
    status, data = api('POST', 'comment', data={'obj_id': public_source_two_groups.id,
                                                'text': 'Comment text',
                                                'group_ids': [public_group2.id]},
                       token=comment_token_two_groups)
    assert status == 200
    comment_id = data['data']['comment_id']

    # This token belongs to public_group2
    status, data = api('GET', f'comment/{comment_id}', token=comment_token_two_groups)
    assert status == 200
    assert data['data']['text'] == 'Comment text'

    # This token does not belnog to public_group2
    status, data = api('GET', f'comment/{comment_id}', token=comment_token)
    assert status == 400
    assert data["message"] == "Insufficient permissions."

    # Both tokens should be able to view comment after updating group list
    status, data = api('PUT', f'comment/{comment_id}',
                       data={
                           'text': 'Comment text new',
                           'group_ids': [public_group.id, public_group2.id]},
                       token=comment_token_two_groups)
    assert status == 200

    status, data = api('GET', f'comment/{comment_id}', token=comment_token_two_groups)
    assert status == 200
    assert data['data']['text'] == 'Comment text new'

    status, data = api('GET', f'comment/{comment_id}', token=comment_token)
    assert status == 200
    assert data['data']['text'] == 'Comment text new'


def test_cannot_add_comment_without_permission(view_only_token, public_source):
    status, data = api('POST', 'comment', data={'obj_id': public_source.id,
                                                'text': 'Comment text'},
                       token=view_only_token)
    assert status == 400
    assert data['status'] == 'error'


def test_delete_comment(comment_token, public_source):
    status, data = api('POST', 'comment', data={'obj_id': public_source.id,
                                                'text': 'Comment text'},
                       token=comment_token)
    assert status == 200
    comment_id = data['data']['comment_id']

    status, data = api('GET', f'comment/{comment_id}', token=comment_token)
    assert status == 200
    assert data['data']['text'] == 'Comment text'

    status, data = api('DELETE', f'comment/{comment_id}', token=comment_token)
    assert status == 200

    status, data = api('GET', f'comment/{comment_id}', token=comment_token)
    assert status == 400
