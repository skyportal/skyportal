import pytest
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


@pytest.mark.flaky(reruns=3)
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
    # The group page is heavy; the admission-requests grid can render slowly under
    # load. Wait for this user's accept button directly (it's the only request on a
    # fresh group) instead of driving the grid's quick-filter, whose render timing
    # vs. the Search box is racy and was the source of the CI flake.
    accept_button = page.locator(
        f'//*[@data-testid="acceptRequestButton{user.id}"]'
    ).first
    expect(accept_button).to_be_visible(timeout=180000)
    expect(page.locator('//div[text()="pending"]').first).to_be_visible()
    accept_button.click()
    expect(page.locator('//div[text()="accepted"]').first).to_be_visible()
    expect(page.locator(f'//a[text()="{user.username}"]').first).to_be_visible()


def test_group_admission_auto_accept_join_button(
    page, user_group2, public_group, group_admin_token
):
    # A group admin enables auto-accept on the group
    status, _ = api(
        "PUT",
        f"groups/{public_group.id}",
        data={"name": public_group.name, "auto_accept_requests": True},
        token=group_admin_token,
    )
    assert status == 200

    page.goto(f"/become_user/{user_group2.id}")
    page.goto("/groups")
    page.get_by_role("tab", name="Non-member groups").click()
    filter_for_value(page, public_group.name)
    # For an auto-accept group the action reads "Join group", not "Request admission"
    join_button = page.locator(
        f'//*[@data-testid="requestAdmissionButton{public_group.id}"]'
    ).first
    expect(join_button).to_have_text("Join group")
    join_button.click()
    # After joining, the group moves into the user's "My Groups" list
    page.get_by_role("tab", name="My Groups").click()
    expect(page.locator(f'//div[@data-id="{public_group.id}"]').first).to_be_visible()


def test_group_admission_request_insufficient_stream_access(
    page,
    user_no_groups_no_streams,
    public_group,
    public_stream,
):
    page.goto(f"/become_user/{user_no_groups_no_streams.id}")
    page.goto("/groups")
    page.get_by_role("tab", name="Non-member groups").click()
    filter_for_value(page, public_group.name)
    request_button = page.locator(
        f'//*[@data-testid="requestAdmissionButton{public_group.id}"]'
    ).first
    expect(request_button).to_be_disabled()
    page.locator(
        f'//span[.//*[@data-testid="requestAdmissionButton{public_group.id}"]]'
    ).first.hover()
    expect(page.get_by_role("tooltip")).to_contain_text(public_stream.name)
