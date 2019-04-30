import requests

import skyportal
from skyportal.model_util import create_token


def test_versioned_request(driver, public_group, public_source):
    auth_token = create_token(public_group.id, ['Manage sources'])
    response = requests.get(f'{driver.server_url}/api/sources/{public_source.id}',
                            headers={'Authorization': f'token {auth_token}'}).json()
    assert response['status'] == 'success'
    assert response['data']['version'] == skyportal.__version__
