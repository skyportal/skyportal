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


def test_spectrum_smoothing_does_not_crash(
    page, user, upload_data_token, public_source, lris
):
    # Upload a spectrum with enough points for smoothing to be meaningful.
    n = 60
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": str(public_source.id),
            "observed_at": "2021-11-02 12:00:00",
            "instrument_id": lris.id,
            "wavelengths": [500.0 + i for i in range(n)],
            "fluxes": [100.0 + (i % 7) for i in range(n)],
        },
        token=upload_data_token,
    )
    assert status == 200

    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))

    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")

    # The Spectroscopy accordion is expanded by default; the smoothing control is
    # the number field beneath the "Smoothing" label.
    smoothing_input = page.locator(
        "//*[text()='Smoothing']/following::input[@type='number'][1]"
    ).first
    expect(smoothing_input).to_be_visible()

    # Entering a value drives the string-typed input path that reportedly crashed
    # the spectrum plot.
    smoothing_input.fill("5")
    page.wait_for_timeout(1500)

    # The plot control is still present (an error boundary would have replaced it)
    # and nothing threw.
    expect(smoothing_input).to_be_visible()
    assert not errors, f"Spectrum smoothing raised an error: {errors}"


def test_spectrum_redshift_slider_does_not_crash(
    page, user, upload_data_token, public_source, lris
):
    # Upload a spectrum so the spectrum plot (and its redshift control) renders.
    n = 60
    status, data = api(
        "POST",
        "spectrum",
        data={
            "obj_id": str(public_source.id),
            "observed_at": "2021-11-02 12:00:00",
            "instrument_id": lris.id,
            "wavelengths": [500.0 + i for i in range(n)],
            "fluxes": [100.0 + (i % 7) for i in range(n)],
        },
        token=upload_data_token,
    )
    assert status == 200

    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))

    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{public_source.id}")

    # The Spectroscopy accordion is expanded by default; the redshift control is
    # the number field beneath the "Redshift" label.
    redshift_input = page.locator(
        "//*[text()='Redshift']/following::input[@type='number'][1]"
    ).first
    expect(redshift_input).to_be_visible()

    # Typing into the redshift box feeds its value into the shared Slider state.
    # Before the fix this stored a raw string, and MUI's Slider threw on it.
    redshift_input.fill("0.05")
    page.wait_for_timeout(1500)

    # The plot control is still present (an error boundary would have replaced it)
    # and nothing threw.
    expect(redshift_input).to_be_visible()
    assert not errors, f"Spectrum redshift slider raised an error: {errors}"
