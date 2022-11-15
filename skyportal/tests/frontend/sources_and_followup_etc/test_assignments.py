import uuid
import pytest


@pytest.mark.flaky(reruns=2)
def test_submit_and_delete_new_assignment(
    driver, super_admin_user, public_source, red_transients_run
):
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.click_xpath('//*[@aria-labelledby="assignmentSelect"]', wait_clickable=False)
    observingrun_title = (
        f"{red_transients_run.calendar_date} "
        f"{red_transients_run.instrument.name}/"
        f"{red_transients_run.instrument.telescope.nickname} "
        f"(PI: {red_transients_run.pi} / "
        f"Group: {red_transients_run.group.name})"
    )
    driver.wait_for_xpath(f'//*[text()="{observingrun_title}"]')
    driver.click_xpath(
        f'//li[@data-value="{red_transients_run.id}"]', scroll_parent=True
    )
    # Click somewhere outside to remove focus from run select
    driver.click_xpath("//header")

    comment_box = driver.wait_for_xpath("//textarea[@name='comment']")
    comment_text = str(uuid.uuid4())
    comment_box.send_keys(comment_text)

    driver.click_xpath('//*[@name="assignmentSubmitButton"]')

    driver.click_xpath("//div[@id='observing-run-assignments-header']")
    driver.wait_for_xpath('//button[@aria-label="delete-assignment"]')
    driver.wait_for_xpath(f'//*[text()="{comment_text}"]')
    driver.click_xpath('//button[@aria-label="delete-assignment"]')
    driver.wait_for_xpath_to_disappear('//button[@aria-label="delete-assignment"]')
    driver.wait_for_xpath_to_disappear(f'//*[text()="{comment_text}"]')
