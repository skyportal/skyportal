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
