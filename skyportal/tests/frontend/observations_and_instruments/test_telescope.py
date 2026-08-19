import uuid

import pytest
from playwright.sync_api import expect

from skyportal.tests import api


def _add_telescope_via_form(page, name, *, diameter, lat, lon, elevation):
    """Open the New Telescope dialog (in the Table view) and submit the rjsf form."""
    # Switch to the Table view, where the "new telescope" button + form live.
    page.locator('//button[normalize-space(.)="Table"]').first.click(force=True)
    # The Add button can sit under the absolutely-positioned Map/Table toggle
    # overlay, so dispatch the click directly on the element (a coordinate click
    # -- even forced -- would be swallowed by the overlay on top).
    page.locator('//*[@name="new_telescope"]').first.dispatch_event("click")

    dialog = page.locator('//div[@role="dialog"]')
    dialog.locator('//*[@id="root_name"]').first.fill(name)
    dialog.locator('//*[@id="root_nickname"]').first.fill(name)
    dialog.locator('//*[@id="root_diameter"]').first.fill(str(diameter))
    dialog.locator('//*[@id="root_lat"]').first.fill(str(lat))
    dialog.locator('//*[@id="root_lon"]').first.fill(str(lon))
    dialog.locator('//*[@id="root_elevation"]').first.fill(str(elevation))

    # robotic + fixed_location radios -> select "Yes" for both (scoped to dialog
    # so we don't hit the DataGrid's "Yes" chips behind it).
    for row in dialog.locator('//span[text()="Yes"]').all():
        row.click()

    dialog.locator('//button[@type="submit"]').first.click()
    # Wait for the dialog to fully close (its fading backdrop would otherwise
    # swallow the subsequent Map/Table toggle click).
    expect(page.locator('//div[@role="dialog"]')).to_have_count(0)


@pytest.mark.flaky(reruns=2)
def test_telescope_frontend_desktop(super_admin_token, super_admin_user, page):
    telescope_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "telescope",
        data={
            "name": telescope_name,
            "nickname": telescope_name,
            "lat": 1.0,
            "lon": 1.0,
            "elevation": 0.0,
            "diameter": 10.0,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/telescopes")

    # The telescope list renders a "<name>_info" item for every telescope.
    expect(page.locator(f'//*[@id="{telescope_name}_info"]').first).to_be_visible()

    name2 = str(uuid.uuid4())
    _add_telescope_via_form(
        page, name2, diameter=2.0, lat=10.0, lon=10.0, elevation=50.0
    )

    # Back to the Map view; the list should now include the newly added telescope.
    page.locator('//button[normalize-space(.)="Map"]').first.click(force=True)
    expect(page.locator(f'//*[@id="{name2}_info"]').first).to_be_visible()
