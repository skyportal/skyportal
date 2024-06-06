import uuid
from skyportal.tests import api


def test_add_and_get_moving_object(
    super_admin_token, upload_data_token, public_source, public_source_two_groups
):
    moving_obj_1 = str(uuid.uuid4())
    moving_obj_2 = str(uuid.uuid4())

    status, data = api(
        'POST',
        'moving_object',
        data={
            'id': moving_obj_1,
            'obj_ids': [str(public_source.id)],
            "mjd": [59410, 59411, 59412],
            "ra": [42.01, 42.01, 42.02],
            "dec": [42.02, 42.01, 42.03],
            "ra_err": [0.01, 0.02, 0.01],
            "dec_err": [0.02, 0.01, 0.02],
        },
        token=upload_data_token,
    )
    assert status == 200
    moving_object_id_1 = data["data"]["id"]

    status, data = api(
        'POST',
        'moving_object',
        data={
            'id': moving_obj_2,
            'obj_ids': [str(public_source_two_groups.id)],
            "mjd": [69410, 69411, 69412],
            "ra": [52.01, 52.01, 52.02],
            "dec": [52.02, 52.01, 52.03],
            "ra_err": [0.01, 0.02, 0.01],
            "dec_err": [0.02, 0.01, 0.02],
        },
        token=upload_data_token,
    )
    assert status == 200
    moving_object_id_2 = data["data"]["id"]

    status, data = api(
        'GET', f'moving_object/{moving_object_id_1}', token=upload_data_token
    )
    assert status == 200
    assert data['status'] == 'success'
    assert "objs" in data["data"]
    assert len(data["data"]["objs"]) == 1
    assert data["data"]["objs"][0]["id"] == str(public_source.id)

    status, data = api(
        'GET', f'moving_object/{moving_object_id_2}', token=upload_data_token
    )
    assert status == 200
    assert data['status'] == 'success'
    assert "objs" in data["data"]
    assert len(data["data"]["objs"]) == 1
    assert data["data"]["objs"][0]["id"] == str(public_source_two_groups.id)

    params = {'obj_id': str(public_source.id), 'include_objs': True}

    status, data = api(
        'GET',
        'moving_object',
        token=upload_data_token,
        params=params,
    )
    assert status == 200
    assert data['status'] == 'success'
    assert len(data["data"]) > 0
    assert any([d['id'] == moving_obj_1 for d in data['data']['moving_objects']])
    assert all(["objs" in d for d in data['data']['moving_objects']])
    assert any(
        [
            d['objs'][0]['id'] == str(public_source.id)
            for d in data['data']['moving_objects']
        ]
    )

    status, data = api(
        'DELETE', f'moving_object/{moving_object_id_1}', token=super_admin_token
    )
    assert status == 200
    assert data['status'] == 'success'

    params = {'obj_id': str(public_source.id)}

    status, data = api(
        'GET',
        'moving_object',
        token=upload_data_token,
        params=params,
    )
    assert status == 200
    assert data['status'] == 'success'
    assert len(data["data"]) > 0
    assert not any(
        [
            d['id'] == moving_obj_1
            and str(public_source.id) in [o['id'] for o in d['objs']]
            for d in data['data']['moving_objects']
        ]
    )
