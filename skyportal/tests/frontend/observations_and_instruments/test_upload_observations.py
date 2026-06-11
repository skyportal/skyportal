import os

from playwright.sync_api import expect

from skyportal.tests.external.test_moving_objects import (
    add_telescope_and_instrument,
    remove_telescope_and_instrument,
)


def test_upload_observations(page, super_admin_user, super_admin_token):
    telescope_id, instrument_id, _, instrument_name = add_telescope_and_instrument(
        "ZTF", super_admin_token, list(range(5))
    )

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/observations/")

    data_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"
    )

    def upload(filename):
        # The rjsf data-url widget reads the file asynchronously and no longer
        # echoes the filename, so just set it, give the reader a moment, submit.
        page.locator('//input[@type="file"]').first.set_input_files(
            os.path.join(data_dir, filename)
        )
        page.wait_for_timeout(1000)
        page.locator('//button[contains(.,"Submit")]').first.click()
        page.wait_for_timeout(2000)

    page.locator('//*[@name="new_executed_observation"]').first.click()
    page.locator('//li[contains(., "Add from File")]').first.click()
    expect(page.locator('//input[@type="file"]').first).to_be_visible()

    dialog = page.get_by_role("dialog")
    dialog.get_by_role("combobox").first.click()
    page.get_by_role("option", name=instrument_name).first.click()

    # malformed upload (rejected server-side); the dialog stays open afterwards
    upload("sample_observation_data_upload_malformed.csv")
    upload("sample_observation_data_upload.csv")

    # close the upload dialog so the executed-observations table is interactable
    page.keyboard.press("Escape")

    cell = page.locator('//*[text()="84434604"]').first
    for _ in range(5):
        search = page.locator(".MuiDataGrid-root").get_by_placeholder("Search…").first
        search.fill("84434604")
        try:
            expect(cell).to_be_visible(timeout=3000)
            break
        except AssertionError:
            page.wait_for_timeout(2000)
            page.reload()
    expect(cell).to_be_visible(timeout=5000)

    remove_telescope_and_instrument(telescope_id, instrument_id, super_admin_token)
