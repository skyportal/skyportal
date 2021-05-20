from skyportal.tests import api
import datetime


def test_add_and_retrieve_comment_group_id(
    comment_token, upload_data_token, public_source, public_group, lris
):
    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': str(public_source.id),
            'observed_at': str(datetime.datetime.now()),
            'instrument_id': lris.id,
            'wavelengths': [664, 665, 666],
            'fluxes': [234.2, 232.1, 235.3],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    spectrum_id = data["data"]["id"]

    status, data = api(
        'POST',
        'comment',
        data={
            'obj_id': public_source.id,
            'spectrum_id': spectrum_id,
            'text': 'Comment text',
            'group_ids': [public_group.id],
        },
        token=comment_token,
    )
    assert status == 200
    comment_id = data['data']['comment_id']

    status, data = api('GET', f'comment/{comment_id}/spectrum', token=comment_token)

    assert status == 200
    assert data['data']['text'] == 'Comment text'


def test_add_and_retrieve_comment_group_access(
    comment_token_two_groups,
    upload_data_token_two_groups,
    public_source_two_groups,
    public_group2,
    public_group,
    comment_token,
    lris,
):
    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': str(public_source_two_groups.id),
            'observed_at': str(datetime.datetime.now()),
            'instrument_id': lris.id,
            'wavelengths': [664, 665, 666],
            'fluxes': [234.2, 232.1, 235.3],
            'group_ids': [public_group2.id],
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data['status'] == 'success'
    spectrum_id = data["data"]["id"]

    status, data = api(
        'POST',
        'comment',
        data={
            'obj_id': public_source_two_groups.id,
            'spectrum_id': spectrum_id,
            'text': 'Comment text',
            'group_ids': [public_group2.id],
        },
        token=comment_token_two_groups,
    )
    assert status == 200
    comment_id = data['data']['comment_id']

    # This token belongs to public_group2
    status, data = api(
        'GET', f'comment/{comment_id}/spectrum', token=comment_token_two_groups
    )
    assert status == 200
    assert data['data']['text'] == 'Comment text'

    # This token does not belong to public_group2
    status, data = api('GET', f'comment/{comment_id}/spectrum', token=comment_token)
    assert status == 400
    assert "Insufficient permissions" in data["message"]

    # Both tokens should be able to view this comment, but not the underlying spectrum
    status, data = api(
        'POST',
        'comment',
        data={
            'obj_id': public_source_two_groups.id,
            'spectrum_id': spectrum_id,
            'text': 'Comment text',
            'group_ids': [public_group.id, public_group2.id],
        },
        token=comment_token_two_groups,
    )
    assert status == 200
    comment_id = data['data']['comment_id']

    status, data = api(
        'GET', f'comment/{comment_id}/spectrum', token=comment_token_two_groups
    )
    assert status == 200
    assert data['data']['text'] == 'Comment text'

    status, data = api('GET', f'comment/{comment_id}/spectrum', token=comment_token)
    assert status == 400  # the underlying spectrum is not accessible to group1

    # post a new spectrum with a comment, open to both groups
    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': str(public_source_two_groups.id),
            'observed_at': str(datetime.datetime.now()),
            'instrument_id': lris.id,
            'wavelengths': [664, 665, 666],
            'fluxes': [234.2, 232.1, 235.3],
            'group_ids': [public_group.id, public_group2.id],
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data['status'] == 'success'
    spectrum_id = data["data"]["id"]

    status, data = api(
        'POST',
        'comment',
        data={
            'obj_id': public_source_two_groups.id,
            'spectrum_id': spectrum_id,
            'text': 'New comment text',
            'group_ids': [public_group2.id],
        },
        token=comment_token_two_groups,
    )
    assert status == 200
    comment_id = data['data']['comment_id']

    # token for group1 can view the spectrum but cannot see comment
    status, data = api('GET', f'comment/{comment_id}/spectrum', token=comment_token)
    assert status == 400
    assert "Insufficient permissions" in data["message"]

    # Both tokens should be able to view comment after updating group list
    status, data = api(
        'PUT',
        f'comment/{comment_id}/spectrum',
        data={
            'text': 'New comment text',
            'group_ids': [public_group.id, public_group2.id],
        },
        token=comment_token_two_groups,
    )
    assert status == 200

    # the new comment on the new spectrum should now accessible
    status, data = api('GET', f'comment/{comment_id}/spectrum', token=comment_token)
    assert status == 200
    assert data['data']['text'] == 'New comment text'


def test_cannot_add_comment_without_permission(
    view_only_token, upload_data_token, public_source, lris
):
    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': str(public_source.id),
            'observed_at': str(datetime.datetime.now()),
            'instrument_id': lris.id,
            'wavelengths': [664, 665, 666],
            'fluxes': [234.2, 232.1, 235.3],
            'group_ids': "all",
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    spectrum_id = data["data"]["id"]

    status, data = api(
        'POST',
        'comment',
        data={
            'obj_id': public_source.id,
            'spectrum_id': spectrum_id,
            'text': 'Comment text',
        },
        token=view_only_token,
    )
    assert status == 400
    assert data['status'] == 'error'


def test_delete_comment(comment_token, upload_data_token, public_source, lris):
    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': str(public_source.id),
            'observed_at': str(datetime.datetime.now()),
            'instrument_id': lris.id,
            'wavelengths': [664, 665, 666],
            'fluxes': [234.2, 232.1, 235.3],
            'group_ids': "all",
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    spectrum_id = data["data"]["id"]

    status, data = api(
        'POST',
        'comment',
        data={
            'obj_id': public_source.id,
            'spectrum_id': spectrum_id,
            'text': 'Comment text',
        },
        token=comment_token,
    )
    assert status == 200
    comment_id = data['data']['comment_id']

    status, data = api('GET', f'comment/{comment_id}/spectrum', token=comment_token)
    assert status == 200
    assert data['data']['text'] == 'Comment text'

    status, data = api('DELETE', f'comment/{comment_id}/spectrum', token=comment_token)
    assert status == 200

    status, data = api('GET', f'comment/{comment_id}/spectrum', token=comment_token)
    assert status == 400
    assert "Invalid CommentOnSpectrum" in data["message"]
