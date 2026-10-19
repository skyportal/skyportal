import os
import uuid

import pytest
from playwright.sync_api import expect


@pytest.mark.flaky(reruns=2)
def test_upload_galaxies(page, super_admin_user, super_admin_token):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/galaxies/")

    filename = "CLU_mini.csv"
    catalog_name = str(uuid.uuid4())

    page.get_by_label("Add a New Galaxy Catalog").click()

    page.locator('//*[@id="root_catalogName"]').first.fill(catalog_name)
    page.locator('//input[@type="file"]').first.set_input_files(
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data",
            filename,
        )
    )

    expect(page.locator(f'//*[contains(., "{filename}")]').first).to_be_visible()
    page.locator('//button[contains(.,"Submit")]').first.click()

    # The data grid quick filter searches galaxy names server-side.
    search_bar = page.locator('//*[@data-testid="galaxy-search-input"]//input').first
    search_bar.fill("6dFgs gJ0001313-055904")
    expect(page.locator('//*[text()="6dFgs gJ0001313-055904"]').first).to_be_visible()
    search_bar.fill("")
