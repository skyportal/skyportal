import pytest
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys


@pytest.mark.flaky(reruns=2)
def test_slack_url(driver, user):
    good_path = "https://hooks.slack.com/"
    bad_path = "http://garbage.url"

    driver.get(f"/become_user/{user.id}")
    driver.get("/profile")
    slack_toggle = driver.wait_for_xpath('//*[@data-testid="slack_toggle"]')

    if not slack_toggle.is_selected():
        slack_toggle.click()

    driver.wait_for_xpath('//*[@data-testid="slack_url"]')
    url_path = driver.wait_for_xpath('//input[@name="url"]')
    url_path.clear()
    url_path.send_keys(bad_path, Keys.ENTER)

    # Click somewhere outside to remove focus from the URL entry
    header = driver.wait_for_xpath("//header")
    ActionChains(driver).move_to_element(header).click().perform()

    # since we added a bad URL, check for the error message
    driver.wait_for_xpath('//*[text()="Must be a Slack URL"]')

    # now add a good path and make sure the error goes away
    url_path = driver.wait_for_xpath('//input[@name="url"]')
    url_path.clear()
    url_path.send_keys(good_path, Keys.ENTER)
    header = driver.wait_for_xpath("//header")
    ActionChains(driver).move_to_element(header).click().perform()
    driver.wait_for_xpath_to_disappear('//*[text()="Must be a Slack URL"]')
