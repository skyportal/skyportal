import datetime
import time
import uuid

import pytest

from skyportal.models import ThreadSession, SourceView
from skyportal.tests import api


def test_top_sources(driver, user, public_source, public_group, upload_data_token):
    obj_id = str(uuid.uuid4())
    status, data = api(
        'POST',
        'sources',
        data={
            'id': obj_id,
            'ra': 50.4,
            'dec': 22.33,
            'redshift': 2.1,
            "altdata": {"simbad": {"class": "RRLyr"}},
            'transient': False,
            'ra_dis': 2.3,
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['data']['id'] == obj_id

    driver.get(f'/become_user/{user.id}')
    driver.get('/')
    # Wait for just added source to show up in added sources
    driver.wait_for_xpath(f'//a/span[contains(.,"{obj_id}")]')

    # edit the preferences to show more than the default 10 sources
    settings_button = driver.wait_for_xpath('//*[@id="topSourcesSettingsIcon"]')
    driver.scroll_to_element_and_click(settings_button)

    input = driver.wait_for_xpath('//input[@name="maxNumSources"]')
    driver.scroll_to_element_and_click(input)
    input.send_keys("50")

    submit_button = driver.wait_for_xpath(
        '//button[@type="submit"][@name="topSourcesSubmit"]'
    )
    driver.scroll_to_element_and_click(submit_button)

    # Test that front-end views register as source views
    driver.click_xpath(f'//a/span[contains(.,"{obj_id}")]')
    driver.wait_for_xpath(f'//div[text()="{obj_id}"]')
    time.sleep(2)
    driver.get("/")
    driver.wait_for_xpath("//*[contains(.,'1 view(s)')]")

    # Test that token requests are registered as source views
    status, data = api('GET', f'sources/{obj_id}', token=upload_data_token)
    time.sleep(1)
    assert status == 200
    driver.refresh()
    driver.wait_for_xpath("//*[contains(.,'2 view(s)')]")


@pytest.mark.flaky(reruns=2)
def test_top_source_prefs(driver, user, public_group, upload_data_token):
    # Add an old source and give it an old view
    obj_id = str(uuid.uuid4())
    status, data = api(
        'POST',
        'sources',
        data={
            'id': obj_id,
            'ra': 50.4,
            'dec': 22.33,
            'redshift': 2.1,
            "altdata": {"simbad": {"class": "RRLyr"}},
            'transient': False,
            'ra_dis': 2.3,
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['data']['id'] == obj_id

    twenty_days_ago = datetime.datetime.now() - datetime.timedelta(days=20)
    sv = SourceView(
        obj_id=obj_id,
        username_or_token_id=upload_data_token,
        is_token=True,
        created_at=twenty_days_ago,
    )
    ThreadSession().add(sv)
    ThreadSession().commit()

    driver.get(f'/become_user/{user.id}')
    driver.get('/')
    # Wait for just top source widget to show up
    last_30_days_button = "//button[contains(@data-testid, 'topSources_30days')]"
    driver.wait_for_xpath(last_30_days_button)

    # edit the preferences to show more than the default 10 sources
    settings_button = driver.wait_for_xpath('//*[@id="topSourcesSettingsIcon"]')
    driver.scroll_to_element_and_click(settings_button)

    input = driver.wait_for_xpath('//input[@name="maxNumSources"]')
    driver.scroll_to_element_and_click(input)
    input.send_keys("50")

    submit_button = driver.wait_for_xpath(
        '//button[@type="submit"][@name="topSourcesSubmit"]'
    )
    driver.scroll_to_element_and_click(submit_button)

    # Test that source doesn't show up in last 7 days of views
    source_view_xpath = f"//div[@data-testid='topSourceItem_{obj_id}']"
    driver.wait_for_xpath_to_disappear(source_view_xpath)

    # Test that source view appears after changing prefs
    driver.click_xpath(last_30_days_button)
    driver.wait_for_xpath(source_view_xpath)
