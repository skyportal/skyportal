import uuid

from skyportal_py.profile import ProfilePatch
from skyportal_py.telescopes import TelescopePost

from skyportal.tests import client


def test_weather_api(upload_data_token, super_admin_token):
    name = str(uuid.uuid4())
    telescope_id = (
        client(super_admin_token)
        .post_telescope(
            TelescopePost(
                name=name,
                nickname=name,
                lat=0.0,
                lon=0.0,
                elevation=0.0,
                diameter=10.0,
                skycam_link="http://www.lulin.ncu.edu.tw/wea/cur_sky.jpg",
                weather_link="http://www.lulin.ncu.edu.tw/",
                robotic=True,
            )
        )
        .id
    )

    # update the user pref
    sp = client(upload_data_token)
    sp.update_profile(
        ProfilePatch(preferences={"weather": {"telescopeID": telescope_id}})
    )

    # get the weather for the user preference telescope
    weather = sp.fetch_weather()

    # get the weather for this telescope id
    weather_specific_id = sp.fetch_weather(telescope_id=telescope_id)

    # did we get the same results?
    assert weather_specific_id.telescope_name == weather.telescope_name
    assert weather_specific_id.weather == weather.weather
