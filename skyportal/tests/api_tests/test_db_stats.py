from skyportal.tests import api


def test_db_stats(
    super_admin_token, public_source, public_group, public_candidate, user
):
    status, data = api("GET", "db_stats", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    assert isinstance(data["data"]["Number of candidates"], int)
    assert isinstance(data["data"]["Number of users"], int)


def test_db_stats_access_denied(
    view_only_token, public_source, public_group, public_candidate, user
):
    status, data = api("GET", "db_stats", token=view_only_token)
    assert status == 401
