import os
import uuid

import pytest
from playwright.sync_api import expect

from skyportal.enum_types import ALLOWED_SPECTRUM_TYPES


@pytest.mark.flaky(reruns=3)
def test_upload_spectroscopy(
    page, sedm, super_admin_user, public_source, super_admin_token
):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/upload_spectrum/{public_source.id}")

    filename = "ZTF20abucjsa_20200909_LT_v1.ascii"

    page.locator('//input[@type="file"]').first.set_input_files(
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data",
            filename,
        )
    )

    # some browsers may render the filename as markdown, in which case the _
    # around the date will cause it to be italicized. So we check each part.
    expect(page.locator('//*[contains(., "ZTF20abucjsa")]').first).to_be_visible()
    expect(page.locator('//*[contains(., "20200909")]').first).to_be_visible()
    expect(page.locator('//*[contains(., "LT")]').first).to_be_visible()

    page.locator('//*[@id="root_mjd"]').first.fill("51232.0")

    # instrument select (the option click closes the dropdown)
    page.locator('//*[@id="root_instrument_id"]').first.click()
    page.locator(f'//li[contains(text(), "{sedm.name}")]').first.click()

    # spectrum type select
    page.locator('//*[@id="root_spectrum_type"]').first.click()
    page.locator(
        f'//li[contains(text(), "{ALLOWED_SPECTRUM_TYPES[-1]}")]'
    ).first.click()

    user_defined_label = str(uuid.uuid4())
    page.locator('//*[@id="root_user_label"]').first.fill(user_defined_label)

    page.locator('//button[contains(.,"Preview")]').first.click()
    page.locator('//button[contains(.,"Upload Spectrum")]').first.click()

    expect(page.locator('//*[contains(.,"successful")]').first).to_be_visible()

    # Go to "Share data" page to look for the spectrum, since we can't easily
    #  look into the plot on the Source page.
    page.goto(f"/share_data/{public_source.id}")

    expect(page.locator(f'//*[contains(.,"{sedm.name}")]').first).to_be_visible(
        timeout=20000
    )
    expect(
        page.locator(f'//*[contains(.,"{ALLOWED_SPECTRUM_TYPES[-1]}")]').first
    ).to_be_visible(timeout=20000)
    expect(
        page.locator(f'//*[contains(.,"{user_defined_label}")]').first
    ).to_be_visible(timeout=20000)
