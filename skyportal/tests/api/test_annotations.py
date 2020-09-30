import numpy.testing as npt
from skyportal.tests import api


def test_post_without_origin_fails(annotation_token, public_source, public_group):

    # this should not work, since no "origin" is given
    status, data = api(
        'POST',
        'annotation',
        data={
            'obj_id': public_source.id,
            'data': {'redshift': 0.15},
            'group_ids': [public_group.id],
        },
        token=annotation_token,
    )

    assert status == 400
    assert data["message"] == "Missing required field `origin`"

    # this should not work, since "origin" is empty
    status, data = api(
        'POST',
        'annotation',
        data={
            'obj_id': public_source.id,
            'origin': '',
            'data': {'redshift': 0.15},
            'group_ids': [public_group.id],
        },
        token=annotation_token,
    )

    assert status == 400
    assert data["message"] == "Missing required field `origin`"


def test_post_same_origin_fails(annotation_token, public_source, public_group):

    # first time adding an annotation to this object from Kowalski
    status, data = api(
        'POST',
        'annotation',
        data={
            'obj_id': public_source.id,
            'origin': 'kowalski',
            'data': {'redshift': 0.15},
            'group_ids': [public_group.id],
        },
        token=annotation_token,
    )

    assert status == 200

    # this should not work, since "origin" Kowalski was already posted to this object
    # instead, try updating the existing annotation if you have new information!
    status, data = api(
        'POST',
        'annotation',
        data={
            'obj_id': public_source.id,
            'origin': 'kowalski',
            'data': {'redshift': 0.15},
            'group_ids': [public_group.id],
        },
        token=annotation_token,
    )

    assert status == 400
    assert 'duplicate key value violates unique constraint' in data["message"]


def test_add_and_retrieve_annotation_group_id(
    annotation_token, public_source, public_group
):
    status, data = api(
        'POST',
        'annotation',
        data={
            'obj_id': public_source.id,
            'origin': 'kowalski',
            'data': {'redshift': 0.15},
            'group_ids': [public_group.id],
        },
        token=annotation_token,
    )
    assert status == 200
    annotation_id = data['data']['annotation_id']

    status, data = api('GET', f'annotation/{annotation_id}', token=annotation_token)

    assert status == 200
    assert data['data']['data'] == {'redshift': 0.15}
    assert data['data']['origin'] == 'kowalski'


def test_add_and_retrieve_annotation_no_group_id(annotation_token, public_source):
    status, data = api(
        'POST',
        'annotation',
        data={
            'obj_id': public_source.id,
            'origin': 'kowalski',
            'data': {'redshift': 0.15},
        },
        token=annotation_token,
    )
    assert status == 200
    annotation_id = data['data']['annotation_id']

    status, data = api('GET', f'annotation/{annotation_id}', token=annotation_token)

    assert status == 200
    assert data['data']['data'] == {'redshift': 0.15}
    assert data['data']['origin'] == 'kowalski'


def test_add_and_retrieve_annotation_group_access(
    annotation_token_two_groups,
    public_source_two_groups,
    public_group2,
    public_group,
    annotation_token,
):
    status, data = api(
        'POST',
        'annotation',
        data={
            'obj_id': public_source_two_groups.id,
            'origin': 'kowalski',
            'data': {'redshift': 0.15},
            'group_ids': [public_group2.id],
        },
        token=annotation_token_two_groups,
    )

    assert status == 200
    annotation_id = data['data']['annotation_id']

    # This token belongs to public_group2
    status, data = api(
        'GET', f'annotation/{annotation_id}', token=annotation_token_two_groups
    )
    assert status == 200
    assert data['data']['data'] == {'redshift': 0.15}
    assert data['data']['origin'] == 'kowalski'

    # This token does not belong to public_group2
    status, data = api('GET', f'annotation/{annotation_id}', token=annotation_token)
    assert status == 400
    assert data["message"] == "Insufficient permissions."

    # Both tokens should be able to view this annotation
    status, data = api(
        'POST',
        'annotation',
        data={
            'obj_id': public_source_two_groups.id,
            'origin': 'snid',
            'data': {'redshift': 0.15},
            'group_ids': [public_group.id, public_group2.id],
        },
        token=annotation_token_two_groups,
    )

    assert status == 200
    annotation_id = data['data']['annotation_id']

    status, data = api(
        'GET', f'annotation/{annotation_id}', token=annotation_token_two_groups
    )
    assert status == 200
    assert data['data']['data'] == {'redshift': 0.15}
    assert data['data']['origin'] == 'snid'

    status, data = api('GET', f'annotation/{annotation_id}', token=annotation_token)
    assert status == 200
    assert data['data']['data'] == {'redshift': 0.15}


