import uuid

from skyportal.tests import api
from skyportal.tests.frontend.sources_and_observingruns_etc.test_sources import (
    add_comment_and_wait_for_display,
)


def test_comments(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")

    comment_text = str(uuid.uuid4())

    # now test the Share data page
    driver.get(f"/share_data/{public_source.id}")

    # little triangle you push to expand the table
    driver.click_xpath("//*[@id='expandable-button']")

    add_comment_and_wait_for_display(driver, comment_text)

    # Make sure individual spectra comments appear on the Source page
    driver.get(f"/source/{public_source.id}")

    driver.wait_for_xpath(f'//p[contains(text(), "{comment_text}")]')


def test_annotations(
    driver, user, annotation_token, upload_data_token, public_source, lris
):
    driver.get(f"/become_user/{user.id}")
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
        data={
            "origin": "kowalski",
            "data": {"useful_info": annotation_data},
        },
        token=annotation_token,
    )

    assert status == 200

    # ----> now test the Share data page <----
    driver.get(f"/share_data/{public_source.id}")

    # filter to only the new spectrum we've added, by typing its id into the
    # data grid's quick-filter search box (the id column is shown in the table)
    spectrum_filter = driver.wait_for_xpath(
        "//*[@data-testid='spectrum-quick-filter']//input"
    )
    # wait_for_xpath only checks DOM presence; the input may be below the fold,
    # so scroll it into view before interacting or .clear() raises
    # "element not interactable".
    driver.scroll_to_element(spectrum_filter)
    spectrum_filter.clear()
    spectrum_filter.send_keys(str(spectrum_id))

    # push the little triangle to expand the table
    driver.click_xpath(
        "//*[@data-testid='spectrum-div']//*[@id='expandable-button']/.."
    )
    driver.wait_for_xpath(f'//div[text()="{annotation_data}"]')

    # ----> now go to the source page <----
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath('//div[text()="Spectrum Obs. at"]')

    # filter once more for only this spectrum, via the annotations table's
    # quick-filter search box (the "Spectrum Obs. at" column shows 2021-11-02.5)
    annotations_filter = driver.wait_for_xpath(
        "//*[@id='annotations-content']"
        "//*[@data-testid='annotations-quick-filter']//input"
    )
    driver.scroll_to_element(annotations_filter)
    annotations_filter.clear()
    annotations_filter.send_keys("2021-11-02.5")

    driver.wait_for_xpath('//div[text()="2021-11-02.5"]')
    driver.wait_for_xpath(f'//div[text()="{annotation_data}"]')
