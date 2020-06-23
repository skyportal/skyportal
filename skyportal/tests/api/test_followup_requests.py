import datetime
import arrow

from skyportal.tests import api




def test_token_user_post_classical_followup_request(red_transients_run,
                                                    public_source,
                                                    upload_data_token):
    request_data = {'run_id': red_transients_run.id,
                    'obj_id': public_source.id,
                    'priority': '5',
                    'comment': 'Please take spectrum only below airmass 1.5'}

    status, data = api('POST', 'assignment',
                       data=request_data,
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    id = data['data']['id']

    status, data = api('GET', f'assignment/{id}',
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'

    for key in request_data:
        assert data['data'][key] == request_data[key]


def test_token_user_post_robotic_followup_request(sedm, public_source,
                                                  upload_data_token):

    request_data = {'instrument_id': sedm.id,
                    'obj_id': public_source.id,
                    'priority': '5',
                    'comment': 'Classification',
                    'start_date': datetime.datetime.utcnow().isoformat(),
                    'end_date': (
                            datetime.datetime.utcnow() + datetime.timedelta(days=7)
                    ).isoformat(),
                    'observations': [
                        {'type': 'spectroscopy',
                         'exposure_time': 60.},
                        {'type': 'imaging',
                         'filter': 'sdssg',
                         'exposure_time': 360.}
                    ]}

    status, data = api('POST', 'followup_request',
                       data=request_data,
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'
    id = data['data']['id']

    status, data = api('GET', f'followup_request/{id}',
                       token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'

    for key in request_data:
        if 'date' not in key:
            assert data['data'][key] == request_data[key]
        else:
            t1 = arrow.get(data['data'][key])
            t2 = arrow.get(request_data[key])
            assert t1 == t2


def test_token_user_post_robotic_followup_request_invalid_filter(sedm, public_source,
                                                  upload_data_token):

    request_data = {'instrument_id': sedm.id,
                    'obj_id': public_source.id,
                    'priority': '5',
                    'comment': 'Classification',
                    'start_date': datetime.datetime.utcnow().isoformat(),
                    'end_date': (
                            datetime.datetime.utcnow() + datetime.timedelta(days=7)
                    ).isoformat(),
                    'observations': [
                        {'type': 'spectroscopy',
                         'exposure_time': 60.},
                        {'type': 'imaging',
                         'filter': 'sdssz',
                         'exposure_time': 360.}
                    ]}

    status, data = api('POST', 'followup_request',
                       data=request_data,
                       token=upload_data_token)
    assert status == 400
    assert data['status'] == 'error'


