from skyportal.tests import api


def test_get_alert(view_only_token):
    oid = "ZTF20aaelulu"
    status, data = api("GET", f"alerts/ztf/{oid}", token=view_only_token)
    print(data)
    assert status == 200
    assert data["status"] == "success"
    assert "data" in data
    assert len(data["data"]) > 0
    assert all(k in data["data"][0] for k in ["candidate", "coordinates"])


def test_get_alert_aux(view_only_token):
    oid = "ZTF20aaelulu"
    status, data = api("GET", f"alerts/ztf/{oid}/aux", token=view_only_token)
    print(data)
    assert status == 200
    assert data["status"] == "success"
    assert "data" in data
    assert all(k in data["data"] for k in ["_id", "cross_matches", "prv_candidates"])
    assert data["data"]["_id"] == oid


def test_get_alert_cutout(view_only_token):
    oid = "ZTF20aaelulu"
    candid = 1105522281015015000
    for cutout in ("science", "template", "difference"):
        for file_format in ("png", "fits"):
            response = api(
                "GET",
                f"/api/alerts/ztf/{oid}/cutout"
                f"?candid={candid}&cutout={cutout}&file_format={file_format}",
                raw_response=True,
            )
            assert response.status_code == 200
