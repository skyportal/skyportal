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
    expect(page.locator('//*[text()="Skycam"]').first).to_be_visible()
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
    expect(page.locator('//*[text()="Skycam"]').first).to_be_visible()
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
    expect(
        page.locator('//*[text()="No skycam link configured"]').first
    ).to_be_visible()


def test_observing_run_columns_are_sortable(
    page,
    super_admin_user,
    super_admin_token,
    red_transients_run,
    public_ZTF20acgrjqm,
    public_ZTFe028h94k,
):
    # these four columns regressed to sortable: false in the
    # mui-datatables -> x-data-grid migration (#6145)
    for obj in [public_ZTFe028h94k, public_ZTF20acgrjqm]:
        status, _ = post_assignment(
            obj,
            red_transients_run,
            priority="3",
            comment="Observe please",
            token=super_admin_token,
        )
        assert status == 200

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/run/{red_transients_run.id}")
    expect(
        page.locator(f'//*[text()="{public_ZTF20acgrjqm.id}"]').first
    ).to_be_visible()

    for field in ["ra", "dec", "rise_time_utc", "set_time_utc"]:
        expect(
            page.locator(
                f'//*[@role="columnheader" and @data-field="{field}" and '
                'contains(@class, "MuiDataGrid-columnHeader--sortable")]'
            ).first
        ).to_be_attached()

    # public_ZTF20acgrjqm is at RA 65.06, public_ZTFe028h94k at RA 229.96
    ra_header = page.locator('//*[@role="columnheader" and @data-field="ra"]').first
    first_target = page.locator('//*[@data-field="target_name"]//a').first

    ra_header.click()
    expect(first_target).to_have_text(public_ZTF20acgrjqm.id)
    ra_header.click()
    expect(first_target).to_have_text(public_ZTFe028h94k.id)


def test_observing_run_expanded_row_stays_with_its_target_when_sorted(
    page,
    super_admin_user,
    super_admin_token,
    red_transients_run,
    public_ZTF20acgrjqm,
    public_ZTFe028h94k,
):
    for obj in [public_ZTFe028h94k, public_ZTF20acgrjqm]:
        status, _ = post_assignment(
            obj,
            red_transients_run,
            priority="3",
            comment="Observe please",
            token=super_admin_token,
        )
        assert status == 200

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/run/{red_transients_run.id}")

    rows = page.locator('//*[@role="row" and @data-id]')
    expect(rows).to_have_count(2)

    expanded_id = rows.first.get_attribute("data-id")
    page.locator('//*[@id="expandable-button"]').first.click()
    expect(rows).to_have_count(3)

    # sort on a column that has always been sortable, so this stays a real
    # check on the detail row rather than on the sortable columns above
    page.locator(
        '//*[@role="columnheader" and @data-field="target_name"]'
    ).first.click()
    expect(rows).to_have_count(3)

    ids = rows.evaluate_all("nodes => nodes.map((node) => node.dataset.id)")
    assert ids.index(f"{expanded_id}__detail") == ids.index(expanded_id) + 1


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
