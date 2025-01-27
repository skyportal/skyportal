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
