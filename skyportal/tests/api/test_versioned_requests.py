from skyportal.tests import api
import skyportal


def test_versioned_request(view_only_token, public_source):
    status, data = api('GET', 'sources/{public_source.id}',
                   token=view_only_token)
    assert data['data']['version'] == skyportal.__version__
    if 'dev' in skyportal.__version__:
        assert '+git' in data['data']['version']
