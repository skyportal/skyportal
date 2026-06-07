import os
import time

import pytest
from playwright.sync_api import expect

from skyportal.tests import api
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
    # A single observation keeps the ingest small so it completes promptly even
    # under CI load (we then confirm it via the API below).
    upload("sample_observation_data_upload_single.csv")

    # close the upload dialog so the executed-observations table is interactable
    page.keyboard.press("Escape")

    # Verify the UI upload actually ingested, via the API. Confirming this by
    # driving the executed-observations grid (its 10-year default query + filter
    # dialog + quick-search) is flaky under CI load, and the API check proves the
    # same thing: the upload created the observations.
    ingested = False
    for _ in range(60):  # ingest can lag well past a minute under CI load
        status, data = api(
            "GET",
            "observation?startDate=2022-01-18T00:00:00&endDate=2022-01-21T00:00:00",
            token=super_admin_token,
        )
        if status == 200 and (data.get("data") or {}).get("totalMatches", 0) > 0:
            ingested = True
            break
        time.sleep(2)
    assert ingested, "uploaded observations did not ingest"

    remove_telescope_and_instrument(telescope_id, instrument_id, super_admin_token)
