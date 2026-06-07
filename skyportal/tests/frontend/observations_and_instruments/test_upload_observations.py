import os

import pytest
from playwright.sync_api import expect

from skyportal.tests.external.test_moving_objects import (
    add_telescope_and_instrument,
    remove_telescope_and_instrument,
)


@pytest.mark.flaky(reruns=3)
def test_upload_observations(page, super_admin_user, super_admin_token):
    telescope_id, instrument_id, _, _ = add_telescope_and_instrument(
        "ZTF", super_admin_token, list(range(5))
    )

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/observations/")

    data_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"
    )

    def open_add_from_file():
        # Uploading is now behind an Add button -> "Add from File" menu item,
        # which opens the dialog containing the file-upload form.
        page.locator('//*[@name="new_executed_observation"]').first.click()
        page.locator('//li[contains(., "Add from File")]').first.click()
        expect(page.locator('//input[@type="file"]').first).to_be_visible()

    def upload(filename):
        # The rjsf data-url widget reads the file asynchronously and no longer
        # echoes the filename, so just set it, give the reader a moment, submit.
        page.locator('//input[@type="file"]').first.set_input_files(
            os.path.join(data_dir, filename)
        )
        page.wait_for_timeout(1000)
        page.locator('//button[contains(.,"Submit")]').first.click()
        page.wait_for_timeout(2000)

    open_add_from_file()
    # malformed upload (rejected server-side); the dialog stays open afterwards
    upload("sample_observation_data_upload_malformed.csv")
    upload("sample_observation_data_upload.csv")

    # close the upload dialog so the executed-observations table is interactable
    page.keyboard.press("Escape")

    # The page's default query is a 10-year scan that times out under CI load.
    # Scope it to a tight window around the uploaded obs (2022-01-19) via the
    # filter dialog, re-applying each iteration since the upload + ingest can lag.
    search = page.locator(".MuiDataGrid-root").get_by_placeholder("Search…").first
    cell = page.locator('//*[text()="84434604"]').first
    for _ in range(15):
        page.locator("//button[@data-testid='Filter Table-iconButton']").first.click()
        page.locator('//input[@name="startDate"]').first.fill("2022-01-18T00:00:00")
        page.locator('//input[@name="endDate"]').first.fill("2022-01-21T00:00:00")
        page.locator("//button[text()='Submit']").first.click()
        page.wait_for_timeout(800)
        page.keyboard.press("Escape")  # close the filter dialog to reach the grid
        search.fill("84434604")
        try:
            expect(cell).to_be_visible(timeout=3000)
            break
        except AssertionError:
            page.wait_for_timeout(2000)
    expect(cell).to_be_visible(timeout=5000)

    remove_telescope_and_instrument(telescope_id, instrument_id, super_admin_token)
