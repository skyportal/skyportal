import uuid

import pytest
from playwright.sync_api import expect

from skyportal.tests import api


@pytest.mark.flaky(reruns=2)
def test_weather_widget(page, user, public_group, super_admin_token, p60_telescope):
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

    page.goto(f"/become_user/{user.id}")
    page.goto("/")

    page.locator('//*[@data-testid="tel-list-button"]').first.click()
    expect(page.locator(f'//*[text()="{p60_telescope.name}"]').first).to_be_visible(
        timeout=30000
    )
    page.locator(f'//*[text()="{p60_telescope.name}"]').first.click()
    expect(page.locator(f'//h6[text()="{p60_telescope.name}"]').first).to_be_visible()
