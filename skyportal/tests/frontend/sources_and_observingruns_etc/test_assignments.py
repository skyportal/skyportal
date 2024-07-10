import uuid
import pytest

from selenium.common.exceptions import TimeoutException


@pytest.mark.flaky(reruns=2)
def test_submit_and_delete_new_assignment(
    driver, super_admin_user, public_source, red_transients_run
):
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/source/{public_source.id}")

    # wait for plots to load, if any
    try:
        driver.wait_for_xpath(
            '//div[@id="photometry-plot"]/div/div/div[@class="plot-container plotly"]',
            timeout=5,
        )
        driver.wait_for_xpath(
            '//div[@id="spectroscopy-plot"]/div/div/div[@class="plot-container plotly"]',
            timeout=5,
        )
    except TimeoutException:
        pass

    assign_select = driver.wait_for_xpath('//*[@aria-labelledby="assignmentSelect"]')
    driver.scroll_to_element_and_click(assign_select)
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

    driver.scroll_to_element_and_click(comment_box)
    comment_box.send_keys(comment_text)

    driver.click_xpath("//header")

    submit_button = driver.wait_for_xpath('//*[@name="assignmentSubmitButton"]')
    driver.scroll_to_element_and_click(submit_button)

    driver.wait_for_xpath(f'//*[text()="{comment_text}"]')

    # delete the assignment
    delete_button = driver.wait_for_xpath(
        '//*[starts-with(@id, "delete_button_assignment_")]'
    )
    delete_button.click()
    driver.wait_for_xpath("//*[contains(text(), 'Confirm')]").click()

    driver.wait_for_xpath_to_disappear(f'//*[text()="{comment_text}"]')
