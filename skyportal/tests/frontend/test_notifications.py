import pytest

from skyportal.tests import api


def filter_for_value(driver, value, last=False):
    if last:
        xpath = '(//*[@data-testid="Search-iconButton"])[last()]'
    else:
        xpath = '//*[@data-testid="Search-iconButton"]'
    driver.click_xpath(xpath)
    search_input_xpath = "//input[@aria-label='Search']"
    search_input = driver.wait_for_xpath(search_input_xpath)
    driver.click_xpath(search_input_xpath)
    search_input.send_keys(value)


@pytest.mark.flaky(reruns=2)
def test_mention_generates_notification_then_mark_read_and_delete(
    driver, user, public_source
):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')

    comment_box = driver.wait_for_xpath("//input[@name='text']")
    comment_text = f"@{user.username}"
    comment_box.send_keys(comment_text)
    driver.click_xpath('//*[@name="submitCommentButton"]')
    driver.wait_for_xpath(f'//p[text()="{comment_text}"]')

    driver.wait_for_xpath("//span[text()='1']")
    driver.click_xpath('//*[@data-testid="notificationsButton"]')
    driver.wait_for_xpath('//*[text()=" mentioned you in a comment on "]')
    driver.click_xpath('//*[contains(@data-testid, "markReadButton")]')
    driver.wait_for_xpath_to_disappear("//span[text()='1']")
    driver.click_xpath('//*[contains(@data-testid, "deleteNotificationButton")]')
    driver.wait_for_xpath_to_disappear('//*[text()=" mentioned you in a comment on "]')
    driver.wait_for_xpath("//*[text()='No notifications']")


@pytest.mark.flaky(reruns=2)
def test_group_admission_requests_notifications(
    driver,
    user,
    super_admin_user,
    public_group,
    public_group2,
    super_admin_token,
):
    # Make super_admin_user an admin member of group2
    status, data = api(
        "POST",
        f"groups/{public_group2.id}/users",
        data={"userID": super_admin_user.id, "admin": True},
        token=super_admin_token,
    )
    assert status == 200

    driver.get(f'/become_user/{user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h6[text()="My Groups"]')
    filter_for_value(driver, public_group2.name)
    driver.click_xpath(f'//*[@data-testid="requestAdmissionButton{public_group2.id}"]')
    driver.wait_for_xpath(
        f'//*[@data-testid="deleteAdmissionRequestButton{public_group2.id}"]'
    )
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/group/{public_group2.id}")
    driver.click_xpath('//*[@data-testid="notificationsButton"]')
    driver.wait_for_xpath('//*[text()=" has requested to join "]')
    driver.click_xpath('//*[@data-testid="deleteAllNotificationsButton"]')
    driver.wait_for_xpath_to_disappear('//*[text()=" has requested to join "]')

    filter_for_value(driver, user.username, last=True)
    driver.wait_for_xpath('//div[text()="pending"]')
    driver.click_xpath(f'//*[@data-testid="acceptRequestButton{user.id}"]')
    driver.wait_for_xpath('//div[text()="accepted"]')
    driver.wait_for_xpath(f'//a[text()="{user.username}"]')

    driver.get(f'/become_user/{user.id}')
    driver.get("/")
    driver.click_xpath('//*[@data-testid="notificationsButton"]')
    driver.wait_for_xpath('//em[text()="accepted"]')
    driver.wait_for_xpath(f'//em[text()="{public_group2.name}"]')
