import uuid
from skyportal.tests import api


def test_post_new_grouped_object(upload_data_token, public_source, public_group):
    """Test creation of a new grouped object."""
    obj_ids = [public_source.id]
    name = str(uuid.uuid4())

    status, data = api(
        'POST',
        'grouped_object',
        data={
            'name': name,
            'type': 'moving_object',
            'description': 'Test moving object group',
            'obj_ids': obj_ids,
            'group_ids': [public_group.id],
            'properties': {'velocity': '10km/s'},
            'origin': 'test pipeline',
        },
        token=upload_data_token,
    )

    print(f"Status: {status}")
    print(f"Response data: {data}")

    assert status == 200


def test_get_grouped_object(upload_data_token, public_source, public_group):
    """Test retrieving grouped objects."""
    obj_ids = [public_source.id]
    name = str(uuid.uuid4())

    status, data = api(
        'POST',
        'grouped_object',
        data={
            'name': name,
            'type': 'moving_object',
            'description': 'Test moving object group',
            'obj_ids': obj_ids,
            'group_ids': [public_group.id],
            'properties': {'velocity': '10km/s'},
            'origin': 'test pipeline',
        },
        token=upload_data_token,
    )

    print(f"Status: {status}")
    print(f"Response data: {data}")

    assert status == 200
    grouped_obj_id = data['data']['id']

    status, data = api(
        'GET', f'grouped_object/{grouped_obj_id}', token=upload_data_token
    )

    assert status == 200
    assert data['data']['name'] == name
    assert data['data']['type'] == 'moving_object'
    assert 'created_by' in data['data']

    status, data = api('GET', 'grouped_object', token=upload_data_token)
    assert status == 200
    assert any(obj['id'] == grouped_obj_id for obj in data['data'])


def test_patch_grouped_object(
    upload_data_token, public_obj, public_source, view_only_token
):
    """Test updating a grouped object."""
    # First create a grouped object
    name = str(uuid.uuid4())
    obj_ids = [public_obj.id]
    print("patch test")

    status, data = api(
        'POST',
        'grouped_object',
        data={
            'name': name,
            'type': 'moving_object',
            'description': 'Test moving object group',
            'obj_ids': obj_ids,
            'properties': {'velocity': '10km/s'},
            'origin': 'test pipeline',
        },
        token=upload_data_token,
    )
    print(f"POST Status: {status}")
    print(f"POST Response data: {data}")
    assert status == 200
    grouped_obj_id = data['data']['id']

    # Now try to update it
    new_name = str(uuid.uuid4())
    new_obj_ids = [public_obj.id, public_source.id]  # Add another object

    status, data = api(
        'PATCH',
        f'grouped_object/{grouped_obj_id}',
        data={
            'name': new_name,
            'obj_ids': new_obj_ids,
            'properties': {'velocity': '20km/s'},  # Changed velocity
        },
        token=upload_data_token,
    )

    print(f"Response data of PATCH: {data}")
    assert status == 200

    # Verify the changes
    status, data = api(
        'GET', f'grouped_object/{grouped_obj_id}', token=upload_data_token
    )
    assert status == 200
    assert data['data']['name'] == new_name
    assert data['data']['properties']['velocity'] == '20km/s'
    assert len(data['data']['obj_ids']) == 2  # Should now have 2 objects
    assert set(data['data']['obj_ids']) == {public_obj.id, public_source.id}

    # Test that view-only token cannot update
    status, data = api(
        'PATCH',
        f'grouped_object/{grouped_obj_id}',
        data={'name': 'should not work'},
        token=view_only_token,
    )
    assert status == 401  # Unauthorized is the correct response
