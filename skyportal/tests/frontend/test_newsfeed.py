import uuid
import pytest

from skyportal.tests import api


@pytest.mark.flaky(reruns=2)
def test_news_feed(
    driver, user, public_source, public_group, upload_data_token, comment_token
):
    obj_id_base = str(uuid.uuid4())
    for i in range(2):
        status, data = api(
            'POST',
            'sources',
            data={
                'id': f'{obj_id_base}_{i}',
                'ra': 234.22,
                'dec': -22.33,
                'redshift': 3,
                'transient': False,
                'ra_dis': 2.3,
                'group_ids': [public_group.id],
            },
            token=upload_data_token,
        )
        assert status == 200
        assert data['data']['id'] == f'{obj_id_base}_{i}'

        status, data = api(
            'POST',
            'comment',
            data={'obj_id': f'{obj_id_base}_{i}', 'text': f'comment_text_{i}'},
            token=comment_token,
        )
        assert status == 200

    driver.get(f'/become_user/{user.id}')
    driver.get('/')
    driver.wait_for_xpath(f'//span[text()="a few seconds ago"]')
    for i in range(2):
        # Source added item
        driver.wait_for_xpath(
            f'//div[contains(@class, "NewsFeed__entryContent")][span[text()="New source added"]][.//a[@href="/source/{obj_id_base}_{i}"]]'
        )

        # Comment item
        driver.wait_for_xpath(f'//span[contains(text(),"comment_text_{i}")]')


@pytest.mark.flaky(reruns=2)
def test_news_feed_prefs_widget(
    driver, user, public_source, public_group, upload_data_token, comment_token
):
    obj_id_base = str(uuid.uuid4())
    for i in range(2):
        status, data = api(
            'POST',
            'sources',
            data={
                'id': f'{obj_id_base}_{i}',
                'ra': 234.22,
                'dec': -22.33,
                'redshift': 3,
                'transient': False,
                'ra_dis': 2.3,
                'group_ids': [public_group.id],
            },
            token=upload_data_token,
        )
        assert status == 200
        assert data['data']['id'] == f'{obj_id_base}_{i}'

        status, data = api(
            'POST',
            'comment',
            data={'obj_id': f'{obj_id_base}_{i}', 'text': f'comment_text_{i}'},
            token=comment_token,
        )
        assert status == 200

    driver.get(f'/become_user/{user.id}')
    driver.get('/')
    driver.wait_for_xpath('//span[text()="a few seconds ago"]')
    for i in range(2):
        # Source added item
        driver.wait_for_xpath(
            f'//div[contains(@class, "NewsFeed__entryContent")][span[text()="New source added"]][.//a[@href="/source/{obj_id_base}_{i}"]]'
        )

        # Comment item
        driver.wait_for_xpath(f'//span[contains(text(),"comment_text_{i}")]')

    driver.wait_for_xpath('//*[@id="newsFeedSettingsIcon"]').click()
    n_items_input = driver.wait_for_xpath('//input[@name="numItems"]')
    n_items_input.clear()
    n_items_input.send_keys("2")
    driver.wait_for_xpath('//button[contains(., "Save")]').click()
    source_added_item_xpath = f'//div[contains(@class, "NewsFeed__entryContent")][span[text()="New source added"]][.//a[@href="/source/{obj_id_base}_0"]]'
    driver.wait_for_xpath_to_disappear(source_added_item_xpath)
    driver.wait_for_xpath('//*[@id="newsFeedSettingsIcon"]').click()
    n_items_input = driver.wait_for_xpath('//input[@name="numItems"]')
    n_items_input.clear()
    n_items_input.send_keys("4")
    driver.wait_for_xpath('//button[contains(., "Save")]').click()
    driver.wait_for_xpath(source_added_item_xpath)
