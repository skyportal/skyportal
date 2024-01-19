import os
import pytest
import time
import uuid

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

from skyportal.tests import api

from baselayer.app.config import load_config


cfg = load_config()


def get_summary(driver, user, group, showSources, showGalaxies, showObservations):
    driver.get(f'/become_user/{user.id}')
    driver.get('/gcn_events/2019-08-14T21:10:39')

    summary_button = driver.wait_for_xpath_to_be_clickable(
        '//button[@name="gcn_summary"]'
    )
    driver.scroll_to_element_and_click(summary_button)

    group_select = '//*[@aria-labelledby="group-select"]'
    driver.wait_for_xpath(group_select)
    driver.click_xpath(group_select)
    group_select_option = f'//li[contains(., "{group.name}")]'
    driver.wait_for_xpath(group_select_option)
    driver.click_xpath(group_select_option)

    if showSources is True:
        show_sources = '//*[@label="Show Sources"]'
        driver.wait_for_xpath(show_sources)
        driver.click_xpath(show_sources)
    if showGalaxies is True:
        show_galaxies = '//*[@label="Show Galaxies"]'
        driver.wait_for_xpath(show_galaxies)
        driver.click_xpath(show_galaxies)
    if showObservations is True:
        show_observations = '//*[@label="Show Observations"]'
        driver.wait_for_xpath(show_observations)
        driver.click_xpath(show_observations)

    get_summary_button = '//button[contains(.,"Get Summary")]'
    element = driver.wait_for_xpath(get_summary_button)
    element.send_keys(Keys.END)
    driver.click_xpath(get_summary_button)

    text_area = '//textarea[@id="text"]'
    driver.wait_for_xpath(text_area, timeout=60)
    driver.wait_for_xpath('//textarea[contains(.,"TITLE: GCN SUMMARY")]', 60)

    download_button = '//button[contains(.,"Download")]'
    driver.click_xpath(download_button)


@pytest.mark.flaky(reruns=3)
def test_gcn_tach(
    driver,
    super_admin_user,
    super_admin_token,
):
    datafile = f'{os.path.dirname(__file__)}/../data/GRB180116A_Fermi_GBM_Gnd_Pos.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    event_data = {'xml': payload}

    dateobs = "2018-01-16T00:36:53"
    status, data = api('GET', f'gcn_event/{dateobs}', token=super_admin_token)

    if status == 404:
        status, data = api(
            'POST', 'gcn_event', data=event_data, token=super_admin_token
        )
        assert status == 200
        assert data['status'] == 'success'

    # wait for event to load
    for n_times in range(26):
        status, data = api('GET', f"gcn_event/{dateobs}", token=super_admin_token)
        if data['status'] == 'success':
            break
        time.sleep(2)
    assert n_times < 25

    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get(f'/gcn_events/{dateobs}')

    right_panel_button = '//*[@data-testid="right-panel-button"]'
    driver.wait_for_xpath(right_panel_button)
    driver.click_xpath(right_panel_button)

    update_aliases = driver.wait_for_xpath(
        '//*[@data-testid="update-aliases"]', timeout=30
    )
    driver.scroll_to_element_and_click(update_aliases, scroll_parent=True)
    driver.wait_for_xpath('//*[contains(., "GRB180116A")]', timeout=60)
    assert (
        len(driver.find_elements(By.XPATH, '//*[@name="gcn_triggers-aliases"]/*')) == 4
    )

    driver.wait_for_xpath('//a[contains(text(), "GRB 180116A: Fermi GBM Detection")]')


def test_gcn_allocation_triggers(
    driver,
    public_group,
    super_admin_user,
    super_admin_token,
    view_only_user,
):
    datafile = f'{os.path.dirname(__file__)}/../data/GRB180116A_Fermi_GBM_Gnd_Pos.xml'
    with open(datafile, 'rb') as fid:
        payload = fid.read()
    event_data = {'xml': payload}

    dateobs = "2018-01-16T00:36:53"
    status, data = api('GET', f'gcn_event/{dateobs}', token=super_admin_token)

    if status == 404:
        status, data = api(
            'POST', 'gcn_event', data=event_data, token=super_admin_token
        )
        assert status == 200
        assert data['status'] == 'success'

    for n_times in range(26):
        status, data = api('GET', f"gcn_event/{dateobs}", token=super_admin_token)
        if data['status'] == 'success':
            break
        time.sleep(2)
    assert n_times < 25

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
            'api_classname': 'ZTFAPI',
            'api_classname_obsplan': 'ZTFMMAAPI',
            'field_fov_type': 'circle',
            'field_fov_attributes': 3.0,
            'sensitivity_data': {
                'ztfr': {
                    'limiting_magnitude': 20.3,
                    'magsys': 'ab',
                    'exposure_time': 30,
                    'zeropoint': 26.3,
                }
            },
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    instrument_id = data['data']['id']

    request_data = {
        'group_id': public_group.id,
        'instrument_id': instrument_id,
        'pi': 'Shri Kulkarni',
        'hours_allocated': 200,
        'start_date': '3021-02-27T00:00:00',
        'end_date': '3021-07-20T00:00:00',
        'proposal_id': 'COO-2020A-P01',
        'default_share_group_ids': [public_group.id],
    }

    status, data = api('POST', 'allocation', data=request_data, token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'
    allocation_id = data['data']['id']

    status, data = api('GET', f'allocation/{allocation_id}', token=super_admin_token)
    assert status == 200
    assert data['status'] == 'success'

    # go to the page of the event
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get(f'/gcn_events/{dateobs}')

    # find the trigger for the allocation
    chip_not_set = f'//div[@id="{instrument_name}_not_set"]'
    driver.wait_for_xpath(chip_not_set)
    assert len(driver.find_elements(By.XPATH, chip_not_set)) == 1
    driver.click_xpath(chip_not_set)

    # check that the allocation trigger is not set
    current_state = f'//div[@id="{allocation_id}_current"]/span[contains(., "Not set")]'
    driver.wait_for_xpath(current_state)

    trigger_state = (
        f'//div[@id="{allocation_id}_triggered"]/span[contains(., "Triggered")]'
    )
    driver.wait_for_xpath(trigger_state)
    driver.click_xpath(trigger_state)

    # check that the allocation trigger is triggered
    chip_triggered = f'//div[@id="{instrument_name}_triggered"]'
    driver.wait_for_xpath(chip_triggered)
    driver.click_xpath(chip_triggered)

    new_current_state = (
        f'//div[@id="{allocation_id}_current"]/span[contains(., "Triggered")]'
    )
    driver.wait_for_xpath(new_current_state)

    # now switch to view only user
    driver.get(f'/become_user/{view_only_user.id}')
    driver.get(f'/gcn_events/{dateobs}')

    driver.wait_for_xpath(chip_triggered)
    assert len(driver.find_elements(By.XPATH, chip_triggered)) == 1
    driver.click_xpath(chip_triggered)

    # we should see an error message
    driver.wait_for_xpath(
        '//*[text()="You do not have permission to edit this GCN event allocation triggers"]'
    )
