import uuid

import pytest
import numpy as np
import numpy.testing as npt
import requests
from requests.exceptions import HTTPError, Timeout, ConnectionError, MissingSchema

from skyportal.tests import api
from skyportal.utils.offset import (
    get_nearby_offset_stars,
    get_finding_chart,
    get_ztfref_url,
    _calculate_best_position_for_offset_stars,
)
from skyportal.models import Photometry


def test_calculate_best_position_no_photometry():
    ra, dec = _calculate_best_position_for_offset_stars(
        [], fallback=(10.0, -20.0), how="snr2", max_offset=0.5, sigma_clip=4.0
    )
    npt.assert_almost_equal(ra, 10)
    npt.assert_almost_equal(dec, -20)


@pytest.mark.flaky(reruns=2)
def test_calculate_position_with_evil_inputs(
    upload_data_token, view_only_token, ztf_camera, public_group
):
    ra, dec = 10.5, -20.8
    obj_id = str(uuid.uuid4())
    status, data = api(
        'POST',
        'sources',
        data={'id': obj_id, 'ra': ra, 'dec': dec, 'group_ids': [public_group.id]},
        token=upload_data_token,
    )
    assert status == 200
    assert data['data']['id'] == obj_id

    n_phot = 10
    mjd = 58000.0 + np.arange(n_phot)
    flux = np.zeros_like(mjd)
    fluxerr = 1e-6 + np.random.random(n_phot)
    filters = ['ztfg'] * n_phot
    ras = ra + np.cos(np.radians(dec)) * np.random.randn(n_phot) / (10 * 3600)
    decs = dec + np.random.randn(n_phot) / (10 * 3600)
    dec_unc = np.zeros_like(mjd)

    med_ra, med_dec = np.median(ras), np.median(decs)

    # valid request with zero-flux sources and astrometry with zero uncertainty
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': obj_id,
            'mjd': list(mjd),
            'instrument_id': ztf_camera.id,
            'flux': list(flux),
            'fluxerr': list(fluxerr),
            'filter': list(filters),
            'ra': list(ras),
            'dec': list(decs),
            'magsys': 'ab',
            'zp': 25.0,
            'dec_unc': list(dec_unc),
            'ra_unc': 0.2,
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    assert len(data['data']['ids']) == n_phot

    removed_kwargs = ["instrument_name", "groups", "magsys", "zp", "snr"]
    phot_list = []
    for photometry_id in data['data']['ids']:
        status, data = api(
            'GET', f'photometry/{photometry_id}?format=flux', token=upload_data_token
        )
        assert status == 200
        assert data['status'] == 'success'
        for key in removed_kwargs:
            data['data'].pop(key)

        phot_list.append(Photometry(**data['data']))

    ra_calc_snr, dec_calc_snr = _calculate_best_position_for_offset_stars(
        phot_list, fallback=(ra, dec), how="snr2", max_offset=0.5, sigma_clip=4.0
    )
    # make sure we get back a the median position
    npt.assert_almost_equal(ra_calc_snr, med_ra, decimal=10)
    npt.assert_almost_equal(dec_calc_snr, med_dec, decimal=10)

    ra_calc_err, dec_calc_err = _calculate_best_position_for_offset_stars(
        phot_list, fallback=(ra, dec), how="invvar", max_offset=0.5, sigma_clip=4.0
    )
    # make sure we get back a median position
    npt.assert_almost_equal(ra_calc_err, med_ra, decimal=10)
    npt.assert_almost_equal(dec_calc_err, med_dec, decimal=10)


