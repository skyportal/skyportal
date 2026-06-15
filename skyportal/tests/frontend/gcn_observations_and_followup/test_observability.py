from playwright.sync_api import expect

from skyportal.tests import api


def test_fixed_location_filtering(
    page, view_only_user, hst, public_source, keck1_telescope
):
    page.goto(f"/become_user/{view_only_user.id}")
    page.goto(f"/observability/{public_source.id}")
    page.locator("//*[@id='selectTelescopes']").first.click()
    expect(page.locator(f'//*[text()="{keck1_telescope.name}"]').first).to_be_visible()
    expect(page.locator(f'//*[text()="{hst.name}"]').first).to_be_hidden()


def test_user_preference_filtering(
    page,
    view_only_user,
    super_admin_token,
    public_source,
    keck1_telescope,
    p60_telescope,
):
    # Set the "only show p60" observability preference via the API rather than
    # driving the heavy /profile page (every preference widget lazy-loads and the
    # telescope select races those fetches under CI load). The feature under test
    # is that /observability honors the preference, which the UI below verifies.
    status, _ = api(
        "PATCH",
        f"internal/profile/{view_only_user.id}",
        data={"preferences": {"observabilityTelescopes": [p60_telescope.id]}},
        token=super_admin_token,
    )
    assert status == 200

    page.goto(f"/become_user/{view_only_user.id}")
    page.goto(f"/observability/{public_source.id}")
    expect(page.locator(f'//*[text()="{keck1_telescope.name}"]').first).to_be_hidden()
    expect(page.locator(f'//*[text()="{p60_telescope.name}"]').first).to_be_visible()
