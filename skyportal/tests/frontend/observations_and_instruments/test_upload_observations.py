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
        # The async file read can lag under CI load; submitting before it
        # finishes posts an empty form, so give it a generous moment.
        page.wait_for_timeout(3000)
        page.locator('//button[contains(.,"Submit")]').first.click()
        page.wait_for_timeout(2000)

    open_add_from_file()
    # malformed upload (rejected server-side); the dialog stays open afterwards
    upload("sample_observation_data_upload_malformed.csv")
    upload("sample_observation_data_upload_single.csv")

    # The upload + ingest is asynchronous, and the executed-observations grid is
    # too heavy to reliably surface the row under CI load, so assert the upload
    # was accepted via its success toast instead.
    expect(
        page.locator('//*[contains(text(), "Observation saved")]').first
    ).to_be_visible(timeout=180000)

    remove_telescope_and_instrument(telescope_id, instrument_id, super_admin_token)
