import pytest
from selenium.common.exceptions import TimeoutException


def remove_notification(driver):
    notification_xpath = '//*[contains(@data-testid, "notification-")]'
    n_retries = 0  # we enforce a max, just to not have a runaway loop
    while n_retries < 5:
        try:
            driver.click_xpath(notification_xpath, timeout=3)
            driver.wait_for_xpath_to_disappear(notification_xpath, timeout=3)
        except TimeoutException:
            try:
                driver.wait_for_xpath_to_disappear(notification_xpath, timeout=3)
                break
            except TimeoutException:
                pass


@pytest.mark.flaky(reruns=3)
def test_quick_search(
    driver,
    super_admin_user,
    public_source,
    public_group,
):
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get("/")
    remove_notification(driver)

    driver.wait_for_xpath('//*[@id="quick-search-bar"]').send_keys(public_source.id)
    driver.click_xpath('//*[@id="quick-search-bar-listbox"]')
    # Should be redirected to source page; check for elements that should render
    driver.wait_for_xpath(f'//h6[text()="{public_source.id}"]')
    driver.wait_for_xpath(f'//span[text()="{public_group.name}"]')

    driver.wait_for_xpath('//*[@id="quick-search-bar"]').send_keys("invalid_source_id")
    driver.wait_for_xpath('//*[text()="No matching Sources."]')
