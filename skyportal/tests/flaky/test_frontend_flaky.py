import datetime
import os
import uuid
import pandas as pd
import time
from regions import Regions
from tdtax import taxonomy, __version__

import pytest
from skyportal.tests import api
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from datetime import date, timedelta


@pytest.mark.flaky(reruns=2)
def test_telescope_frontend_desktop(super_admin_token, super_admin_user, driver):

    telescope_name = str(uuid.uuid4())
    status, data = api(
        'POST',
        'telescope',
        data={
            'name': telescope_name,
            'nickname': telescope_name,
            'lat': 1.0,
            'lon': 1.0,
            'elevation': 0.0,
            'diameter': 10.0,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    driver.get(f"/become_user/{super_admin_user.id}")

    # go to the telescope page
    driver.get("/telescopes")

    # check for API telescope in the map
    marker_xpath = f'//*[@class="rsm-svg "]/*/*/*[@id="telescope_marker"]/*[@id="telescopes_label"][contains(.,"{telescope_name}")]'
    driver.wait_for_xpath(marker_xpath, timeout=30)
    driver.click_xpath(marker_xpath)
    # check for API telescope in the list
    driver.wait_for_xpath(f'//*[@id="{telescope_name}_info"]')

    # go to the new telescope form
    driver.wait_for_xpath('//*[@id="new-telescope"]')
    driver.click_xpath('//*[@id="new-telescope"]')

    # add new telescope
    name2 = str(uuid.uuid4())
    driver.wait_for_xpath('//*[@id="root_name"]').send_keys(name2)
    driver.wait_for_xpath('//*[@id="root_nickname"]').send_keys(name2)
    driver.wait_for_xpath('//*[@id="root_diameter"]').send_keys('2.0')
    driver.wait_for_xpath('//*[@id="root_lat"]').send_keys('10.0')
    driver.wait_for_xpath('//*[@id="root_lon"]').send_keys('10.0')
    driver.wait_for_xpath('//*[@id="root_elevation"]').send_keys('50.0')

    tab = driver.find_element(By.XPATH, '//*[@class="MuiFormGroup-root"]')
    for row in tab.find_elements(By.XPATH, '//span[text()="Yes"]'):
        row.click()

    submit_button_xpath = '//button[@type="submit"]'
    driver.wait_for_xpath(submit_button_xpath)
    driver.click_xpath(submit_button_xpath)

    # check for form telescope in the map
    marker_xpath = f'//*[@class="rsm-svg "]/*/*/*[@id="telescope_marker"]/*[@id="telescopes_label"][contains(.,"{name2}")]'
    driver.wait_for_xpath(marker_xpath, timeout=30)
    driver.click_xpath(marker_xpath)
    # check for form telescope in the list
    driver.wait_for_xpath(f'//*[@id="{name2}_info"]')


@pytest.mark.flaky(reruns=2)
def test_telescope_frontend_mobile(super_admin_token, super_admin_user, driver):

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
    # resize screen to fit mobile width defined in the frontend
    driver.set_window_position(0, 0)
    driver.set_window_size(550, 1000)
    driver.get(f"/become_user/{super_admin_user.id}")

    # go to the allocations page
    driver.get("/telescopes")

    # check for API instrument
    driver.wait_for_xpath(
        f'//*[@class="MuiList-root MuiList-padding"]/*/*/span[text()="{telescope_name}"]'
    )

    # add dropdown instrument
    name2 = str(uuid.uuid4())
    driver.wait_for_xpath('//*[@id="root_name"]').send_keys(name2)
    driver.wait_for_xpath('//*[@id="root_nickname"]').send_keys(name2)
    driver.wait_for_xpath('//*[@id="root_lat"]').send_keys('5.0')
    driver.wait_for_xpath('//*[@id="root_lon"]').send_keys('5.0')
    driver.wait_for_xpath('//*[@id="root_diameter"]').send_keys('2.0')
    driver.wait_for_xpath('//*[@id="root_elevation"]').send_keys('50.0')

    tab = driver.find_element(By.XPATH, '//*[@class="MuiFormGroup-root"]')
    for row in tab.find_elements(By.XPATH, '//span[text()="Yes"]'):
        row.click()

    submit_button_xpath = '//button[@type="submit"]'
    driver.wait_for_xpath(submit_button_xpath)
    driver.click_xpath(submit_button_xpath)

    # check for dropdown instrument
    driver.wait_for_xpath(
        f'//*[@class="MuiList-root MuiList-padding"]/*/*/span[text()="{name2}"]'
    )

    driver.set_window_position(0, 0)
    driver.set_window_size(1920, 1080)


@pytest.mark.flaky(reruns=5)
def test_instrument_frontend(super_admin_token, super_admin_user, driver):

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
            'api_classname': 'ZTFAPI',
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    driver.get(f"/become_user/{super_admin_user.id}")

    # go to the allocations page
    driver.get("/instruments")

    # check for API instrument
    driver.wait_for_xpath(
        f'//span[text()[contains(.,"{instrument_name}/{telescope_name}")]]', timeout=20
    )
    # add dropdown instrument
    instrument_name2 = str(uuid.uuid4())
    driver.wait_for_xpath('//*[@id="root_name"]').send_keys(instrument_name2)
    driver.click_xpath('//*[@id="root_type"]')
    driver.click_xpath('//li[contains(text(), "Imager")]')
    driver.wait_for_xpath('//*[@id="root_band"]').send_keys('Optical')
    driver.click_xpath('//*[@id="root_telescope_id"]')
    driver.click_xpath(f'//li[contains(text(), "{telescope_name}")]')
    driver.click_xpath('//*[@id="root_api_classname"]')
    driver.click_xpath('//li[contains(text(), "ZTFAPI")]')

    submit_button_xpath = '//button[@type="submit"]'
    driver.wait_for_xpath(submit_button_xpath)
    driver.click_xpath(submit_button_xpath)
    # check for new API instrument
    driver.wait_for_xpath(
        f'//span[text()[contains(.,"{instrument_name2}/{telescope_name}")]]', timeout=20
    )
    # try adding a second time
    driver.click_xpath("//body")
    driver.execute_script("window.scrollBy(0,0)", "")
    driver.wait_for_xpath('//*[@id="root_name"]').send_keys(instrument_name2)

    driver.click_xpath('//*[@id="root_type"]')
    driver.click_xpath('//li[contains(text(), "Imager")]')
    driver.wait_for_xpath('//*[@id="root_band"]').send_keys('Optical')
    driver.click_xpath('//*[@id="root_telescope_id"]')
    driver.click_xpath(f'//li[contains(text(), "{telescope_name}")]')
    driver.click_xpath('//*[@id="root_api_classname"]')
    driver.click_xpath('//li[contains(text(), "ZTFAPI")]')

    submit_button_xpath = '//button[@type="submit"]'
    driver.wait_for_xpath(submit_button_xpath)
    driver.click_xpath(submit_button_xpath)

    driver.wait_for_xpath('//span[contains(text(), "Instrument name matches another")]')


@pytest.mark.flaky(reruns=3)
def test_super_user_post_allocation(
    public_group, super_admin_token, super_admin_user, driver
):

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
            'api_classname': 'ZTFAPI',
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    instrument_id = data['data']['id']

    instrument_name2 = str(uuid.uuid4())
    status, data = api(
        'POST',
        'instrument',
        data={
            'name': instrument_name2,
            'type': 'imager',
            'band': 'NIR',
            'filters': ['f110w'],
            'telescope_id': telescope_id,
            'api_classname': 'ZTFAPI',
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    request_data = {
        'group_id': public_group.id,
        'instrument_id': instrument_id,
        'pi': 'Shri Kulkarni',
        'hours_allocated': 200,
        'start_date': '3021-02-27T00:00:00',
        'end_date': '3021-07-20T00:00:00',
        'proposal_id': 'COO-2020A-P01',
    }

    status, data = api('POST', 'allocation', data=request_data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    id = data['data']['id']

    status, data = api('GET', f'allocation/{id}', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    driver.get(f"/become_user/{super_admin_user.id}")

    # go to the allocations page
    driver.get("/allocations")
    start_date = date.today().strftime("%m/%d/%Y")
    end_date = (date.today() + timedelta(days=2)).strftime("%m/%d/%Y")
    # check for API instrument
    driver.wait_for_xpath(
        f'//span[text()[contains(.,"{instrument_name}/{telescope_name}")]]', timeout=20
    )
    driver.wait_for_xpath('//*[@id="root_pi"]').send_keys('Shri')
    driver.wait_for_xpath('//*[@id="root_start_date"]').send_keys(start_date)
    driver.wait_for_xpath('//*[@id="root_start_date"]').send_keys(Keys.TAB)
    driver.wait_for_xpath('//*[@id="root_start_date"]').send_keys('01:01')
    driver.wait_for_xpath('//*[@id="root_start_date"]').send_keys('P')

    driver.wait_for_xpath('//*[@id="root_end_date"]').send_keys(end_date)
    driver.wait_for_xpath('//*[@id="root_end_date"]').send_keys(Keys.TAB)
    driver.wait_for_xpath('//*[@id="root_end_date"]').send_keys('01:01')
    driver.wait_for_xpath('//*[@id="root_end_date"]').send_keys('P')

    driver.wait_for_xpath('//*[@id="root_hours_allocated"]').send_keys('100')
    driver.click_xpath('//*[@id="root_instrument_id"]')
    driver.click_xpath(f'//li[contains(text(), "{instrument_name2}")]')
    driver.click_xpath('//*[@id="root_group_id"]')
    driver.click_xpath('//li[contains(text(), "Sitewide Group")]')

    submit_button_xpath = '//button[@type="submit"]'
    driver.wait_for_xpath(submit_button_xpath)
    driver.click_xpath(submit_button_xpath)

    # check for dropdown instrument
    driver.wait_for_xpath(
        f'//span[text()[contains(.,"{instrument_name2}/{telescope_name}")]]'
    )


@pytest.mark.flaky(reruns=2)
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
    instrument_id = data['data']['id']

    params = {'includeGeoJSON': True}

    # wait for the fields to populate
    nretries = 0
    fields_loaded = False
    while not fields_loaded and nretries < 5:
        try:
            status, data = api(
                'GET',
                f'instrument/{instrument_id}',
                params=params,
                token=super_admin_token,
            )
            assert status == 200
            assert data['status'] == 'success'
            assert data['data']['band'] == 'NIR'

            assert len(data['data']['fields']) == 5
            fields_loaded = True
        except AssertionError:
            nretries = nretries + 1
            time.sleep(3)

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
    nretries = 0
    observations_loaded = False
    while not observations_loaded and nretries < 5:
        try:
            status, data = api(
                'GET', 'observation', params=data, token=super_admin_token
            )
            assert status == 200
            data = data["data"]
            assert len(data['observations']) == 10
            observations_loaded = True
        except AssertionError:
            nretries = nretries + 1
            time.sleep(3)

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
    driver.wait_for_xpath('//*[@id="localizationSelectLabel"]/../*/*[@role="button"]')
    driver.click_xpath('//*[@id="localizationSelectLabel"]/../*/*[@role="button"]')
    driver.wait_for_xpath('//li[contains(text(), "bayestar.fits.gz")]')
    driver.click_xpath('//li[contains(text(), "bayestar.fits.gz")]')

    submit_button_xpath = (
        '//div[@data-testid="gcnsource-selection-form"]//button[@type="submit"]'
    )
    driver.wait_for_xpath(submit_button_xpath)
    driver.click_xpath(submit_button_xpath)

    # check that the executed observation table appears
    driver.wait_for_xpath('//*[text()="84434604"]', timeout=10)
    driver.wait_for_xpath('//*[text()="ztfr"]')
    driver.wait_for_xpath('//*[text()="1.57415"]')
    driver.wait_for_xpath('//*[text()="20.40705"]')


@pytest.mark.flaky(reruns=2)
def test_followup_request_frontend(
    public_group_sedm_allocation,
    public_source,
    upload_data_token,
    super_admin_user,
    sedm,
    driver,
):

    request_data = {
        'allocation_id': public_group_sedm_allocation.id,
        'obj_id': public_source.id,
        'payload': {
            'priority': 5,
            'start_date': '3020-09-01',
            'end_date': '3022-09-01',
            'observation_type': 'IFU',
        },
    }

    status, data = api(
        'POST', 'followup_request', data=request_data, token=upload_data_token
    )
    assert status == 200
    assert data['status'] == 'success'

    driver.get(f"/become_user/{super_admin_user.id}")

    # go to the allocations page
    driver.get("/followup_requests")

    driver.click_xpath(f"//div[@data-testid='{sedm.name}-requests-header']")
    driver.wait_for_xpath(
        f'//div[contains(@data-testid, "{sedm.name}_followupRequestsTable")]//div[contains(., "IFU")]'
    )
    driver.wait_for_xpath(
        f'''//div[contains(@data-testid, "{sedm.name}_followupRequestsTable")]//div[contains(., "5")]'''
    )
    driver.wait_for_xpath(
        f'''//div[contains(@data-testid, "{sedm.name}_followupRequestsTable")]//div[contains(., "submitted")]'''
    )

    driver.wait_for_xpath('//*[@id="root_sourceID"]').send_keys('not_the_source')
    submit_button_xpath = '//button[contains(.,"Submit")]'
    driver.wait_for_xpath(submit_button_xpath)
    driver.click_xpath(submit_button_xpath)

    driver.wait_for_xpath_to_disappear(
        f'''//div[contains(@data-testid, "{sedm.name}_followupRequestsTable")]//div[contains(., "IFU")]'''
    )
    driver.wait_for_xpath_to_disappear(
        f'''//div[contains(@data-testid, "{sedm.name}_followupRequestsTable")]//div[contains(., "5")]'''
    )
    driver.wait_for_xpath_to_disappear(
        f'''//div[contains(@data-testid, "{sedm.name}_followupRequestsTable")]//div[contains(., "submitted")]'''
    )


# @pytest.mark.flaky(reruns=2)
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

    params = {'includeGeoJSON': True}

    # wait for the fields to populate
    nretries = 0
    fields_loaded = False
    while not fields_loaded and nretries < 5:
        try:
            status, data = api(
                'GET',
                f'instrument/{instrument_id}',
                token=super_admin_token,
                params=params,
            )
            assert status == 200
            assert data['status'] == 'success'
            assert data['data']['band'] == 'NIR'

            assert len(data['data']['fields']) == 5
            fields_loaded = True
        except AssertionError:
            nretries = nretries + 1
            time.sleep(3)

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
    catalog_name = str(uuid.uuid4())
    galaxy_name = str(uuid.uuid4())
    data = {
        'catalog_name': catalog_name,
        'catalog_data': {'name': [galaxy_name], 'ra': [228.5], 'dec': [35.5]},
    }
    status, data = api('POST', 'galaxy_catalog', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    driver.get(f'/become_user/{user.id}')
    driver.get('/gcn_events/2019-04-25T08:18:05')

    nretries = 0
    while nretries < 5:
        try:
            driver.wait_for_xpath('//*[text()="190425 08:18:05"]')
            break
        except TimeoutException:
            driver.refresh()
            nretries = nretries + 1

    driver.wait_for_xpath('//*[text()="LVC"]')
    driver.wait_for_xpath('//*[text()="BNS"]')

    submit_button_xpath = (
        '//div[@data-testid="observationplan-request-form"]//button[@type="submit"]'
    )
    driver.wait_for_xpath(submit_button_xpath)

    select_box = driver.find_element(
        By.ID, "mui-component-select-followupRequestAllocationSelect"
    )
    select_box.click()
    driver.click_xpath(
        f'//li[contains(text(), "{instrument_name}")][contains(text(), "{public_group.name}")]',
        scroll_parent=True,
    )
    # Click somewhere outside to remove focus from instrument select
    driver.click_xpath("//body")
    driver.click_xpath(submit_button_xpath)

    submit_button_xpath = '//button[contains(., "Generate Observation Plans")]'
    driver.wait_for_xpath(submit_button_xpath)
    driver.click_xpath(submit_button_xpath)
    time.sleep(30)

    driver.wait_for_xpath(
        f"//div[@data-testid='{instrument_name}-requests-header']", timeout=30
    )
    driver.click_xpath(f"//div[@data-testid='{instrument_name}-requests-header']")
    driver.wait_for_xpath(
        f'//div[contains(@data-testid, "{instrument_name}_observationplanRequestsTable")]//div[contains(., "ztfg,ztfr,ztfg")]',
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
        f'//a[contains(@data-testid, "gcnRequest_{observation_plan_request_id}")]',
        scroll_parent=True,
    )
    driver.click_xpath(
        f'//button[contains(@data-testid, "treasuremapRequest_{observation_plan_request_id}")]',
        scroll_parent=True,
    )
    driver.click_xpath(
        f'//a[contains(@data-testid, "downloadRequest_{observation_plan_request_id}")]',
        scroll_parent=True,
    )
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
    driver.click_xpath(
        f'//button[contains(@data-testid, "observingRunRequest_{observation_plan_request_id}")]',
        scroll_parent=True,
    )
    driver.wait_for_xpath(
        f'''//div[contains(@data-testid, "{instrument_name}_observationplanRequestsTable")]//div[contains(., "deleted from telescope queue")]''',
        timeout=10,
    )


@pytest.mark.flaky(reruns=2)
def test_gcn_request(driver, user, super_admin_token, public_group):

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
            'filters': ['ztfr'],
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

    params = {'includeGeoJSON': True}

    # wait for the fields to populate
    nretries = 0
    fields_loaded = False
    while not fields_loaded and nretries < 5:
        try:
            status, data = api(
                'GET',
                f'instrument/{instrument_id}',
                params=params,
                token=super_admin_token,
            )
            assert status == 200
            assert data['status'] == 'success'
            assert data['data']['band'] == 'NIR'

            assert len(data['data']['fields']) == 5
            fields_loaded = True
        except AssertionError:
            nretries = nretries + 1
            time.sleep(3)

    datafile = f'{os.path.dirname(__file__)}/../../../data/sample_observation_data.csv'
    data = {
        'telescopeName': telescope_name,
        'instrumentName': instrument_name,
        'observationData': pd.read_csv(datafile).to_dict(orient='list'),
    }

    status, data = api('POST', 'observation', data=data, token=super_admin_token)

    assert status == 200
    assert data['status'] == 'success'

    params = {
        'telescopeName': telescope_name,
        'instrumentName': instrument_name,
        'startDate': "2019-04-25 08:18:05",
        'endDate': "2019-04-28 08:18:05",
        'localizationDateobs': "2019-04-25T08:18:05",
        'localizationName': "bayestar.fits.gz",
        'localizationCumprob': 1.01,
        'returnStatistics': True,
    }

    # wait for the executed observations to populate
    nretries = 0
    observations_loaded = False
    while not observations_loaded and nretries < 5:
        try:
            status, data = api(
                'GET', 'observation', params=params, token=super_admin_token
            )
            assert status == 200
            data = data["data"]
            assert len(data['observations']) == 10
            observations_loaded = True
        except AssertionError:
            nretries = nretries + 1
            time.sleep(3)

    driver.get(f'/become_user/{user.id}')
    driver.get('/gcn_events/2019-04-25T08:18:05')
    nretries = 0
    while nretries < 5:
        try:
            driver.wait_for_xpath('//*[text()="190425 08:18:05"]', timeout=20)
            break
        except TimeoutException:
            driver.refresh()
            nretries = nretries + 1
    driver.wait_for_xpath('//*[text()="LVC"]')
    driver.wait_for_xpath('//*[text()="BNS"]')

    driver.wait_for_xpath('//*[@id="localizationSelectLabel"]/../*/*[@role="button"]')
    driver.click_xpath('//*[@id="localizationSelectLabel"]/../*/*[@role="button"]')
    driver.wait_for_xpath('//li[contains(text(), "bayestar.fits.gz")]')
    driver.click_xpath('//li[contains(text(), "bayestar.fits.gz")]')
    driver.wait_for_xpath('//*[@id="root_localizationCumprob"]').clear()
    driver.wait_for_xpath('//*[@id="root_localizationCumprob"]').send_keys(1.01)

    submit_button_xpath = '//button[@type="submit"]'
    driver.wait_for_xpath(submit_button_xpath)
    driver.click_xpath(submit_button_xpath)

    # adding a retry loop because the list of instruments can take time to be fetched
    driver.wait_for_xpath('//*[@id="instrumentSelectLabel"]/../*/*[@role="button"]')
    driver.click_xpath('//*[@id="instrumentSelectLabel"]/../*/*[@role="button"]')

    nretries = 0
    while nretries < 5:
        try:
            driver.click_xpath(
                f'//*[@id="menu-gcnPageInstrumentSelect"]/*/ul/li[contains(text(), "{instrument_name}")]',
                scroll_parent=True,
            )
            break
        except AssertionError:
            nretries = nretries + 1

    driver.click_xpath(
        f'//a[contains(@data-testid, "observationGcn_{instrument_id}")]',
        scroll_parent=True,
    )


@pytest.mark.flaky(reruns=2)
def test_candidate_date_filtering(
    driver,
    user,
    public_candidate,
    public_filter,
    public_group,
    upload_data_token,
    ztf_camera,
):
    candidate_id = str(uuid.uuid4())
    for i in range(5):
        status, data = api(
            "POST",
            "candidates",
            data={
                "id": f"{candidate_id}_{i}",
                "ra": 234.22,
                "dec": -22.33,
                "redshift": 3,
                "altdata": {"simbad": {"class": "RRLyr"}},
                "transient": False,
                "ra_dis": 2.3,
                "filter_ids": [public_filter.id],
                "passed_at": str(datetime.datetime.utcnow()),
            },
            token=upload_data_token,
        )
        assert status == 200

        status, data = api(
            "POST",
            "photometry",
            data={
                "obj_id": f"{candidate_id}_{i}",
                "mjd": 58000.0,
                "instrument_id": ztf_camera.id,
                "flux": 12.24,
                "fluxerr": 0.031,
                "zp": 25.0,
                "magsys": "ab",
                "filter": "ztfr",
                "group_ids": [public_group.id],
            },
            token=upload_data_token,
        )
        assert status == 200

    driver.get(f"/become_user/{user.id}")
    driver.get("/candidates")
    driver.click_xpath(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]',
        wait_clickable=False,
    )
    start_date_input = driver.wait_for_xpath("//input[@id='startDatePicker']")
    start_date_input.clear()
    start_date_input.send_keys("12/01/2020 12:00 p")
    end_date_input = driver.wait_for_xpath("//input[@id='endDatePicker']")
    end_date_input.clear()
    end_date_input.send_keys("12/01/2020 12:00 p")
    submit_button = driver.wait_for_xpath_to_be_clickable('//button[text()="Search"]')
    driver.scroll_to_element_and_click(submit_button)
    for i in range(5):
        driver.wait_for_xpath_to_disappear(
            f'//a[@data-testid="{candidate_id}_{i}"]', 10
        )
    end_date_input.clear()
    end_date_input.send_keys("12/01/2090 12:00 p")
    submit_button = driver.wait_for_xpath_to_be_clickable('//button[text()="Search"]')
    driver.scroll_to_element_and_click(submit_button)
    for i in range(5):
        driver.wait_for_xpath(f'//a[@data-testid="{candidate_id}_{i}"]', 10)


def filter_for_user(driver, username):
    # Helper function to filter for a specific user on the page
    driver.click_xpath("//button[@data-testid='Filter Table-iconButton']")
    username_input_xpath = "//input[@id='root_username']"
    username_input = driver.wait_for_xpath(username_input_xpath)
    driver.click_xpath(username_input_xpath)
    username_input.send_keys(username)
    driver.click_xpath(
        "//div[contains(@class, 'MUIDataTableFilter-root')]//button[text()='Submit']",
        scroll_parent=True,
    )


def test_user_expiration(
    driver,
    user,
    super_admin_user,
):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/user_management')
    filter_for_user(driver, user.username)

    # Set expiration date to today
    driver.click_xpath(f"//*[@data-testid='editUserExpirationDate{user.id}']")
    date = datetime.now().strftime("%m/%d/%Y")
    driver.wait_for_xpath("//input[@id='expirationDatePicker']").send_keys(date)
    driver.click_xpath('//*[text()="Submit"]')

    # Check that user deactivated
    driver.get(f'/become_user/{user.id}')
    driver.get("/")
    driver.wait_for_xpath_to_disappear("//*[contains(text(), 'Top Sources')]")


def test_slider_classifications(
    driver,
    public_source,
    super_admin_user,
    public_group,
    taxonomy_token,
):
    test_taxonomy = "test taxonomy" + str(uuid.uuid4())
    status, _ = api(
        'POST',
        'taxonomy',
        data={
            'name': test_taxonomy,
            'hierarchy': taxonomy,
            'group_ids': [public_group.id],
            'provenance': f"tdtax_{__version__}",
            'version': __version__,
            'isLatest': True,
        },
        token=taxonomy_token,
    )
    assert status == 200

    driver.get(f"/become_user/{super_admin_user.id}")  # become a super-user

    # Go to the group sources page
    driver.get(f"/group_sources/{public_group.id}")

    # Wait for the group name appears
    driver.wait_for_xpath(f"//*[text()[contains(., '{public_group.name}')]]")

    # Expand public source row
    driver.click_xpath("//*[@id='expandable-button']")

    # Select test taxonomy
    driver.click_xpath(f"//*[@id='taxonomy-select-{public_source.id}']")
    driver.click_xpath(f"//li[text()='{test_taxonomy}']", scroll_parent=True)
    driver.click_xpath("//h6[text()='Stellar variable']")

    # Set 'Algol' slider to 0.5
    driver.click_xpath("//span[@id='Algol']//span[@data-index='2']")
    driver.click_xpath("//button[@name='submitClassificationsButton']")

    # need to reload the page to see classification
    driver.get(f"/group_sources/{public_group.id}")
    driver.wait_for_xpath(f"//*[text()[contains(., '{'Algol'}')]]")
