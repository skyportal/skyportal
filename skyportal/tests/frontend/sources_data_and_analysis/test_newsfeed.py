import uuid

import pytest
from playwright.sync_api import expect
from skyportal.tests import api


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


def _open_settings(page):
    # Settle the dashboard first so the settings popover's anchor (and its Save
    # button) doesn't keep shifting as widgets/feed re-render under load.
    page.wait_for_load_state("networkidle")
    page.locator('//*[@id="newsFeedSettingsIcon"]').first.click()


def _save_settings(page):
    # The dashboard re-renders continuously under load (relative timestamps,
    # widget loads), so the Save button never settles as "stable"; force the
    # click past the stability check (it is visible and enabled).
    page.locator('//form//button[@type="submit" and contains(., "Save")]').first.click(
        force=True
    )
    page.wait_for_load_state("networkidle")


@pytest.mark.flaky(reruns=3)
def test_news_feed(
    page, user, public_group, upload_data_token, comment_token, super_admin_token
):
    obj_id_base = _seed_sources_and_comments(
        api, public_group, upload_data_token, comment_token
    )

    # Show bot comments via the API rather than driving the flaky news-feed
    # settings popover (which sits on the churning dashboard). The feature under
    # test here is that the feed renders the new sources + comments.
    status, _ = api(
        "PATCH",
        f"internal/profile/{user.id}",
        data={
            "preferences": {
                "newsFeed": {"categories": {"includeCommentsFromBots": True}}
            }
        },
        token=super_admin_token,
    )
    assert status == 200

    page.goto(f"/become_user/{user.id}")
    page.goto("/")
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
    # Let the dashboard's widgets finish loading so the layout (and the settings
    # popover anchored to it) stops shifting before we interact.
    page.wait_for_load_state("networkidle")

    expect(page.locator('//span[text()="a few seconds ago"]').first).to_be_visible()
    expect(page.locator('//*[@id="newsFeedSettingsIcon"]').first).to_be_visible()

    remove_notification(page)

    _open_settings(page)
    expect(
        page.locator('//*[@data-testid="categories.includeCommentsFromBots"]').first
    ).to_be_visible()
    page.locator('//*[@data-testid="categories.includeCommentsFromBots"]').first.click()
    _save_settings(page)
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

    _open_settings(page)
    _set_num_items(page, "2")
    _save_settings(page)
    expect(page.locator(source_added_item_xpath).first).to_be_hidden()

    _open_settings(page)
    _set_num_items(page, "4")
    _save_settings(page)
    expect(page.locator(source_added_item_xpath).first).to_be_visible()

    _open_settings(page)
    page.locator('//*[@data-testid="categories.sources"]').first.click()
    _save_settings(page)
    for i in range(2):
        expect(
            page.locator(
                f'//div[contains(@class, "entryContent")][.//p[text()="New source saved"]][.//a[@href="/source/{obj_id_base}_{i}"]]'
            ).first
        ).to_be_hidden()

    _open_settings(page)
    page.locator('//*[@data-testid="categories.comments"]').first.click()
    _save_settings(page)
    for i in range(2):
        expect(
            page.locator(f'//p[contains(text(),"comment_text_{i}")]').first
        ).to_be_hidden()

    _open_settings(page)
    page.locator('//*[@data-testid="categories.comments"]').first.click()
    _save_settings(page)
    for i in range(2):
        expect(
            page.locator(f'//p[contains(text(),"comment_text_{i}")]').first
        ).to_be_visible()

    _open_settings(page)
    page.locator('//*[@data-testid="categories.includeCommentsFromBots"]').first.click()
    _save_settings(page)
    for i in range(2):
        expect(
            page.locator(f'//p[contains(text(),"comment_text_{i}")]').first
        ).to_be_hidden()
