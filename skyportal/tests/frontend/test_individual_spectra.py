import uuid

from playwright.sync_api import expect

from skyportal.tests import api
from skyportal.tests.frontend.sources_and_observingruns_etc.test_sources import (
    add_comment_and_wait_for_display,
)


def test_comments(page, user, public_source):
    page.goto(f"/become_user/{user.id}")

    comment_text = str(uuid.uuid4())

    # now test the Share data page
    page.goto(f"/share_data/{public_source.id}")

    # little triangle you push to expand the table
    page.locator("//*[@id='expandable-button']").first.click()

    add_comment_and_wait_for_display(page, comment_text)

    # Make sure individual spectra comments appear on the Source page
    page.goto(f"/source/{public_source.id}")
    expect(
        page.locator(f'//p[contains(text(), "{comment_text}")]').first
    ).to_be_visible()


def test_annotations(
    page, user, annotation_token, upload_data_token, public_source, lris
):
    page.goto(f"/become_user/{user.id}")
    annotation_data = str(uuid.uuid4())

    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": str(public_source.id),
            "observed_at": "2021-11-02 12:00:00",
            "instrument_id": lris.id,
            "wavelengths": [664, 665, 666],
            "fluxes": [234.2, 232.1, 235.3],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"
    spectrum_id = data["data"]["id"]

    status, data = api(
        "POST",
        f"spectra/{spectrum_id}/annotations",
        data={"origin": "kowalski", "data": {"useful_info": annotation_data}},
        token=annotation_token,
    )
    assert status == 200

    # ----> now test the Share data page <----
    page.goto(f"/share_data/{public_source.id}")

    # filter to only the new spectrum we've added, by typing its id into the
    # data grid's quick-filter search box
    spectrum_filter = page.locator(
        "//*[@data-testid='spectrum-quick-filter']//input"
    ).first
    spectrum_filter.fill(str(spectrum_id))

    # push the little triangle to expand the table
    page.locator(
        "//*[@data-testid='spectrum-div']//*[@id='expandable-button']/.."
    ).first.click()
    expect(page.locator(f'//div[text()="{annotation_data}"]').first).to_be_visible()

    # ----> now go to the source page <----
    page.goto(f"/source/{public_source.id}")
    expect(page.locator('//div[text()="Spectrum Obs. at"]').first).to_be_visible()

    # filter once more for only this spectrum, via the annotations table's
    # quick-filter search box
    annotations_filter = page.locator(
        "//*[@id='annotations-content']"
        "//*[@data-testid='annotations-quick-filter']//input"
    ).first
    annotations_filter.fill("2021-11-02.5")

    expect(page.locator('//div[text()="2021-11-02.5"]').first).to_be_visible()
    expect(page.locator(f'//div[text()="{annotation_data}"]').first).to_be_visible()
