import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect


def remove_notification(page):
    notification = page.locator('[data-testid*="notification-"]')
    n_retries = 0  # we enforce a max, just to not have a runaway loop
    while n_retries < 5:
        try:
            notification.first.click(timeout=3000)
        except PlaywrightTimeoutError:
            return  # nothing to dismiss
        try:
            expect(notification).to_have_count(0, timeout=3000)
            return
        except AssertionError:
            pass
        n_retries += 1


@pytest.mark.flaky(reruns=3)
def test_quick_search(
    page,
    super_admin_user,
    public_source,
    public_group,
):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/")
    remove_notification(page)

    page.locator("#quick-search-bar").first.fill(public_source.id)
    page.locator("#quick-search-bar-listbox").first.click()
    # Should be redirected to source page; check for elements that should render
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()
    expect(page.locator(f'//span[text()="{public_group.name}"]').first).to_be_visible()

    page.locator("#quick-search-bar").first.fill("invalid_source_id")
    expect(page.locator('//*[text()="No matching Sources."]').first).to_be_visible()
