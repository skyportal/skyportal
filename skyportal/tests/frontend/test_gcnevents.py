import os
import time
import pandas as pd
import uuid
import pytest
from regions import Regions

from skyportal.tests import api


@pytest.mark.flaky(reruns=2)
def test_gcnevents(
    driver, user, super_admin_token, upload_data_token, view_only_token, ztf_camera
):

    datafile = f'{os.path.dirname(__file__)}/../data/GRB180116A_Fermi_GBM_Gnd_Pos.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

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

    driver.get(f'/become_user/{user.id}')
    driver.get('/gcn_events/2018-01-16T00:36:53')

    driver.wait_for_xpath('//*[text()="180116 00:36:53"]')
    driver.wait_for_xpath('//*[text()="Fermi"]')
    driver.wait_for_xpath('//*[text()="GRB"]')


# @pytest.mark.flaky(reruns=2)
def test_observationplan_request(driver, user, super_admin_token, public_group):

    datafile = f'{os.path.dirname(__file__)}/../data/GRB180116A_Fermi_GBM_Gnd_Pos.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    data = {'xml': payload}

    status, data = api('POST', 'gcn_event', data=data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    name = str(uuid.uuid4())
    status, data = api(
        'POST',
        'telescope',
        data={
            'name': name,
            'nickname': name,
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
            "api_observationplan_classname": "MMAAPI",
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
    driver.get('/gcn_events/2018-01-16T00:36:53')

    driver.wait_for_xpath('//*[text()="180116 00:36:53"]')
    driver.wait_for_xpath('//*[text()="Fermi"]')
    driver.wait_for_xpath('//*[text()="GRB"]')

    submit_button_xpath = '//button[@type="submit"]'
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

    driver.click_xpath(f"//div[@data-testid='{instrument_name}-requests-header']")
    driver.wait_for_xpath(
        f'//div[contains(@data-testid, "{instrument_name}_observationplanRequestsTable")]//div[contains(., "g,r,i")]'
    )
    driver.wait_for_xpath(
        f'''//div[contains(@data-testid, "{instrument_name}_observationplanRequestsTable")]//div[contains(., "complete")]'''
    )

    driver.click_xpath(
        '//button[contains(@data-testid, "deleteRequest")]', scroll_parent=True
    )

    driver.wait_for_xpath_to_disappear(
        f'''//div[contains(@data-testid, "{instrument_name}_observationplanRequestsTable")]//div[contains(., "g,r,i")]'''
    )
    driver.wait_for_xpath_to_disappear(
        f'''//div[contains(@data-testid, "{instrument_name}_observationplanRequestsTable")]//div[contains(., "complete")]'''
    )
