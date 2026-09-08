"""The Solar System tab on a solar system object's photometry plot."""

from playwright.sync_api import expect

from skyportal.models import DBSession


def test_solar_system_tab_does_not_crash_the_page(
    page, super_admin_user, public_source
):
    # The tab is only offered for solar system objects.
    public_source.is_roid = True
    DBSession().commit()

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/source/{public_source.id}")
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()

    page.locator('//button[normalize-space(text())="Solar System"]').first.click()

    # The tab draws its own plot, so the main plot builds no traces for it; a
    # null trace list used to take the page down through the error boundary.
    expect(
        page.locator('//h1[contains(text(), "Something went wrong")]')
    ).to_have_count(0)
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()

    # This source carries no per-point geometry, so the tab explains itself
    # rather than rendering an empty plot.
    expect(page.get_by_text("per-point geometry").first).to_be_visible()
