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


def test_db_stats_history(super_admin_token, public_candidate):
    status, data = api(
        "GET",
        "db_stats/history",
        params={"tables": "candidates,sources", "interval": "day"},
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    history = data["data"]
    assert history["interval"] == "day"
    assert "candidates" in history["tables"]
    assert set(history["counts"]) == {"candidates", "sources"}
    for counts in history["counts"].values():
        assert len(counts) == len(history["bins"])
    # the fixture's candidate was created within the default 30-day window
    assert sum(history["counts"]["candidates"]) >= 1


def test_db_stats_history_bad_arguments(super_admin_token):
    status, data = api(
        "GET",
        "db_stats/history",
        params={"interval": "decade"},
        token=super_admin_token,
    )
    assert status == 400
    assert "Invalid interval" in data["message"]

    status, data = api(
        "GET",
        "db_stats/history",
        params={"tables": "photometry"},
        token=super_admin_token,
    )
    assert status == 400
    assert "Unknown table" in data["message"]

    status, data = api(
        "GET",
        "db_stats/history",
        params={"interval": "hour", "startDate": "2000-01-01T00:00:00"},
        token=super_admin_token,
    )
    assert status == 400
    assert "bins" in data["message"]


def test_db_stats_history_access_denied(view_only_token):
    status, data = api("GET", "db_stats/history", token=view_only_token)
    assert status == 401
