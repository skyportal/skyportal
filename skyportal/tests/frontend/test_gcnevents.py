import os
import uuid
import pytest
import pandas as pd
import time
from regions import Regions
from selenium.webdriver.common.keys import Keys

from skyportal.tests import api


@pytest.mark.flaky(reruns=5)
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

    galaxy_name = str(uuid.uuid4())
    data = {
        'catalog_name': 'galaxy_in_Fermi',
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
    driver.wait_for_xpath('//*[@id="root_startDate"]').send_keys('01/15/2018')
    driver.wait_for_xpath('//*[@id="root_startDate"]').send_keys(Keys.TAB)
    driver.wait_for_xpath('//*[@id="root_startDate"]').send_keys('01:01')
    driver.wait_for_xpath('//*[@id="root_startDate"]').send_keys('P')
    driver.wait_for_xpath('//*[@id="root_endDate"]').send_keys('01/18/2018')
    driver.wait_for_xpath('//*[@id="root_endDate"]').send_keys(Keys.TAB)
    driver.wait_for_xpath('//*[@id="root_endDate"]').send_keys('01:01')
    driver.wait_for_xpath('//*[@id="root_endDate"]').send_keys('P')
    driver.wait_for_xpath('//*[@id="root_localizationName"]')
    driver.click_xpath('//*[@id="root_localizationName"]')
    driver.wait_for_xpath('//li[contains(text(), "214.74000_28.14000_11.19000")]')
    driver.click_xpath('//li[contains(text(), "214.74000_28.14000_11.19000")]')

    submit_button_xpath = '//button[@type="submit"]'
    driver.wait_for_xpath(submit_button_xpath)
    driver.click_xpath(submit_button_xpath)

    # check for object
    driver.wait_for_xpath(f'//*[text()[contains(.,"{obj_id}")]]')


@pytest.mark.flaky(reruns=5)
def test_gcnevents_observations(
    driver, user, super_admin_token, upload_data_token, view_only_token, ztf_camera
):

    datafile = f'{os.path.dirname(__file__)}/../data/GW190425_initial.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    telescope_name = str(uuid.uuid4())
    status, data = api(
        'POST',
        'telescope',
        data={
            'name': telescope_name,
            'nickname': telescope_name,
            'lat': 0.0,
            'lon': 0.0,
            'elevation': 0.0,
            'diameter': 10.0,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    telescope_id = data['data']['id']

    fielddatafile = f'{os.path.dirname(__file__)}/../../../data/ZTF_Fields.csv'
    regionsdatafile = f'{os.path.dirname(__file__)}/../../../data/ZTF_Region.reg'

    instrument_name = str(uuid.uuid4())
    status, data = api(
        'POST',
        'instrument',
        data={
            'name': instrument_name,
            'type': 'imager',
            'band': 'Optical',
            'filters': ['ztfr'],
            'telescope_id': telescope_id,
            'field_data': pd.read_csv(fielddatafile)[:5].to_dict(orient='list'),
            'field_region': Regions.read(regionsdatafile).serialize(format='ds9'),
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    # wait for the fields to populate
    time.sleep(15)

    datafile = f'{os.path.dirname(__file__)}/../../../data/sample_observation_data.csv'
    data = {
        'telescopeName': telescope_name,
        'instrumentName': instrument_name,
        'observationData': pd.read_csv(datafile).to_dict(orient='list'),
    }

    status, data = api('POST', 'observation', data=data, token=super_admin_token)

    assert status == 200
    assert data['status'] == 'success'

    # wait for the executed observations to populate
    time.sleep(15)

    driver.get(f'/become_user/{user.id}')
    driver.get('/gcn_events/2019-04-25T08:18:05')

    driver.wait_for_xpath('//*[text()="190425 08:18:05"]')
    driver.wait_for_xpath('//*[text()="LVC"]')
    driver.wait_for_xpath('//*[text()="BNS"]')

    # test modify sources form
    driver.wait_for_xpath('//*[@id="root_startDate"]').send_keys('04/24/2019')
    driver.wait_for_xpath('//*[@id="root_startDate"]').send_keys(Keys.TAB)
    driver.wait_for_xpath('//*[@id="root_startDate"]').send_keys('01:01')
    driver.wait_for_xpath('//*[@id="root_startDate"]').send_keys('P')
    driver.wait_for_xpath('//*[@id="root_endDate"]').send_keys('04/30/2019')
    driver.wait_for_xpath('//*[@id="root_endDate"]').send_keys(Keys.TAB)
    driver.wait_for_xpath('//*[@id="root_endDate"]').send_keys('01:01')
    driver.wait_for_xpath('//*[@id="root_endDate"]').send_keys('P')
    driver.wait_for_xpath('//*[@id="root_localizationCumprob"]').clear()
    driver.wait_for_xpath('//*[@id="root_localizationCumprob"]').send_keys('1.01')
    driver.wait_for_xpath('//*[@id="root_localizationName"]')
    driver.click_xpath('//*[@id="root_localizationName"]')
    driver.wait_for_xpath('//li[contains(text(), "bayestar.fits.gz")]')
    driver.click_xpath('//li[contains(text(), "bayestar.fits.gz")]')

    submit_button_xpath = (
        '//div[@data-testid="gcnsource-selection-form"]//button[@type="submit"]'
    )
    driver.wait_for_xpath(submit_button_xpath)
    driver.click_xpath(submit_button_xpath)

    # check that the executed observation table appears
    driver.wait_for_xpath('//*[text()="84434604"]')
    driver.wait_for_xpath('//*[text()="ztfr"]')
    driver.wait_for_xpath('//*[text()="1.57415"]')
    driver.wait_for_xpath('//*[text()="20.40705"]')


@pytest.mark.flaky(reruns=5)
def test_observationplan_request(driver, user, super_admin_token, public_group):

    datafile = f'{os.path.dirname(__file__)}/../data/GW190425_initial.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    telescope_name = str(uuid.uuid4())
    status, data = api(
        'POST',
        'telescope',
        data={
            'name': telescope_name,
            'nickname': telescope_name,
            'lat': 0.0,
            'lon': 0.0,
            'elevation': 0.0,
            'diameter': 10.0,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    telescope_id = data['data']['id']

    fielddatafile = f'{os.path.dirname(__file__)}/../../../data/ZTF_Fields.csv'
    regionsdatafile = f'{os.path.dirname(__file__)}/../../../data/ZTF_Region.reg'

    instrument_name = str(uuid.uuid4())
    status, data = api(
        'POST',
        'instrument',
        data={
            'name': instrument_name,
            'type': 'imager',
            'band': 'NIR',
            'filters': ['f110w'],
            'telescope_id': telescope_id,
            "api_classname_obsplan": "ZTFMMAAPI",
            'field_data': pd.read_csv(fielddatafile)[:5].to_dict(orient='list'),
            'field_region': Regions.read(regionsdatafile).serialize(format='ds9'),
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    instrument_id = data['data']['id']

    # wait for the fields to populate
    time.sleep(15)

    print(super_admin_token)
    status, data = api(
        "POST",
        "allocation",
        data={
            "group_id": public_group.id,
            "instrument_id": instrument_id,
            "hours_allocated": 100,
            "pi": "Ed Hubble",
            '_altdata': '{"access_token": "testtoken"}',
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    driver.get(f'/become_user/{user.id}')
    driver.get('/gcn_events/2019-04-25T08:18:05')

    driver.wait_for_xpath('//*[text()="190425 08:18:05"]')
    driver.wait_for_xpath('//*[text()="LVC"]')
    driver.wait_for_xpath('//*[text()="BNS"]')

    submit_button_xpath = (
        '//div[@data-testid="observationplan-request-form"]//button[@type="submit"]'
    )
    driver.wait_for_xpath(submit_button_xpath)

    select_box = driver.find_element_by_id(
        "mui-component-select-followupRequestAllocationSelect"
    )
    select_box.click()

    driver.click_xpath(
        f'//li[contains(text(), "{instrument_name}")][contains(text(), "{public_group.name}")]',
        scroll_parent=True,
    )

    # Click somewhere outside to remove focus from instrument select
    driver.click_xpath("//header")

    driver.click_xpath(submit_button_xpath)

    # wait for the observation plan to complete
    time.sleep(15)

    driver.click_xpath(f"//div[@data-testid='{instrument_name}-requests-header']")
    driver.wait_for_xpath(
        f'//div[contains(@data-testid, "{instrument_name}_observationplanRequestsTable")]//div[contains(., "g,r,i")]',
        timeout=15,
    )
    driver.wait_for_xpath(
        f'''//div[contains(@data-testid, "{instrument_name}_observationplanRequestsTable")]//div[contains(., "complete")]''',
        timeout=15,
    )

    status, data = api("GET", "observation_plan", token=super_admin_token)
    assert status == 200

    observation_plan_request_id = data['data'][-1]['observation_plans'][0][
        'observation_plan_request_id'
    ]

    driver.click_xpath(
        f'//button[contains(@data-testid, "sendRequest_{observation_plan_request_id}")]',
        scroll_parent=True,
    )
    driver.wait_for_xpath(
        f'''//div[contains(@data-testid, "{instrument_name}_observationplanRequestsTable")]//div[contains(., "submitted to telescope queue")]''',
        timeout=10,
    )
    driver.click_xpath(
        f'//button[contains(@data-testid, "removeRequest_{observation_plan_request_id}")]',
        scroll_parent=True,
    )
    driver.wait_for_xpath(
        f'''//div[contains(@data-testid, "{instrument_name}_observationplanRequestsTable")]//div[contains(., "deleted from telescope queue")]''',
        timeout=10,
    )
