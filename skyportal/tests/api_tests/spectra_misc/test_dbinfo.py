import skyportal
from skyportal.tests import api, client


def test_db_info(view_only_token):
    info = client(view_only_token).fetch_dbinfo()
    assert isinstance(info.source_table_empty, bool)
    assert isinstance(info.postgres_version, str)

    # raw api: the envelope-level version key is stripped by the typed client
    status, data = api("GET", "internal/dbinfo", token=view_only_token)
    assert status == 200
    assert data["version"] == skyportal.__version__
