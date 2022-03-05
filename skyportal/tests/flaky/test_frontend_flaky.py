import os
import uuid
import pytest
import pandas as pd
import time
from regions import Regions

from skyportal.tests import api
from selenium.webdriver.common.keys import Keys


@pytest.mark.flaky(reruns=2)
def test_telescope_frontend(super_admin_token, super_admin_user, driver):

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

    driver.get(f"/become_user/{super_admin_user.id}")

    # go to the allocations page
    driver.get("/telescopes")

    # check for API instrument
    driver.wait_for_xpath(f'//span[text()="{telescope_name}"]')

    # add dropdown instrument
    name2 = str(uuid.uuid4())
    driver.wait_for_xpath('//*[@id="root_name"]').send_keys(name2)
    driver.wait_for_xpath('//*[@id="root_nickname"]').send_keys(name2)
    driver.wait_for_xpath('//*[@id="root_diameter"]').send_keys('2.0')

    tab = driver.find_element_by_xpath('//*[@class="MuiFormGroup-root"]')
    for row in tab.find_elements_by_xpath('//span[text()="Yes"]'):
        row.click()

    submit_button_xpath = '//button[@type="submit"]'
    driver.wait_for_xpath(submit_button_xpath)
    driver.click_xpath(submit_button_xpath)

    # check for dropdown instrument
    driver.wait_for_xpath(f'//span[text()="{name2}"]')


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

    # check for API instrument
    driver.wait_for_xpath(
        f'//span[text()[contains(.,"{instrument_name}/{telescope_name}")]]', timeout=20
    )
    driver.wait_for_xpath('//*[@id="root_pi"]').send_keys('Shri')
    driver.wait_for_xpath('//*[@id="root_start_date"]').send_keys('01/01/2022')
    driver.wait_for_xpath('//*[@id="root_start_date"]').send_keys(Keys.TAB)
    driver.wait_for_xpath('//*[@id="root_start_date"]').send_keys('01:01')
    driver.wait_for_xpath('//*[@id="root_start_date"]').send_keys('P')

    driver.wait_for_xpath('//*[@id="root_end_date"]').send_keys('03/01/2022')
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


# @pytest.mark.flaky(reruns=2)
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
