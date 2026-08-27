"""The Outburst tab on a solar system object's photometry plot.

The tab draws its own plot, so the main plot has no traces to build for it.
That used to take down the whole source page with "Cannot read properties of
null (reading 'push')", because the trace builder returned null for a tab it
did not recognise and the caller pushed onto it.
"""

from playwright.sync_api import expect

from skyportal.models import DBSession


def test_outburst_tab_does_not_crash_the_page(page, super_admin_user, public_source):
    # The tab is only offered for solar system objects.
    public_source.is_roid = True
    DBSession().commit()

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/source/{public_source.id}")
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()

    page.locator('//button[normalize-space(text())="Outburst"]').first.click()

    # The error boundary replaces the page wholesale, so its heading is the
    # clearest signal that the click broke something.
    expect(
        page.locator('//h1[contains(text(), "Something went wrong")]')
    ).to_have_count(0)
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()
