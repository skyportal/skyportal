import pytest


@pytest.mark.flaky(reruns=2)
def test_slack_integration(driver, user):
    driver.get(f'/become_user/{user.id}')
    driver.get('/profile')
    slack_toggle = driver.wait_for_xpath('//*[@data-testid="slack_toggle"]')

    if not slack_toggle.is_selected():
        slack_toggle.click()

    # check to see if the @mentions and "Also push to Slack" appear
    driver.wait_for_xpath('//*[@data-testid="slack_mentions"]')
    driver.wait_for_xpath('//*[@data-testid="slack_also_push"]')

    # uncheck the integration toggle
    slack_toggle.click()

    # make sure that the options go away
    driver.wait_for_xpath_to_disappear('//*[@data-testid="slack_mentions"]')
    driver.wait_for_xpath_to_disappear('//*[@data-testid="slack_also_push"]')
