import uuid

import numpy as np
import numpy.testing as npt
from playwright.sync_api import expect

from baselayer.app.config import load_config
from skyportal.tests import api

cfg = load_config()


def test_periodogram(
    page, user, public_source, public_group, ztf_camera, upload_data_token
):
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 10.22,
            "dec": -22.33,
            "redshift": 1,
            "transient": False,
            "ra_dis": 2.3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id

    P = 2.10
    times = np.random.uniform(57000, 57020, size=(100,))
    noise = 0.1 * np.random.normal(size=times.shape)
    flux = 15.0 + 1.5 * np.sin((2 * np.pi / P) * (times - 57000)) + noise
    fluxerr = 0.1 + 0.02 * np.random.normal(size=times.shape)

    data = {
        "obj_id": obj_id,
        "mjd": list(times),
        "instrument_id": ztf_camera.id,
        "flux": list(flux),
        "fluxerr": list(fluxerr),
        "filter": ["ztfr"] * len(flux),
        "zp": [25.0] * len(flux),
        "magsys": ["ab"] * len(flux),
        "ra": 165.0,
        "ra_unc": 0.17,
        "dec": -30.0,
        "dec_unc": 0.2,
        "group_ids": [public_group.id],
    }
    # Put in some actual photometry data first
    status, data = api("POST", "photometry", data=data, token=upload_data_token)
    assert status == 200
    assert data["status"] == "success"

    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{obj_id}/periodogram")

    # If the bestp id shows up then a period was found
    bestp = page.locator("//span[contains(@data-testid, 'bestp')]").first
    expect(bestp).to_be_visible()

    # did we find the right period?
    bestp_flt = float(bestp.inner_text())
    npt.assert_almost_equal(bestp_flt, P, decimal=1)

    # Is the bottom phaseplot rendering?
    expect(
        page.locator("//div[contains(@data-testid, 'phaseplot')]").first
    ).to_be_visible()


def test_periodogram_filter_select(
    page, user, public_group, ztf_camera, upload_data_token
):
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={"id": obj_id, "ra": 10.22, "dec": -22.33, "group_ids": [public_group.id]},
        token=upload_data_token,
    )
    assert status == 200

    times = np.random.uniform(57000, 57020, size=(100,))
    flux = 15.0 + 1.5 * np.sin((2 * np.pi / 2.10) * (times - 57000))
    data = {
        "obj_id": obj_id,
        "mjd": list(times),
        "instrument_id": ztf_camera.id,
        "flux": list(flux),
        "fluxerr": [0.1] * len(flux),
        "filter": ["ztfg"] * 50 + ["ztfr"] * 50,
        "zp": [25.0] * len(flux),
        "magsys": ["ab"] * len(flux),
        "ra": 165.0,
        "ra_unc": 0.17,
        "dec": -30.0,
        "dec_unc": 0.2,
        "group_ids": [public_group.id],
    }
    status, data = api("POST", "photometry", data=data, token=upload_data_token)
    assert status == 200

    page.goto(f"/become_user/{user.id}")
    page.goto(f"/source/{obj_id}/periodogram")
    expect(page.locator("//span[@data-testid='bestp']").first).to_be_visible()

    # One filter is preselected, so switching to the other must replot with it
    phaseplot = page.locator("//div[@data-testid='phaseplot']").first
    for filt in ["ztfg", "ztfr"]:
        page.locator(
            '//*[@role="combobox"][contains(@aria-labelledby, "FilterSourceSelect")]'
        ).first.click()
        page.locator(f'//li[@data-value="{filt}"]').first.click()
        page.locator('//button[contains(., "Recalculate")]').first.click()
        expect(phaseplot).to_contain_text(f": {filt})")
