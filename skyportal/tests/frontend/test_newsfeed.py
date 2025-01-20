import uuid

import pytest
from selenium.webdriver.common.action_chains import ActionChains

from skyportal.tests import api

from .test_quick_search import remove_notification


@pytest.mark.flaky(reruns=2)
def test_news_feed(driver, user, public_group, upload_data_token, comment_token):
    obj_id_base = str(uuid.uuid4())
    for i in range(2):
        status, data = api(
            "POST",
            "sources",
            data={
                "id": f"{obj_id_base}_{i}",
                "ra": 234.22,
                "dec": -22.33,
                "redshift": 3,
                "transient": False,
                "ra_dis": 2.3,
                "group_ids": [public_group.id],
            },
            token=upload_data_token,
        )
        assert status == 200
        assert data["data"]["id"] == f"{obj_id_base}_{i}"

        status, data = api(
            "POST",
            f"sources/{obj_id_base}_{i}/comments",
            data={"obj_id": f"{obj_id_base}_{i}", "text": f"comment_text_{i}"},
            token=comment_token,
        )
        assert status == 200

    driver.get(f"/become_user/{user.id}")
    driver.get("/")
    driver.wait_for_xpath('//span[text()="a few seconds ago"]')
    driver.wait_for_xpath('//*[@id="newsFeedSettingsIcon"]')

    remove_notification(driver)

    driver.click_xpath('//*[@id="newsFeedSettingsIcon"]')
    driver.wait_for_xpath('//*[@data-testid="categories.includeCommentsFromBots"]')
    driver.click_xpath('//*[@data-testid="categories.includeCommentsFromBots"]')
    driver.click_xpath('//button[contains(., "Save")]')
    for i in range(2):
        # Source added item
        driver.wait_for_xpath(
            f'//div[contains(@class, "entryContent")][.//p[text()="New source saved"]][.//a[@href="/source/{obj_id_base}_{i}"]]'
        )

        # Comment item
        driver.wait_for_xpath(f'//p[contains(text(),"comment_text_{i}")]')


@pytest.mark.flaky(reruns=2)
def test_news_feed_prefs_widget(
    driver, user, public_group, upload_data_token, comment_token
):
    obj_id_base = str(uuid.uuid4())
    for i in range(2):
        status, data = api(
            "POST",
            "sources",
            data={
                "id": f"{obj_id_base}_{i}",
                "ra": 234.22,
                "dec": -22.33,
                "redshift": 3,
                "transient": False,
                "ra_dis": 2.3,
                "group_ids": [public_group.id],
            },
            token=upload_data_token,
        )
        assert status == 200
        assert data["data"]["id"] == f"{obj_id_base}_{i}"

        status, data = api(
            "POST",
            f"sources/{obj_id_base}_{i}/comments",
            data={"obj_id": f"{obj_id_base}_{i}", "text": f"comment_text_{i}"},
            token=comment_token,
        )
        assert status == 200

    driver.get(f"/become_user/{user.id}")
    driver.get("/")

    driver.wait_for_xpath('//span[text()="a few seconds ago"]')
    driver.wait_for_xpath('//*[@id="newsFeedSettingsIcon"]')

    remove_notification(driver)

    driver.click_xpath('//*[@id="newsFeedSettingsIcon"]')
    driver.wait_for_xpath('//*[@data-testid="categories.includeCommentsFromBots"]')
    driver.click_xpath('//*[@data-testid="categories.includeCommentsFromBots"]')
    driver.click_xpath('//button[contains(., "Save")]')
    driver.wait_for_xpath('//span[text()="a few seconds ago"]')
    for i in range(2):
        # Source added item
        driver.wait_for_xpath(
            f'//div[contains(@class, "entryContent")][.//p[text()="New source saved"]][.//a[@href="/source/{obj_id_base}_{i}"]]'
        )

        # Comment item
        driver.wait_for_xpath(f'//p[contains(text(),"comment_text_{i}")]')

    driver.click_xpath('//*[@id="newsFeedSettingsIcon"]')
    n_items_input = driver.wait_for_xpath('//*[@data-testid="numItems"]//input')
    n_items_input.clear()
    ActionChains(driver).click(n_items_input).send_keys("2").perform()
    driver.click_xpath('//button[contains(., "Save")]')
    source_added_item_xpath = f'//div[contains(@class, "entryContent")][.//p[text()="New source saved"]][.//a[@href="/source/{obj_id_base}_0"]]'
    driver.wait_for_xpath_to_disappear(source_added_item_xpath)

    driver.click_xpath('//*[@id="newsFeedSettingsIcon"]')
    n_items_input = driver.wait_for_xpath('//*[@data-testid="numItems"]//input')
    n_items_input.clear()
    ActionChains(driver).send_keys_to_element(n_items_input, "4").perform()
    driver.click_xpath('//button[contains(., "Save")]')
    driver.wait_for_xpath(source_added_item_xpath)

    driver.click_xpath('//*[@id="newsFeedSettingsIcon"]')
    driver.click_xpath('//*[@data-testid="categories.sources"]')
    driver.click_xpath('//button[contains(., "Save")]')
    for i in range(2):
        # Source added item
        driver.wait_for_xpath_to_disappear(
            f'//div[contains(@class, "entryContent")][.//p[text()="New source saved"]][.//a[@href="/source/{obj_id_base}_{i}"]]'
        )

    driver.click_xpath('//*[@id="newsFeedSettingsIcon"]')
    driver.click_xpath('//*[@data-testid="categories.comments"]')
    driver.click_xpath('//button[contains(., "Save")]')
    for i in range(2):
        # Comment item
        driver.wait_for_xpath_to_disappear(f'//p[contains(text(),"comment_text_{i}")]')
    driver.click_xpath('//*[@id="newsFeedSettingsIcon"]')
    driver.click_xpath('//*[@data-testid="categories.comments"]')
    driver.click_xpath('//button[contains(., "Save")]')
    for i in range(2):
        # Comment item
        driver.wait_for_xpath(f'//p[contains(text(),"comment_text_{i}")]')
    driver.click_xpath('//*[@id="newsFeedSettingsIcon"]')
    driver.click_xpath('//*[@data-testid="categories.includeCommentsFromBots"]')
    driver.click_xpath('//button[contains(., "Save")]')
    for i in range(2):
        # Comment item
        driver.wait_for_xpath_to_disappear(f'//p[contains(text(),"comment_text_{i}")]')
