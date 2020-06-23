import uuid
from skyportal.tests import api
from skyportal.models import Telescope, Instrument, DBSession


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

