from skyportal.tests import api


def test_source_list(token):
    status, data = api('GET', 'sources', token=token)
    assert status == 200
    data['status'] == 'success'
