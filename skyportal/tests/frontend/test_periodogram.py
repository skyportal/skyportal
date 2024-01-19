import uuid

import numpy as np
import numpy.testing as npt

from baselayer.app.config import load_config
from skyportal.tests import api

cfg = load_config()


def test_periodogram(
    driver, user, public_source, public_group, ztf_camera, upload_data_token
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
        'obj_id': obj_id,
        'mjd': list(times),
        'instrument_id': ztf_camera.id,
        'flux': list(flux),
        'fluxerr': list(fluxerr),
        'filter': ['ztfr'] * len(flux),
        'zp': [25.0] * len(flux),
        'magsys': ['ab'] * len(flux),
        'ra': 165.0,
        'ra_unc': 0.17,
        'dec': -30.0,
        'dec_unc': 0.2,
        'group_ids': [public_group.id],
    }
    # Put in some actual photometry data first
    status, data = api(
        'POST',
        'photometry',
        data=data,
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{obj_id}/periodogram")

    # If the bestp id shows up then a period was found
    best_period = "//span[contains(@data-testid, 'bestp')]"
    bestp = driver.wait_for_xpath(best_period)

    # did we find the right period?
    bestp_flt = float(bestp.text)
    npt.assert_almost_equal(bestp_flt, P, decimal=1)

    # Is the bottom phaseplot rendering?
    phaseplot = "//div[contains(@data-testid, 'phaseplot')]"
    driver.wait_for_xpath(phaseplot)
