import pytest


@pytest.mark.flaky(reruns=2)
def test_slack_integration(driver, user):
    driver.get(f"/become_user/{user.id}")
    driver.get("/profile")
    slack_toggle = driver.wait_for_xpath('//*[@data-testid="slack_toggle"]')

    if not slack_toggle.is_selected():
        slack_toggle.click()

    # uncheck the integration toggle
    slack_toggle.click()
