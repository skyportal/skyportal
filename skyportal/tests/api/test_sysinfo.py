from skyportal.tests import api
import skyportal


def test_sysinfo(view_only_token):
    status, data = api('GET', 'sysinfo', token=view_only_token)
    assert status == 200
    assert data['status'] == 'success'
    assert isinstance(data['data']['sources_table_empty'], bool)
    assert data['data']['version'] == skyportal.__version__
