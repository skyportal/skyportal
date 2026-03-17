import skyportal
from skyportal.tests import api


def test_db_info(view_only_token):
    status, data = api("GET", "internal/dbinfo", token=view_only_token)
    assert status == 200
    assert data["status"] == "success"
    assert isinstance(data["data"]["source_table_empty"], bool)
    assert isinstance(data["data"]["postgres_version"], str)
    assert data["version"] == skyportal.__version__
