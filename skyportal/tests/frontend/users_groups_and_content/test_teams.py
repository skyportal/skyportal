import uuid

from playwright.sync_api import expect

from skyportal.tests import api


def test_teams_page_and_switcher(
    page, super_admin_user, public_group, super_admin_token
):
    # Create a team via the API, then confirm it renders on the management page
    # and that the header team switcher appears.
    team_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "teams",
        data={
            "name": team_name,
            "primary_color": "#123456",
            "group_ids": [public_group.id],
        },
        token=super_admin_token,
    )
    assert status == 200

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/teams")
    expect(page.locator('//h5[text()="Create New Team"]').first).to_be_visible()
    expect(page.locator(f'//*[contains(text(),"{team_name}")]').first).to_be_visible()

    # The header switcher shows once the user has at least one team.
    page.goto("/")
    expect(page.locator('[data-testid="teamSwitcher"]').first).to_be_visible()
