import uuid
import pytest
from .. import api


def post_assignment(obj, run, priority, comment, token):
    return api(
        "POST",
        "assignment",
        data={
            "obj_id": obj.id,
            "run_id": run.id,
            "priority": priority,
            "comment": comment,
        },
        token=token,
    )


@pytest.mark.flaky(reruns=2)
def test_source_is_added_to_observing_run_via_frontend(
    driver, super_admin_user, public_source, red_transients_run
):
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/source/{public_source.id}")
    run_select = driver.wait_for_xpath('//*[@id="mui-component-select-run_id"]')
    driver.scroll_to_element_and_click(run_select)
    observingrun_title = (
        f"{red_transients_run.calendar_date} "
        f"{red_transients_run.instrument.name}/"
        f"{red_transients_run.instrument.telescope.nickname} "
        f"(PI: {red_transients_run.pi} / "
        f"Group: {red_transients_run.group.name})"
    )
    driver.wait_for_xpath(f'//*[text()="{observingrun_title}"]')
    driver.scroll_to_element_and_click(
        driver.wait_for_xpath(f'//li[@data-value="{red_transients_run.id}"]')
    )

    comment_box = driver.wait_for_xpath("//textarea[@name='comment']")
    comment_text = str(uuid.uuid4())
    comment_box.send_keys(comment_text)

    submit_button = driver.wait_for_xpath('//*[@name="assignmentSubmitButton"]')

    driver.scroll_to_element_and_click(submit_button)
    driver.get(f"/run/{red_transients_run.id}")
    driver.wait_for_xpath(f'//*[text()="{public_source.id}"]')


@pytest.mark.flaky(reruns=2)
def test_assignment_posts_to_observing_run(
    driver, super_admin_user, public_source, red_transients_run, super_admin_token
):

    driver.get(f"/become_user/{super_admin_user.id}")

    status, data = post_assignment(
        public_source,
        red_transients_run,
        priority="3",
        comment="Observe please",
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"

    driver.get(f"/run/{red_transients_run.id}")
    driver.wait_for_xpath(f'//*[text()="{public_source.id}"]')
