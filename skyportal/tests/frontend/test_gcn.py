import os
import pytest
import time

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
    driver.wait_for_xpath('//*[@data-testid="update-aliases"]')
    driver.click_xpath('//*[@data-testid="update-aliases"]')
    driver.wait_for_xpath('//*[contains(., "GRB180116A")]', timeout=60)
    assert len(driver.find_elements(By.XPATH, '//*[@name="aliases-chips"]/*')) == 1

    driver.wait_for_xpath('//a[contains(text(), "GRB 180116A: Fermi GBM Detection")]')
