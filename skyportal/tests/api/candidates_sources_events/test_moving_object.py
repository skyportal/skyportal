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
            'name': moving_obj_1,
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
            'name': moving_obj_2,
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
    assert data['data']['obj_ids'] == [str(public_source.id)]

    status, data = api(
        'GET', f'moving_object/{moving_object_id_2}', token=upload_data_token
    )
    assert status == 200
    assert data['status'] == 'success'
    assert data['data']['obj_ids'] == [str(public_source_two_groups.id)]

    params = {'obj_id': str(public_source.id)}

    status, data = api(
        'GET',
        'moving_object',
        token=upload_data_token,
        params=params,
    )
    assert status == 200
    assert data['status'] == 'success'
    assert any(
        d['obj_ids'] == [str(public_source.id)] for d in data['data']['moving_objects']
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
    assert not any(
        d['obj_ids'] == [str(public_source.id)] for d in data['data']['moving_objects']
    )
