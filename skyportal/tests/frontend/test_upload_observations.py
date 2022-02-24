import os
import uuid
import time
import pandas as pd
from regions import Regions
from selenium.common.exceptions import TimeoutException

from skyportal.tests import api


def test_upload_observations(driver, super_admin_user, super_admin_token):

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

    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get("/observations/")

    filename = "sample_observation_data_upload_malformed.csv"

    attachment_file = driver.wait_for_xpath('//input[@type="file"]')
    attachment_file.send_keys(
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'data',
            filename,
        ),
    )

    driver.wait_for_xpath(f'//*[contains(., "{filename}")]')
    submit_button_xpath = '//button[contains(.,"Submit")]'
    driver.click_xpath(submit_button_xpath, scroll_parent=True)

    # check that upload fails
    driver.wait_for_xpath(
        '//div[contains(.,"Filter 1.0 not present in [\'ztfr\']")]', timeout=10
    )

    filename = "sample_observation_data_upload_noseeing.csv"

    attachment_file = driver.wait_for_xpath('//input[@type="file"]')
    attachment_file.send_keys(
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'data',
            filename,
        ),
    )

    driver.wait_for_xpath(f'//*[contains(., "{filename}")]')
    submit_button_xpath = '//button[contains(.,"Submit")]'
    driver.click_xpath(submit_button_xpath, scroll_parent=True)

    scroll_forward_button_xpath = '//button[@data-testid="pagination-next"]'
    try:
        # sometimes need to scroll forward
        driver.click_xpath(scroll_forward_button_xpath, scroll_parent=True)
    except TimeoutException:
        pass
    # check that the executed observation table appears
    driver.wait_for_xpath('//*[text()="94434604"]')

    filename = "sample_observation_data_upload.csv"

    attachment_file = driver.wait_for_xpath('//input[@type="file"]')
    attachment_file.send_keys(
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'data',
            filename,
        ),
    )

    driver.wait_for_xpath(f'//*[contains(., "{filename}")]')
    submit_button_xpath = '//button[contains(.,"Submit")]'
    driver.click_xpath(submit_button_xpath, scroll_parent=True)

    scroll_backward_button_xpath = '//button[@data-testid="pagination-back"]'
    try:
        # sometimes need to scroll backward
        driver.click_xpath(scroll_backward_button_xpath, scroll_parent=True)
    except TimeoutException:
        pass

    # check that the executed observation table appears
    driver.wait_for_xpath('//*[text()="84434604"]')
