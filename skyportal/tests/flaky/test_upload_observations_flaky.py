import os

import pytest
from playwright.sync_api import expect

from skyportal.tests.external.test_moving_objects import (
    add_telescope_and_instrument,
    remove_telescope_and_instrument,
)


@pytest.mark.flaky(reruns=2)
def test_upload_observations(page, super_admin_user, super_admin_token):
    telescope_id, instrument_id, _, _ = add_telescope_and_instrument(
        "ZTF", super_admin_token, list(range(5))
    )

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/observations/")

    filename = "sample_observation_data_upload_malformed.csv"

    page.locator('//input[@type="file"]').first.set_input_files(
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data",
            filename,
        )
    )

    expect(page.locator(f'//*[contains(., "{filename}")]').first).to_be_visible()
    submit_button_xpath = '//button[contains(.,"Submit")]'
    page.locator(submit_button_xpath).first.click()

    filename = "sample_observation_data_upload.csv"

    page.locator('//input[@type="file"]').first.set_input_files(
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data",
            filename,
        )
    )

    expect(page.locator(f'//*[contains(., "{filename}")]').first).to_be_visible()
    submit_button_xpath = '//button[contains(.,"Submit")]'
    page.locator(submit_button_xpath).first.click()

    search_button_xpath = '//button[@data-testid="Search-iconButton"]'
    page.locator(search_button_xpath).first.click()
    search_bar = page.locator('//input[@aria-label="Search"]').first
    search_bar.fill("84434604")
    expect(page.locator('//*[text()="84434604"]').first).to_be_visible()

    remove_telescope_and_instrument(telescope_id, instrument_id, super_admin_token)
