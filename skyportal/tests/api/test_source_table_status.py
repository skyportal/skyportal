from skyportal.tests import api
import skyportal


def test_source_table_status(view_only_token):
    status, data = api('GET', 'internal/source_table_empty', token=view_only_token)
    assert status == 200
    assert data['status'] == 'success'
    assert isinstance(data['data']['source_table_empty'], bool)
    assert data['data']['version'] == skyportal.__version__
