from skyportal.tests import api
from datetime import date, timedelta
import uuid
import os
import time
import numpy as np


def test_shift(public_group, super_admin_token, view_only_token, super_admin_user):
    name = str(uuid.uuid4())
    start_date = date.today().strftime("%Y-%m-%dT%H:%M:%S")
    end_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
    request_data = {
        'name': name,
        'group_id': public_group.id,
        'start_date': start_date,
        'end_date': end_date,
        'description': 'the Night Shift',
        'shift_admins': [super_admin_user.id],
        'required_users_number': 2,
    }
    status, data = api('POST', 'shifts', data=request_data, token=view_only_token)
    assert status == 401
    assert data['status'] == 'error'

    status, data = api('POST', 'shifts', data=request_data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    shift_id = data['data']['id']

    status, data = api(
        'GET', f'shifts/{shift_id}', data=request_data, token=super_admin_token
    )
    assert status == 200
    assert data['status'] == 'success'

    status, data = api(
        'GET', f'shifts?group_id={public_group.id}', token=super_admin_token
    )
    assert status == 200
    assert data['status'] == 'success'

    assert any([request_data['name'] == s['name'] for s in data["data"]])
    assert any([request_data['start_date'] == s['start_date'] for s in data["data"]])
    assert any([request_data['end_date'] == s['end_date'] for s in data["data"]])
    assert any(
        [
            request_data['required_users_number'] == s['required_users_number']
            for s in data["data"]
        ]
    )

    assert any(
        [
            len([s for s in shift['shift_users_ids'] if s == super_admin_user.id]) == 1
            for shift in data['data']
        ]
    )

    name2 = str(uuid.uuid4())
    request_data = {
        'name': name2,
        'description': 'the Day Shift',
        'required_users_number': 3,
    }

    status, data = api(
        'PATCH', f'shifts/{shift_id}', data=request_data, token=super_admin_token
    )
    assert status == 200
    assert data['status'] == 'success'

    status, data = api(
        'GET', f'shifts/{shift_id}', data=request_data, token=super_admin_token
    )
    assert status == 200
    assert data['status'] == 'success'

    assert request_data['name'] == data['data']['name']
    assert request_data['description'] == data['data']['description']
    assert (
        request_data['required_users_number'] == data['data']['required_users_number']
    )


def test_shift_summary(
    public_group,
    super_admin_token,
    super_admin_user,
):
    # add a shift to the group, with a start day one day before today,
    # and an end day one day after today
    shift_name_1 = str(uuid.uuid4())
    start_date = "2018-01-15T12:00:00"
    end_date = "2018-01-17T12:00:00"
    request_data = {
        'name': shift_name_1,
        'group_id': public_group.id,
        'start_date': start_date,
        'end_date': end_date,
        'description': 'Shift during GCN',
        'shift_admins': [super_admin_user.id],
    }

    status, data = api('POST', 'shifts', data=request_data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    shift_id = data['data']['id']

    status, data = api(
        'GET', f'shifts/{shift_id}', data=request_data, token=super_admin_token
    )
    assert status == 200
    assert data['status'] == 'success'

    shift_name_2 = str(uuid.uuid4())
    start_date = "2018-01-17T12:00:00"
    end_date = "2018-01-18T12:00:00"
    request_data = {
        'name': shift_name_2,
        'group_id': public_group.id,
        'start_date': start_date,
        'end_date': end_date,
        'description': 'Shift not during GCN',
        'shift_admins': [super_admin_user.id],
    }

    status, data = api('POST', 'shifts', data=request_data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    shift_id_2 = data['data']['id']

    status, data = api(
        'GET', f'shifts?group_id={public_group.id}', token=super_admin_token
    )
    assert status == 200
    assert data['status'] == 'success'

    datafile = f'{os.path.dirname(__file__)}/../data/GRB180116A_Fermi_GBM_Gnd_Pos.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    # wait for event to load

    for n_times in range(16):
        status, data = api(
            'GET', "gcn_event/2018-01-16T00:36:53", token=super_admin_token
        )
        if data['status'] == 'success':
            break
        time.sleep(2)
    assert n_times < 15

    # wait for the localization to load
    skymap = "214.74000_28.14000_11.19000"
    params = {"include2DMap": True}
    for n_times_2 in range(16):
        status, data = api(
            'GET',
            f'localization/2018-01-16T00:36:53/name/{skymap}',
            token=super_admin_token,
            params=params,
        )

        if data['status'] == 'success':
            data = data["data"]
            assert data["dateobs"] == "2018-01-16T00:36:53"
            assert data["localization_name"] == "214.74000_28.14000_11.19000"
            assert np.isclose(np.sum(data["flat_2d"]), 1)
            break
        else:
            time.sleep(2)
    assert n_times_2 < 15

    status, data = api('GET', f'shifts/summary/{shift_id}', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    assert int(data['data']['shifts']['total']) == 1
    assert int(data['data']['gcns']['total']) == 1
    assert data['data']['shifts']['data'][0]['name'] == shift_name_1
    assert data['data']['gcns']['data'][0]['dateobs'] == '2018-01-16T00:36:53'
    assert shift_id in data['data']['gcns']['data'][0]['shift_ids']
    assert shift_id_2 not in data['data']['gcns']['data'][0]['shift_ids']

    request_data = {
        'startDate': "2018-01-14T12:00:00",
        'endDate': "2018-01-19T12:00:00",
    }

    status, data = api(
        'GET', 'shifts/summary', params=request_data, token=super_admin_token
    )

    assert status == 200
    assert data['status'] == 'success'
    assert int(data['data']['shifts']['total']) == 2
    assert int(data['data']['gcns']['total']) == 1
    assert shift_id in data['data']['gcns']['data'][0]['shift_ids']
    assert shift_id_2 not in data['data']['gcns']['data'][0]['shift_ids']
