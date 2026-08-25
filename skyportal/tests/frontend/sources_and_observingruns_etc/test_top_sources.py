import datetime
import time
import uuid

import pytest
from playwright.sync_api import expect

from skyportal.models import DBSession, SourceView
from skyportal.tests import api


def _set_max_num_sources(page, value):
    num = page.locator('//input[@name="maxNumSources"]').first
    num.click()
    num.press("ControlOrMeta+a")
    num.press_sequentially(value)


def test_top_sources(page, user, public_source, public_group, upload_data_token):
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 50.4,
            "dec": 22.33,
            "redshift": 2.1,
            "altdata": {"simbad": {"class": "RRLyr"}},
            "transient": False,
            "ra_dis": 2.3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id

    page.goto(f"/become_user/{user.id}")
    page.goto("/")
    expect(page.locator(f'//a/span[contains(.,"{obj_id}")]').first).to_be_visible()

    # edit the preferences to show more than the default 10 sources
    page.locator('//*[@id="topSourcesSettingsIcon"]').first.click()
    _set_max_num_sources(page, "50")
    page.locator('//button[@type="submit"][@name="topSourcesSubmit"]').first.click()

    # Test that front-end views register as source views
    page.locator(f'//a/span[contains(.,"{obj_id}")]').first.click()
    expect(page.locator(f'//h6[text()="{obj_id}"]').first).to_be_visible()
    time.sleep(2)
    page.goto("/")
    expect(page.locator("//*[contains(.,'1 view')]").first).to_be_visible()

    # Token requests register source views but must NOT increment the UI count
    status, data = api("GET", f"sources/{obj_id}", token=upload_data_token)
    time.sleep(1)
    assert status == 200
    page.reload()
    expect(page.locator("//*[contains(.,'1 view')]").first).to_be_visible()


@pytest.mark.flaky(reruns=2)
def test_top_source_prefs(page, user, public_group, upload_data_token):
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 50.4,
            "dec": 22.33,
            "redshift": 2.1,
            "altdata": {"simbad": {"class": "RRLyr"}},
            "transient": False,
            "ra_dis": 2.3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id

    twenty_days_ago = datetime.datetime.now() - datetime.timedelta(days=20)
    sv = SourceView(
        obj_id=obj_id,
        username_or_token_id=upload_data_token,
        is_token=False,
        created_at=twenty_days_ago,
    )
    DBSession().add(sv)
    DBSession().commit()

    page.goto(f"/become_user/{user.id}")
    page.goto("/")

    timespan_button = "//button[contains(@data-testid, 'topSources_timespanButton')]"
    expect(page.locator(timespan_button).first).to_be_visible()

    page.locator('//*[@id="topSourcesSettingsIcon"]').first.click()
    _set_max_num_sources(page, "50")
    page.locator('//button[@type="submit"][@name="topSourcesSubmit"]').first.click()

    # Source doesn't show up in last 7 days of views
    source_view_xpath = f"//div[starts-with(@data-testid, 'topSourceItem_{obj_id}')]"
    expect(page.locator(source_view_xpath).first).to_be_hidden()

    # Source shows up in last 30 days of views
    page.locator(timespan_button).first.click()
    page.locator("//*[contains(@data-testid, 'topSources_30days')]").first.click()

    expect(page.locator(source_view_xpath).first).to_be_visible()
