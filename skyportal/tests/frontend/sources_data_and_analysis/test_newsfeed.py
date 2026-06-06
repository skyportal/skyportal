import uuid

import pytest
from playwright.sync_api import expect

from skyportal.tests import api

from .test_quick_search import remove_notification


def _seed_sources_and_comments(api_, public_group, upload_data_token, comment_token):
    obj_id_base = str(uuid.uuid4())
    for i in range(2):
        status, data = api_(
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

        status, data = api_(
            "POST",
            f"sources/{obj_id_base}_{i}/comments",
            data={"obj_id": f"{obj_id_base}_{i}", "text": f"comment_text_{i}"},
            token=comment_token,
        )
        assert status == 200
    return obj_id_base


def _set_num_items(page, value):
    n_items_input = page.locator('//*[@data-testid="numItems"]//input').first
    n_items_input.click()
    n_items_input.press("ControlOrMeta+a")
    n_items_input.press_sequentially(value)


@pytest.mark.flaky(reruns=3)
def test_news_feed(page, user, public_group, upload_data_token, comment_token):
    obj_id_base = _seed_sources_and_comments(
        api, public_group, upload_data_token, comment_token
    )

    page.goto(f"/become_user/{user.id}")
    page.goto("/")
    expect(page.locator('//span[text()="a few seconds ago"]').first).to_be_visible()
    expect(page.locator('//*[@id="newsFeedSettingsIcon"]').first).to_be_visible()

    remove_notification(page)

    page.locator('//*[@id="newsFeedSettingsIcon"]').first.click()
    expect(
        page.locator('//*[@data-testid="categories.includeCommentsFromBots"]').first
    ).to_be_visible()
    page.locator('//*[@data-testid="categories.includeCommentsFromBots"]').first.click()
    page.locator('//form//button[@type="submit" and contains(., "Save")]').first.click()
    for i in range(2):
        expect(
            page.locator(
                f'//div[contains(@class, "entryContent")][.//p[text()="New source saved"]][.//a[@href="/source/{obj_id_base}_{i}"]]'
            ).first
        ).to_be_visible()
        expect(
            page.locator(f'//p[contains(text(),"comment_text_{i}")]').first
        ).to_be_visible()


@pytest.mark.flaky(reruns=3)
def test_news_feed_prefs_widget(
    page, user, public_group, upload_data_token, comment_token
):
    obj_id_base = _seed_sources_and_comments(
        api, public_group, upload_data_token, comment_token
    )

    page.goto(f"/become_user/{user.id}")
    page.goto("/")

    expect(page.locator('//span[text()="a few seconds ago"]').first).to_be_visible()
    expect(page.locator('//*[@id="newsFeedSettingsIcon"]').first).to_be_visible()

    remove_notification(page)

    page.locator('//*[@id="newsFeedSettingsIcon"]').first.click()
    expect(
        page.locator('//*[@data-testid="categories.includeCommentsFromBots"]').first
    ).to_be_visible()
    page.locator('//*[@data-testid="categories.includeCommentsFromBots"]').first.click()
    page.locator('//form//button[@type="submit" and contains(., "Save")]').first.click()
    expect(page.locator('//span[text()="a few seconds ago"]').first).to_be_visible()
    for i in range(2):
        expect(
            page.locator(
                f'//div[contains(@class, "entryContent")][.//p[text()="New source saved"]][.//a[@href="/source/{obj_id_base}_{i}"]]'
            ).first
        ).to_be_visible()
        expect(
            page.locator(f'//p[contains(text(),"comment_text_{i}")]').first
        ).to_be_visible()

    source_added_item_xpath = f'//div[contains(@class, "entryContent")][.//p[text()="New source saved"]][.//a[@href="/source/{obj_id_base}_0"]]'

    page.locator('//*[@id="newsFeedSettingsIcon"]').first.click()
    _set_num_items(page, "2")
    page.locator('//form//button[@type="submit" and contains(., "Save")]').first.click()
    expect(page.locator(source_added_item_xpath).first).to_be_hidden()

    page.locator('//*[@id="newsFeedSettingsIcon"]').first.click()
    _set_num_items(page, "4")
    page.locator('//form//button[@type="submit" and contains(., "Save")]').first.click()
    expect(page.locator(source_added_item_xpath).first).to_be_visible()

    page.locator('//*[@id="newsFeedSettingsIcon"]').first.click()
    page.locator('//*[@data-testid="categories.sources"]').first.click()
    page.locator('//form//button[@type="submit" and contains(., "Save")]').first.click()
    for i in range(2):
        expect(
            page.locator(
                f'//div[contains(@class, "entryContent")][.//p[text()="New source saved"]][.//a[@href="/source/{obj_id_base}_{i}"]]'
            ).first
        ).to_be_hidden()

    page.locator('//*[@id="newsFeedSettingsIcon"]').first.click()
    page.locator('//*[@data-testid="categories.comments"]').first.click()
    page.locator('//form//button[@type="submit" and contains(., "Save")]').first.click()
    for i in range(2):
        expect(
            page.locator(f'//p[contains(text(),"comment_text_{i}")]').first
        ).to_be_hidden()

    page.locator('//*[@id="newsFeedSettingsIcon"]').first.click()
    page.locator('//*[@data-testid="categories.comments"]').first.click()
    page.locator('//form//button[@type="submit" and contains(., "Save")]').first.click()
    for i in range(2):
        expect(
            page.locator(f'//p[contains(text(),"comment_text_{i}")]').first
        ).to_be_visible()

    page.locator('//*[@id="newsFeedSettingsIcon"]').first.click()
    page.locator('//*[@data-testid="categories.includeCommentsFromBots"]').first.click()
    page.locator('//form//button[@type="submit" and contains(., "Save")]').first.click()
    for i in range(2):
        expect(
            page.locator(f'//p[contains(text(),"comment_text_{i}")]').first
        ).to_be_hidden()
