import uuid

from skyportal.tests import api


def test_weather_api(upload_data_token, super_admin_token):
    name = str(uuid.uuid4())
    post_data = {
        "name": name,
        "nickname": name,
        "lat": 0.0,
        "lon": 0.0,
        "elevation": 0.0,
        "diameter": 10.0,
        "skycam_link": "http://www.lulin.ncu.edu.tw/wea/cur_sky.jpg",
        "weather_link": "http://www.lulin.ncu.edu.tw/",
        "robotic": True,
    }

    status, data = api("POST", "telescope", data=post_data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    telescope_id = data["data"]["id"]

    # update the user pref
    patch_data = {"preferences": {"weather": {"telescopeID": telescope_id}}}
    status, data = api(
        "PATCH", "internal/profile", data=patch_data, token=upload_data_token
    )
    assert status == 200
    assert data["status"] == "success"

    # get the weather for the user preference telescope
    status, data = api("GET", "weather", token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"

    # get the weather for this telescope id
    status, data_specific_id = api(
        "GET", f"weather?telescope_id={telescope_id}", token=upload_data_token
    )
    assert status == 200
    assert data_specific_id["status"] == "success"

    # did we get the same results?
    assert data_specific_id["data"]["telescope_name"] == data["data"]["telescope_name"]
    assert data_specific_id["data"]["weather"] == data["data"]["weather"]
