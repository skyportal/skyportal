import pytest

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
    assert history["bins"][0] == history["startDate"]
    assert set(history["counts"]) == {"candidates", "sources"}
    for counts in history["counts"].values():
        assert len(counts) == len(history["bins"])
    assert sum(history["counts"]["candidates"]) >= 1


@pytest.mark.parametrize(
    "params, message",
    [
        ({"interval": "decade"}, "Invalid interval"),
        ({"tables": "photometry"}, "Unknown table"),
        ({"interval": "hour", "startDate": "2000-01-01T00:00:00"}, "bins"),
        ({"startDate": "not-a-date"}, "Invalid date"),
        ({"startDate": "2100-01-01T00:00:00"}, "startDate must be before endDate"),
    ],
)
def test_db_stats_history_bad_arguments(super_admin_token, params, message):
    status, data = api(
        "GET", "db_stats/history", params=params, token=super_admin_token
    )
    assert status == 400
    assert message in data["message"]


def test_db_stats_history_access_denied(view_only_token):
    status, data = api("GET", "db_stats/history", token=view_only_token)
    assert status == 401
