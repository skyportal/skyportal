import skyportal
from skyportal.tests import api


def test_versioned_request(view_only_token, public_source):
    response = api(
        "GET", "sources/{public_source.id}", token=view_only_token, raw_response=True
    )
    json = response.json()
    assert "version" in json and json["version"] == skyportal.__version__
    if "dev" in skyportal.__version__:
        assert "+git" in json["version"]
