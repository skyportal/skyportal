import uuid
import datetime

import pytest
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException

from skyportal.tests import api


@pytest.mark.flaky(reruns=2)
def test_recent_sources(driver, user, public_group, upload_data_token):
    obj_id = str(uuid.uuid4())
    ra = 50.1
    redshift = 2.5
    status, data = api(
        'POST',
        'sources',
        data={
            'id': obj_id,
            'ra': ra,
            'dec': 22.33,
            'redshift': redshift,
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
    recent_source_dataid = "recentSourceItem"
    recent_source_item = driver.wait_for_xpath(
        f'//div[starts-with(@data-testid, "{recent_source_dataid}")][.//span[text()="a few seconds ago"]][.//span[contains(text(), "{obj_id}")]]'
    )

    # Hover over item to see quick view button and click it
    ActionChains(driver).move_to_element(recent_source_item).perform()
    driver.click_xpath("//div[contains(@data-testid, 'quickViewButton')]")

    driver.wait_for_xpath_to_appear(
        "//*[@data-testid='source-quick-view-dialog-content']"
    )

    # Check dialog content
    driver.wait_for_xpath(f'//h4[text()="{obj_id}"]')
    driver.wait_for_xpath(f'//div[text()[contains(., "{redshift}")]]')
    driver.wait_for_xpath(f'//div[text()[contains(., "{ra}")]]')
    group_name = public_group.name[0:15]
    driver.wait_for_xpath(
        f'//span[contains(@class, "MuiChip-label")][text()="{group_name}"]'
    )
    driver.click_xpath("//div[contains(@class, 'sourceLinkButton')]")


@pytest.mark.flaky(reruns=2)
def test_hidden_recent_source(driver, user_no_groups, public_group, upload_data_token):
    obj_id = str(uuid.uuid4())
    ra = 50.1
    redshift = 2.5
    status, data = api(
        'POST',
        'sources',
        data={
            'id': obj_id,
            'ra': ra,
            'dec': 22.33,
            'redshift': redshift,
            "altdata": {"simbad": {"class": "RRLyr"}},
            'transient': False,
            'ra_dis': 2.3,
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['data']['id'] == obj_id

    driver.get(f'/become_user/{user_no_groups.id}')
    driver.get('/')

    # Make sure just added source doesn't show up
    with pytest.raises(TimeoutException):
        recent_source_class = "makeStyles-recentSourceItemWithButton"
        driver.wait_for_xpath(
            f'//div[starts-with(@class, "{recent_source_class}")][.//span[text()="a few seconds ago"]][.//span[contains(text(), "{obj_id}")]]'
        )


def test_recently_saved_candidate(
    driver, user, public_group, public_filter, upload_data_token
):
    obj_id = str(uuid.uuid4())

    status, data = api(
        'POST',
        'candidates',
        data={
            'id': obj_id,
            'ra': 50.1,
            'dec': 22.33,
            'redshift': 2.5,
            "altdata": {"simbad": {"class": "RRLyr"}},
            'transient': False,
            'ra_dis': 2.3,
            'filter_ids': [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token,
    )
    assert status == 200

    status, data = api(
        'POST',
        'sources',
        data={'id': obj_id, 'group_ids': [public_group.id]},
        token=upload_data_token,
    )
    assert status == 200

    driver.get(f'/become_user/{user.id}')
    driver.get('/')
    driver.wait_for_xpath(
        f'//div[starts-with(@data-testid, "recentSourceItem")][.//span[text()="a few seconds ago"]][.//span[contains(text(), "{obj_id}")]]'
    )
