import uuid

from skyportal.tests import api


def test_weather_widget(driver, user, public_group, upload_data_token):

    name = str(uuid.uuid4())
    post_data = {
        'name': name,
        'nickname': name,
        'lat': 0.0,
        'lon': 0.0,
        'elevation': 0.0,
        'diameter': 10.0,
        'skycam_link': 'http://www.lulin.ncu.edu.tw/wea/cur_sky.jpg',
        'weather_link': 'http://www.lulin.ncu.edu.tw/',
        'robotic': True,
    }

    status, data = api('POST', 'telescope', data=post_data, token=upload_data_token)
    assert status == 200
    assert data['status'] == 'success'

    driver.get(f'/become_user/{user.id}')
    driver.get('/')

    weather = driver.wait_for_xpath('//*[@id="weatherWidget"]')

    weather_text = weather.text
    assert weather_text.find("No weather information available") != -1

    driver.click_xpath('//*[@aria-controls="tel-list"]')
