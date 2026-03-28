import uuid

from skyportal.tests import api


def test_get_telescope_longitude_longitude_box(super_admin_token):
    name = str(uuid.uuid4())
    post_data = {
        "name": name,
        "nickname": name,
        "lat": 0.0,
        "lon": 0.0,
        "elevation": 0.0,
        "diameter": 10.0,
        "skycam_link": "http://www.lulin.ncu.edu.tw/wea/cur_sky.jpg",
        "robotic": True,
    }

    status, data = api("POST", "telescope", data=post_data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    telescope_id_1 = data["data"]["id"]

    name = str(uuid.uuid4())
    post_data = {
        "name": name,
        "nickname": name,
        "lat": -30.0,
        "lon": 60.0,
        "elevation": 0.0,
        "diameter": 10.0,
        "skycam_link": "http://www.lulin.ncu.edu.tw/wea/cur_sky.jpg",
        "robotic": True,
    }

    status, data = api("POST", "telescope", data=post_data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    telescope_id_2 = data["data"]["id"]

    params = {
        "latitudeMin": -45.0,
        "latitudeMax": -15.0,
        "longitudeMin": 45.0,
        "longitudeMax": 75.0,
    }

    status, data = api("GET", "telescope", token=super_admin_token, params=params)
    assert status == 200
    assert data["status"] == "success"

    assert telescope_id_2 in [tel["id"] for tel in data["data"]]
    assert telescope_id_1 not in [tel["id"] for tel in data["data"]]


def test_token_user_post_get_telescope(super_admin_token):
    name = str(uuid.uuid4())
    post_data = {
        "name": name,
        "nickname": name,
        "lat": 0.0,
        "lon": 0.0,
        "elevation": 0.0,
        "diameter": 10.0,
        "skycam_link": "http://www.lulin.ncu.edu.tw/wea/cur_sky.jpg",
        "robotic": True,
    }

    status, data = api("POST", "telescope", data=post_data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    telescope_id = data["data"]["id"]
    status, data = api("GET", f"telescope/{telescope_id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    for key in post_data:
        assert data["data"][key] == post_data[key]


def test_fetch_telescope_by_name(super_admin_token):
    name = str(uuid.uuid4())
    post_data = {
        "name": name,
        "nickname": name,
        "lat": 0.0,
        "lon": 0.0,
        "elevation": 0.0,
        "diameter": 10.0,
        "skycam_link": "http://www.lulin.ncu.edu.tw/wea/cur_sky.jpg",
    }

    status, data = api("POST", "telescope", data=post_data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"telescope?name={name}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    for key in post_data:
        assert data["data"][0][key] == post_data[key]


def test_token_user_update_telescope(super_admin_token):
    name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "telescope",
        data={
            "name": name,
            "nickname": name,
            "lat": 0.0,
            "lon": 0.0,
            "elevation": 0.0,
            "diameter": 10.0,
            "robotic": True,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    telescope_id = data["data"]["id"]
    status, data = api("GET", f"telescope/{telescope_id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["diameter"] == 10.0

    status, data = api(
        "PUT",
        f"telescope/{telescope_id}",
        data={
            "name": name,
            "nickname": name,
            "lat": 0.0,
            "lon": 0.0,
            "elevation": 0.0,
            "diameter": 12.0,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"telescope/{telescope_id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["diameter"] == 12.0


def test_token_user_delete_telescope(super_admin_token):
    name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "telescope",
        data={
            "name": name,
            "nickname": name,
            "lat": 0.0,
            "lon": 0.0,
            "elevation": 0.0,
            "diameter": 10.0,
            "robotic": False,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    telescope_id = data["data"]["id"]
    status, data = api("GET", f"telescope/{telescope_id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["diameter"] == 10.0

    status, data = api("DELETE", f"telescope/{telescope_id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"telescope/{telescope_id}", token=super_admin_token)
    assert status == 400
