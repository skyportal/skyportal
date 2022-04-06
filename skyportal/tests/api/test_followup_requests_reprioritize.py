import os

from skyportal.tests import api


def test_reprioritize_followup_request(
    public_group_sedm_allocation, public_source, upload_data_token, super_admin_token
):

    datafile = f'{os.path.dirname(__file__)}/../data/GW190425_initial.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    dateobs = "2019-04-25 08:18:05"
    params = {"include2DMap": True}

    status, data = api(
        'GET', f'gcn_event/{dateobs}', token=super_admin_token, params=params
    )
    assert status == 200
    localization_id = data['data']['localizations'][0]['id']

    request_data = {
        'allocation_id': public_group_sedm_allocation.id,
        'obj_id': public_source.id,
        'payload': {
            'priority': 1,
            'start_date': '3020-09-01',
            'end_date': '3022-09-01',
            'observation_type': 'IFU',
        },
    }

    status, data = api(
        'POST', 'followup_request', data=request_data, token=upload_data_token
    )
    assert status == 200
    assert data['status'] == 'success'
    id = data['data']['id']

    new_request_data = {
        'localizationId': localization_id,
        'requestIds': [id],
    }

    status, data = api(
        'PUT',
        'followup_request/prioritization',
        data=new_request_data,
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    status, data = api('GET', f'followup_request/{id}', token=upload_data_token)
    assert status == 200

    assert data['data']["payload"]["priority"] == 5.0
