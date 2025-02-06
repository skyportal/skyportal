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

    print(f"POST Status: {status}")
    print(f"POST Response data: {data}")

    assert status == 200
    assert data['data']['name'] == name


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

    print(f"POST Status: {status}")
    print(f"POST Response data: {data}")

    assert status == 200
    grouped_obj_name = data['data']['name']

    status, data = api(
        'GET', f'grouped_object/{grouped_obj_name}', token=upload_data_token
    )

    print(f"GET Status: {status}")
    print(f"GET Response data: {data}")

    assert status == 200
    assert data['data']['name'] == name
    assert data['data']['type'] == 'moving_object'
    assert 'created_by' in data['data']

    status, data = api('GET', 'grouped_object', token=upload_data_token)
    assert status == 200
    assert any(obj['name'] == grouped_obj_name for obj in data['data'])


def test_patch_grouped_object(
    upload_data_token, public_obj, public_source, view_only_token
):
    """Test updating a grouped object."""
    name = str(uuid.uuid4())
    obj_ids = [public_obj.id]

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
    assert status == 200
    grouped_obj_name = name

    new_obj_ids = [public_obj.id, public_source.id]

    status, data = api(
        'PATCH',
        f'grouped_object/{grouped_obj_name}',
        data={
            'obj_ids': new_obj_ids,
            'properties': {'velocity': '20km/s'},
        },
        token=upload_data_token,
    )

    assert status == 200

    # Verify the changes
    status, data = api(
        'GET', f'grouped_object/{grouped_obj_name}', token=upload_data_token
    )
    assert status == 200
    assert data['data']['name'] == name
    assert data['data']['properties']['velocity'] == '20km/s'
    assert len(data['data']['obj_ids']) == 2
    assert set(data['data']['obj_ids']) == {public_obj.id, public_source.id}

    # Test that view-only token cannot update
    status, data = api(
        'PATCH',
        f'grouped_object/{grouped_obj_name}',
        data={'properties': {'velocity': '30km/s'}},
        token=view_only_token,
    )
    assert status == 401


def test_delete_grouped_object(upload_data_token, public_source, view_only_token):
    """Test deletion of a grouped object."""
    name = str(uuid.uuid4())
    obj_ids = [public_source.id]

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
    assert status == 200
    grouped_obj_name = name

    # Test that view-only token cannot delete
    status, data = api(
        'DELETE',
        f'grouped_object/{grouped_obj_name}',
        token=view_only_token,
    )
    assert status == 401

    # Delete with proper permissions
    status, data = api(
        'DELETE',
        f'grouped_object/{grouped_obj_name}',
        token=upload_data_token,
    )
    print(f"DELETE Status: {status}")
    print(f"DELETE Response: {data}")
    assert status == 200

    # Verify the object is deleted
    status, data = api(
        'GET',
        f'grouped_object/{grouped_obj_name}',
        token=upload_data_token,
    )
    print(f"GET Status after delete: {status}")
    print(f"GET Response after delete: {data}")
    assert status == 404  # Not Found is the correct response for a missing resource
    assert "Invalid grouped object name" in data["message"]
