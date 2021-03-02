import numpy as np

from baselayer.app.config import load_config
from skyportal.tests import api

cfg = load_config()


def test_periodogram(
    driver, user, public_source, public_group, ztf_camera, upload_data_token
):
    times = np.linspace(58000, 58100, num=200)
    mags = np.sin(times - 58000) + 15.0
    fluxerr = np.ones_like(mags) / 10

    # Put in some actual photometry data first
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': list(times),
            'instrument_id': ztf_camera.id,
            'flux': list(mags),
            'fluxerr': list(fluxerr),
            'filter': 'ztfg',
            'zp': 25.0,
            'magsys': 'ab',
            'ra': 165.0,
            'ra_unc': 0.17,
            'dec': -30.0,
            'dec_unc': 0.2,
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}/periodogram")

    # If the bestp id shows up then a period was found
    best_period = "//span[contains(@data-testid, 'bestp')]"
    driver.wait_for_xpath(best_period)

    # Is the bottom phaseplot rendering?
    phaseplot = "//div[contains(@data-testid, 'phaseplot')]"
    driver.wait_for_xpath(phaseplot)
