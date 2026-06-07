from playwright.sync_api import expect

from skyportal.tests import api


def filter_for_value(page, value, last=False):
    # The x-data-grid default-toolbar quick-filter renders a TextField whose
    # `aria-label="Search"` lands on the wrapper (FormControl root div), not the
    # inner <input>. So target the input as a descendant of that wrapper.
    input_xpath = "//*[@aria-label='Search']//input"
    if last:
        input_xpath = f"({input_xpath})[last()]"
    page.locator(input_xpath).first.fill(value)


def test_group_admission_request_and_acceptance(
    page, user, super_admin_user, public_group, public_group2, view_only_token
):
    # Create the admission request via the API (a user can only request admission
    # for themselves, so use the user's own token) rather than the flaky /groups
    # request flow; the behavior under test is the admin acceptance UI below.
    status, _ = api(
        "POST",
        "group_admission_requests",
        data={"groupID": public_group2.id, "userID": user.id},
        token=view_only_token,
    )
    assert status == 200

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/group/{public_group2.id}")
    filter_for_value(page, user.username, last=True)
    expect(page.locator('//div[text()="pending"]').first).to_be_visible()
    page.locator(f'//*[@data-testid="acceptRequestButton{user.id}"]').first.click()
    expect(page.locator('//div[text()="accepted"]').first).to_be_visible()
    expect(page.locator(f'//a[text()="{user.username}"]').first).to_be_visible()


def test_group_admission_request_insufficient_stream_access(
    page,
    user_no_groups_no_streams,
    public_group,
):
    page.goto(f"/become_user/{user_no_groups_no_streams.id}")
    page.goto("/groups")
    expect(page.locator('//h6[text()="My Groups"]').first).to_be_visible()
    filter_for_value(page, public_group.name)
    page.locator(
        f'//*[@data-testid="requestAdmissionButton{public_group.id}"]'
    ).first.click()
    expect(
        page.locator(
            '//*[contains(text(), "does not have access to the following streams")]'
        ).first
    ).to_be_visible()
