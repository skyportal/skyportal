import uuid

import pytest
from playwright.sync_api import expect

from skyportal.tests import api


@pytest.mark.flaky(reruns=3)
def test_instrument_frontend(super_admin_token, super_admin_user, page):
    telescope_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "telescope",
        data={
            "name": telescope_name,
            "nickname": telescope_name,
            "lat": 0.0,
            "lon": 0.0,
            "elevation": 0.0,
            "diameter": 10.0,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    telescope_id = data["data"]["id"]

    instrument_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "instrument",
        data={
            "name": instrument_name,
            "type": "imager",
            "band": "NIR",
            "filters": ["f110w"],
            "telescope_id": telescope_id,
            "api_classname": "ZTFAPI",
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/instruments")

    def _fill_new_instrument_form(name):
        page.locator('//*[@name="new_instrument"]').first.click()
        dialog = page.locator('//div[@role="dialog"]')
        dialog.locator('//*[@id="root_name"]').first.fill(name)
        dialog.locator('//*[@id="root_type"]').first.click()
        page.locator('//li[contains(text(), "Imager")]').first.click()
        dialog.locator('//*[@id="root_band"]').first.fill("Optical")
        dialog.locator('//*[@id="root_telescope_id"]').first.click()
        page.locator(f'//li[contains(text(), "{telescope_name}")]').first.click()
        dialog.locator('//*[@id="root_api_classname"]').first.click()
        page.locator('//li[contains(text(), "ZTFAPI")]').first.click()
        return dialog

    def _search_instrument(name):
        # The instrument grid is server-paginated; filtering by name guarantees
        # the row is present regardless of which page it would otherwise land on.
        # Scope to the DataGrid so we don't grab the global nav search bar. Note:
        # ``fill`` replaces the field's contents, so we must NOT clear it first --
        # an extra empty fill kicks off a slow unfiltered fetch that can resolve
        # after the name fetch and clobber the grid.
        search = page.locator(".MuiDataGrid-root").get_by_placeholder("Search").first
        search.fill(name)

    # The API-posted instrument shows up once we filter to it.
    _search_instrument(instrument_name)
    expect(
        page.locator(f'//*[contains(text(),"{instrument_name}")]').first
    ).to_be_visible()

    instrument_name2 = str(uuid.uuid4())
    dialog = _fill_new_instrument_form(instrument_name2)
    dialog.locator('//button[@type="submit"]').first.click()
    expect(page.locator('//div[@role="dialog"]')).to_have_count(0)

    _search_instrument(instrument_name2)
    expect(
        page.locator(f'//*[contains(text(),"{instrument_name2}")]').first
    ).to_be_visible()

    # try adding the same name a second time -> duplicate-name validation error
    dialog = _fill_new_instrument_form(instrument_name2)
    dialog.locator('//button[@type="submit"]').first.click()
    expect(
        page.locator('//*[contains(text(), "Instrument name matches another")]').first
    ).to_be_visible()
