import uuid
from skyportal.tests import api
from skyportal.models import Telescope, Instrument, DBSession



def test_token_user_post_classical_followup_request(red_transients_run, public_source,
                                                    upload_data_token):

    request_data = {'run_id': red_transients_run.id,
                    'type': 'classical_spectroscopy',
                    'exposure_time_blue': 55.,
                    'exposure_time_red': 120.,
                    'n_exposures_blue': 2,
                    'n_exposures_red': 1,
                    'obj_id': public_source.id,
                    'priority': '5',
                    'comment': 'Please take spectrum only below airmass 1.5'}

    name = str(uuid.uuid4())
    status, data = api('POST', 'followup_request',
                       data=request_data,
                       token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    telescope_id = data['data']['id']



