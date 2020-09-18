import uuid
import pytest
from ...models import DBSession, ObservingRun
from .. import api

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


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
    driver.wait_for_xpath(f'//*[text()="{comment_text}"]')


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


@pytest.mark.flaky(reruns=2)
def test_observing_run_skycam_component(
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
    driver.wait_for_xpath('//*[text()="Current Conditions"]')
    driver.wait_for_xpath(
        f'//img[contains(@src, "{red_transients_run.instrument.telescope.skycam_link}")]'
    )

    red_transients_run.instrument.telescope.skycam_link = (
        'http://this.is.a.bad.link.web.biz'
    )
    DBSession().add(red_transients_run.instrument.telescope)
    DBSession().commit()

    driver.get(f"/run/{red_transients_run.id}")
    driver.wait_for_xpath(
        f'//b[contains(text(), "{red_transients_run.instrument.name}")]'
    )
    driver.wait_for_xpath('//*[text()="Current Conditions"]')
    fallback_url = "static/images/static.jpg"
    driver.wait_for_xpath(f'//img[contains(@src, "{fallback_url}")]')

    red_transients_run.instrument.telescope.skycam_link = None
    DBSession().add(red_transients_run.instrument.telescope)
    DBSession().commit()

    driver.get(f"/run/{red_transients_run.id}")
    driver.wait_for_xpath(
        f'//b[contains(text(), "{red_transients_run.instrument.name}")]'
    )
    driver.wait_for_xpath_to_disappear('//*[text()="Current Conditions"]')
    driver.wait_for_xpath_to_disappear(
        f'//img[contains(@src, "{red_transients_run.instrument.telescope.skycam_link}")]'
    )


@pytest.mark.flaky(reruns=2)
def test_observing_run_page(driver, view_only_user, red_transients_run):
    driver.get(f'/become_user/{view_only_user.id}')
    driver.get(f'/runs')
    runs = ObservingRun.query.all()

    for run in runs:
        observingrun_title = (
            f"{run.calendar_date} "
            f"{run.instrument.name}/"
            f"{run.instrument.telescope.nickname} "
            f"(PI: {run.pi} / "
            f"Group: {run.group.name})"
        )

        driver.wait_for_xpath(f'//*[text()="{observingrun_title}"]')


@pytest.mark.flaky(reruns=2)
def test_add_run_to_observing_run_page(
    driver, user, lris, public_group, red_transients_run
):
    driver.get(f'/become_user/{user.id}')
    driver.get(f'/runs')

    driver.wait_for_xpath('//form')
    observingrun_title = (
        f"{red_transients_run.calendar_date} "
        f"{red_transients_run.instrument.name}/"
        f"{red_transients_run.instrument.telescope.nickname} "
        f"(PI: {red_transients_run.pi} / "
        f"Group: {red_transients_run.group.name})"
    )

    # long timeout as it can take a long time for the telescopelist,
    # observingrun list, and instrumentlist to fully load on
    # when these lists are long and the webserver is strained
    driver.wait_for_xpath(f'//*[text()="{observingrun_title}"]', timeout=15)

    pi_element = driver.wait_for_xpath('//input[@id="root_pi"]')

    calendar_keys = '02022021'
    observer = uuid.uuid4().hex
    pi_name = uuid.uuid4().hex

    ActionChains(driver).click(pi_element).pause(1).send_keys(pi_name).pause(
        1
    ).send_keys(Keys.TAB).send_keys(calendar_keys).pause(1).send_keys(Keys.TAB).pause(
        1
    ).send_keys(
        observer
    ).pause(
        1
    ).perform()

    instruments_element = driver.wait_for_xpath('//*[@id="root_instrument_id"]')

    ActionChains(driver).click(instruments_element).pause(1).perform()

    lris_element = driver.wait_for_xpath(f'//li[@data-value="{lris.id}"]')
    driver.scroll_to_element(lris_element)
    ActionChains(driver).click(lris_element).pause(1).perform()

    groups_element = driver.wait_for_xpath('//*[@id="root_group_id"]')

    ActionChains(driver).click(groups_element).pause(1).perform()

    public_group_element = driver.wait_for_xpath(
        f'//li[@data-value="{public_group.id}"]'
    )
    ActionChains(driver).click(public_group_element).pause(1).perform()

    submit_button = driver.wait_for_xpath('//button[@type="submit"]')
    ActionChains(driver).click(submit_button).pause(1).perform()

    # long timeout as it can take a long time for the telescopelist,
    # observingrun list, and instrumentlist to fully load on
    # when these lists are long and the webserver is strained
    driver.wait_for_xpath(
        f'''//*[text()='2021-02-02 {lris.name}/{lris.telescope.nickname} (PI: {pi_name} / Group: {public_group.name})']''',
        timeout=15,
    )