@pytest.mark.flaky(reruns=2)
def test_calculate_best_position_with_photometry(
    upload_data_token, view_only_token, ztf_camera, public_group
):
    ra, dec = 10.5, -20.8
    obj_id = str(uuid.uuid4())
    status, data = api(
        'POST',
        'sources',
        data={'id': obj_id, 'ra': ra, 'dec': dec, 'group_ids': [public_group.id]},
        token=upload_data_token,
    )
    assert status == 200
    assert data['data']['id'] == obj_id

    n_phot = 10
    mjd = 58000.0 + np.arange(n_phot)
    flux = float(n_phot) + np.random.random(n_phot) * 100
    fluxerr = 1e-6 + np.random.random(n_phot)
    filters = ['ztfg'] * n_phot
    ras = ra + np.cos(np.radians(dec)) * np.random.randn(n_phot) / (10 * 3600)
    decs = dec + np.random.randn(n_phot) / (10 * 3600)

    # valid request
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': obj_id,
            'mjd': list(mjd),
            'instrument_id': ztf_camera.id,
            'flux': list(flux),
            'fluxerr': list(fluxerr),
            'filter': list(filters),
            'ra': list(ras),
            'dec': list(decs),
            'magsys': 'ab',
            'zp': 25.0,
            'dec_unc': 0.2,
            'ra_unc': 0.2,
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    assert len(data['data']['ids']) == n_phot

    removed_kwargs = ["instrument_name", "groups", "magsys", "zp", "snr"]
    phot_list = []
    for photometry_id in data['data']['ids']:
        status, data = api(
            'GET', f'photometry/{photometry_id}?format=flux', token=upload_data_token
        )
        assert status == 200
        assert data['status'] == 'success'
        for key in removed_kwargs:
            data['data'].pop(key)

        phot_list.append(Photometry(**data['data']))

    ra_calc_snr, dec_calc_snr = _calculate_best_position_for_offset_stars(
        phot_list, fallback=(ra, dec), how="snr2", max_offset=0.5, sigma_clip=4.0
    )
    # make sure we get back a slightly different position than the true center
    with pytest.raises(AssertionError):
        npt.assert_almost_equal(ra_calc_snr, ra, decimal=10)
    with pytest.raises(AssertionError):
        npt.assert_almost_equal(dec_calc_snr, dec, decimal=10)

    ra_calc_err, dec_calc_err = _calculate_best_position_for_offset_stars(
        phot_list, fallback=(ra, dec), how="invvar", max_offset=0.5, sigma_clip=4.0
    )
    # make sure we get back a slightly different position for two different
    # methods
    with pytest.raises(AssertionError):
        npt.assert_almost_equal(ra_calc_snr, ra_calc_err, decimal=10)

    with pytest.raises(AssertionError):
        npt.assert_almost_equal(dec_calc_snr, dec_calc_err, decimal=10)


# use a bona fide URL to test to see if the ZTF search facility is working
ztfref_url = get_ztfref_url(123.0, 33.3, 2)
# if it's a valid URL, then we can assume that the ZTF search facility is working
run_ztfref_test = True
try:
    if ztfref_url != "":
        r = requests.get(ztfref_url)
        r.raise_for_status()
    else:
        run_ztfref_test = False
except (HTTPError, TimeoutError, ConnectionError, MissingSchema) as e:
    run_ztfref_test = False
    print(e)


@pytest.mark.skipif(not run_ztfref_test, reason='IRSA server down')
def test_get_ztfref_url():
    url = get_ztfref_url(123.0, 33.3, 2)

    assert isinstance(url, str)
    assert url.find("irsa") != -1


def test_get_nearby_offset_stars():
    how_many = 3
    rez = get_nearby_offset_stars(
        123.0, 33.3, "testSource", how_many=how_many, radius_degrees=3 / 60.0
    )
    # expecting 5 parameters:
    #   a list of the source+offset stars,
    #   What query was used against Gaia,
    #   number of queries_issued,
    #   number of offset stars
    #   whether ZRF ref was used for astrometry
    assert len(rez) == 5
    assert isinstance(rez[0], list)
    assert len(rez[0]) == how_many + 1

    with pytest.raises(Exception):
        rez = get_nearby_offset_stars(
            123.0,
            33.3,
            "testSource",
            how_many=how_many,
            radius_degrees=3 / 60.0,
            allowed_queries=1,
            queries_issued=2,
        )


desi_url = (
    "http://legacysurvey.org/viewer/fits-cutout/"
    "?ra=123.0&dec=33.0&layer=dr8&pixscale=2.0&bands=r"
)

# check to see if the DESI server is up. If not, do not run test.
run_desi_test = True
try:
    r = requests.get(desi_url)
    r.raise_for_status()
except (HTTPError, Timeout, ConnectionError) as e:
    run_desi_test = False
    print(e)


@pytest.mark.skipif(not run_desi_test, reason="DESI server down")
def test_get_desi_finding_chart():
    rez = get_finding_chart(
        123.0, 33.3, "testSource", image_source='desi', output_format='pdf'
    )

    assert isinstance(rez, dict)
    assert rez["success"]
    assert rez["name"].find("testSource") != -1
    assert rez["data"].find(bytes("PDF", encoding='utf8')) != -1


# test for failure on a too-small image size
def test_get_finding_chart():
    rez = get_finding_chart(123.0, 33.3, "testSource", imsize=1.0, image_source='dss')
    assert not rez["success"]

    rez = get_finding_chart(123.0, 33.3, "testSource", image_source='zomg_telescope')
    assert isinstance(rez, dict)
    assert not rez["success"]