def test_update_annotation_group_list(
    annotation_token_two_groups,
    public_source_two_groups,
    public_group2,
    public_group,
    annotation_token,
):
    status, data = api(
        'POST',
        'annotation',
        data={
            'obj_id': public_source_two_groups.id,
            'origin': 'kowalski',
            'data': {'redshift': 0.15},
            'group_ids': [public_group2.id],
        },
        token=annotation_token_two_groups,
    )
    assert status == 200
    annotation_id = data['data']['annotation_id']

    # This token belongs to public_group2
    status, data = api(
        'GET', f'annotation/{annotation_id}', token=annotation_token_two_groups
    )
    assert status == 200
    assert data['data']['origin'] == 'kowalski'
    assert data['data']['data'] == {'redshift': 0.15}

    # This token does not belong to public_group2
    status, data = api('GET', f'annotation/{annotation_id}', token=annotation_token)
    assert status == 400
    assert data["message"] == "Insufficient permissions."

    # Both tokens should be able to view annotation after updating group list
    status, data = api(
        'PUT',
        f'annotation/{annotation_id}',
        data={
            'data': {'redshift': 0.17},
            'group_ids': [public_group.id, public_group2.id],
        },
        token=annotation_token_two_groups,
    )
    assert status == 200

    status, data = api(
        'GET', f'annotation/{annotation_id}', token=annotation_token_two_groups
    )
    assert status == 200
    assert data['data']['data'] == {'redshift': 0.17}

    status, data = api('GET', f'annotation/{annotation_id}', token=annotation_token)
    assert status == 200
    assert data['data']['data'] == {'redshift': 0.17}


def test_cannot_add_annotation_without_permission(view_only_token, public_source):
    status, data = api(
        'POST',
        'annotation',
        data={
            'obj_id': public_source.id,
            'origin': 'kowalski',
            'data': {'redshift': 0.15},
        },
        token=view_only_token,
    )
    assert status == 400
    assert data['status'] == 'error'


def test_delete_annotation(annotation_token, public_source):
    status, data = api(
        'POST',
        'annotation',
        data={
            'obj_id': public_source.id,
            'origin': 'kowalski',
            'data': {'redshift': 0.15},
        },
        token=annotation_token,
    )
    assert status == 200
    annotation_id = data['data']['annotation_id']

    status, data = api('GET', f'annotation/{annotation_id}', token=annotation_token)
    assert status == 200
    assert data['data']['data'] == {'redshift': 0.15}
    assert data['data']['origin'] == 'kowalski'

    status, data = api('DELETE', f'annotation/{annotation_id}', token=annotation_token)
    assert status == 200

    status, data = api('GET', f'annotation/{annotation_id}', token=annotation_token)
    assert status == 400


def test_add_redshift_annotation(super_admin_token, public_source, public_group):
    status, data = api(
        'POST',
        'annotation',
        data={
            'obj_id': public_source.id,
            'origin': 'kowalski',
            'data': {'redshift': 0.221},
            'group_ids': [public_group.id],
        },
        token=super_admin_token,
    )
    assert status == 200

    status, data = api('GET', f'sources/{public_source.id}', token=super_admin_token)
    assert status == 200
    npt.assert_almost_equal(data['data']['redshift'], 0.221)
