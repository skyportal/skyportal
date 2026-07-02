import time
import uuid

from playwright.sync_api import expect

from skyportal.models import DBSession, ObservingRun
from skyportal.tests import api


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


def test_source_is_added_to_observing_run_via_frontend(
    page, super_admin_user, public_source, red_transients_run
):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/source/{public_source.id}")

    page.locator(
        '//*[@role="combobox" and (@aria-labelledby="assignmentSelect" or @id="assignmentSelect")]'
    ).first.click()
    observingrun_title = (
        f"{red_transients_run.calendar_date} "
        f"{red_transients_run.instrument.name}/"
        f"{red_transients_run.instrument.telescope.nickname} "
        f"(PI: {red_transients_run.pi} / "
        f"Group: {red_transients_run.group.name})"
    )
    expect(page.locator(f'//*[text()="{observingrun_title}"]').first).to_be_visible()
    page.locator(f'//li[@data-value="{red_transients_run.id}"]').first.click()

    comment_text = str(uuid.uuid4())
    page.locator("//*[@data-testid='assignmentCommentInput']/div/textarea").first.fill(
        comment_text
    )
    page.locator('//*[@data-testid="assignmentSubmitButton"]').first.click()

    page.goto(f"/run/{red_transients_run.id}")
    # long timeout to give the backend time to perform ephemeris calcs
    expect(page.locator(f'//*[text()="{public_source.id}"]').first).to_be_visible()
    expect(page.locator(f'//*[text()="{comment_text}"]').first).to_be_visible()


def test_assignment_posts_to_observing_run(
    page, super_admin_user, public_source, red_transients_run, super_admin_token
):
    page.goto(f"/become_user/{super_admin_user.id}")

    status, data = post_assignment(
        public_source,
        red_transients_run,
        priority="3",
        comment="Observe please",
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    page.goto(f"/run/{red_transients_run.id}")
    expect(page.locator(f'//*[text()="{public_source.id}"]').first).to_be_visible()
    for group in [s.group for s in public_source.sources]:
        locator = page.locator(f'//span[text()="{group.name[:15]}"]').first
        if group.single_user_group:
            expect(locator).to_be_hidden()
        else:
            expect(locator).to_be_visible()


def test_observing_run_skycam_component(
    page, super_admin_user, public_source, red_transients_run, super_admin_token
):
    page.goto(f"/become_user/{super_admin_user.id}")

    status, data = post_assignment(
        public_source,
        red_transients_run,
        priority="3",
        comment="Observe please",
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    page.goto(f"/run/{red_transients_run.id}")
    expect(page.locator('//*[text()="Current Conditions"]').first).to_be_visible()
    expect(
        page.locator(
            f'//img[contains(@src, "{red_transients_run.instrument.telescope.skycam_link}")]'
        ).first
    ).to_be_visible()

    red_transients_run.instrument.telescope.skycam_link = (
        "http://this.is.a.bad.link.web.biz"
    )
    DBSession().add(red_transients_run.instrument.telescope)
    DBSession().commit()

    page.goto(f"/run/{red_transients_run.id}")
    expect(
        page.locator(
            f'//b[contains(text(), "{red_transients_run.instrument.name}")]'
        ).first
    ).to_be_visible()
    expect(page.locator('//*[text()="Current Conditions"]').first).to_be_visible()
    expect(
        page.locator('//img[contains(@src, "static/images/static.jpg")]').first
    ).to_be_visible()

    red_transients_run.instrument.telescope.skycam_link = None
    DBSession().add(red_transients_run.instrument.telescope)
    DBSession().commit()

    page.goto(f"/run/{red_transients_run.id}")
    expect(
        page.locator(
            f'//b[contains(text(), "{red_transients_run.instrument.name}")]'
        ).first
    ).to_be_visible()
    expect(page.locator('//*[text()="Current Conditions"]').first).to_be_hidden()


def test_observing_run_page(page, view_only_user, red_transients_run):
    page.goto(f"/become_user/{view_only_user.id}")
    page.goto("/runs")
    runs = ObservingRun.query.all()

    page.locator('//button[contains(., "All runs")]').first.click()

    for run in runs:
        observingrun_title = (
            f"{run.calendar_date} "
            f"{run.instrument.name}/"
            f"{run.instrument.telescope.nickname} "
            f"(PI: {run.pi} / "
            f"Group: {run.group.name})"
        )
        expect(
            page.locator(f'//*[text()="{observingrun_title}"]').first
        ).to_be_visible()


def test_add_run_to_observing_run_page(
    page, user, lris, public_group, red_transients_run
):
    page.goto(f"/become_user/{user.id}")
    page.goto("/runs")

    expect(page.locator("//form").first).to_be_visible()
    page.locator('//button[contains(., "All runs")]').first.click()

    observingrun_title = (
        f"{red_transients_run.calendar_date} "
        f"{red_transients_run.instrument.name}/"
        f"{red_transients_run.instrument.telescope.nickname} "
        f"(PI: {red_transients_run.pi} / "
        f"Group: {red_transients_run.group.name})"
    )
    expect(page.locator(f'//*[text()="{observingrun_title}"]').first).to_be_visible()

    calendar_keys = "01022021"
    observer = uuid.uuid4().hex
    pi_name = uuid.uuid4().hex

    page.locator('//input[@id="root_pi"]').first.click()
    page.keyboard.type(pi_name)
    page.keyboard.press("Tab")
    page.keyboard.type(calendar_keys)
    page.keyboard.press("Tab")
    page.keyboard.type(observer)

    # instruments
    page.locator('//*[@id="root_instrument_id"]').first.click()
    page.locator(f'//li[contains(text(), "{lris.name}")]').first.click()
    time.sleep(1)

    # groups
    page.locator('//*[@id="root_group_id"]').first.click()
    page.locator(f'//li[contains(text(), "{public_group.name}")]').first.click()

    page.locator('//button[@type="submit"]').first.click()

    expect(
        page.locator(
            f"""//*[text()='2021-01-02 {lris.name}/{lris.telescope.nickname} (PI: {pi_name} / Group: {public_group.name})']"""
        ).first
    ).to_be_visible()
