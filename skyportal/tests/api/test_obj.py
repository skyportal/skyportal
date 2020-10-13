from skyportal.tests import api


def test_check_candidate(view_only_token, public_candidate):
    status, data = api(
        "GET", f"objs/{public_candidate.id}/short", token=view_only_token
    )
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["is_candidate"]
    assert not data["data"]["is_source"]


def test_check_source(view_only_token, public_source):
    status, data = api("GET", f"objs/{public_source.id}/short", token=view_only_token)
    assert status == 200
    assert data["status"] == "success"
    assert not data["data"]["is_candidate"]
    assert data["data"]["is_source"]
