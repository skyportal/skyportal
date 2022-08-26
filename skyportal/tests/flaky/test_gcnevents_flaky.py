import os
import uuid
import pytest
import time

from skyportal.tests import api


@pytest.mark.flaky(reruns=2)
def test_gcn_IPN(super_admin_token):

    skymap = f'{os.path.dirname(__file__)}/../data/GRB220617A_IPN_map_hpx.fits.gz'
    dateobs = '2022-06-17T18:31:12'
    tags = ['IPN', 'GRB']

    data = {'dateobs': dateobs, 'skymap': skymap, 'tags': tags}

    nretries = 0
    posted = False
    while nretries < 10 and not posted:
        status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
        if status == 200:
            posted = True
        else:
            nretries += 1
            time.sleep(3)

    assert nretries < 10
    assert posted is True
    assert status == 200
    assert data['status'] == 'success'

    dateobs = "2022-06-17 18:31:12"
    status, data = api('GET', f'gcn_event/{dateobs}', token=super_admin_token)
    assert status == 200
    data = data["data"]
    assert data["dateobs"] == "2022-06-17T18:31:12"
    assert 'IPN' in data["tags"]


@pytest.mark.flaky(reruns=2)
def test_gcnevents_object(
    driver, user, super_admin_token, upload_data_token, view_only_token, ztf_camera
):

    datafile = f'{os.path.dirname(__file__)}/../data/GRB180116A_Fermi_GBM_Gnd_Pos.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    # wait for event to load
    time.sleep(15)

    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 229.9620403,
            "dec": 34.8442757,
            "redshift": 3,
        },
        token=upload_data_token,
    )
    assert status == 200

    status, data = api("GET", f"sources/{obj_id}", token=view_only_token)
    assert status == 200

    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': obj_id,
            'mjd': 58134.025611226854 + 1,
            'instrument_id': ztf_camera.id,
            'flux': 12.24,
            'fluxerr': 0.031,
            'zp': 25.0,
            'magsys': 'ab',
            'filter': 'ztfg',
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    status, data = api("GET", f"sources/{obj_id}", token=view_only_token)
    assert status == 200
    catalog_name = str(uuid.uuid4())
    galaxy_name = str(uuid.uuid4())
    data = {
        'catalog_name': catalog_name,
        'catalog_data': {'name': [galaxy_name], 'ra': [228.5], 'dec': [35.5]},
    }
    status, data = api('POST', 'galaxy_catalog', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    # wait for galaxies to load
    nretries = 0
    galaxies_loaded = False
    while not galaxies_loaded and nretries < 5:
        try:
            status, data = api('GET', 'galaxy_catalog', token=view_only_token)
            assert status == 200
            galaxies_loaded = True
        except AssertionError:
            nretries = nretries + 1
            time.sleep(3)

    driver.get(f'/become_user/{user.id}')
    driver.get('/gcn_events/2018-01-16T00:36:53')

    driver.wait_for_xpath('//*[text()="180116 00:36:53"]')
    driver.wait_for_xpath('//*[text()="Fermi"]')
    driver.wait_for_xpath('//*[text()="GRB"]')

    # test modify sources form
    driver.wait_for_xpath('//*[@id="root_queryList"]')
    driver.click_xpath('//*[@id="root_queryList"]')
    driver.wait_for_xpath('//li[contains(text(), "sources")]')
    driver.click_xpath('//li[contains(text(), "sources")]')

    submit_button_xpath = '//button[@type="submit"]'
    driver.wait_for_xpath(submit_button_xpath)
    driver.click_xpath(submit_button_xpath)

    # check for object
    driver.wait_for_xpath(f'//*[text()[contains(.,"{obj_id}")]]', timeout=15)
