import pytest


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
    driver.wait_for_xpath(
        f'//*[text()="{user.username} mentioned you in a comment on {public_source.id}"]'
    )
    driver.click_xpath('//*[contains(@data-testid, "markReadButton")]')
    driver.wait_for_xpath_to_disappear("//span[text()='1']")
    driver.click_xpath('//*[contains(@data-testid, "deleteNotificationButton")]')
    driver.wait_for_xpath_to_disappear(
        f'//*[text()="{user.username} mentioned you in a comment on {public_source.id}"]'
    )
    driver.wait_for_xpath("//*[text()='No notifications']")
