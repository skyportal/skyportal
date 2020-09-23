import uuid
import time
import pytest
import requests
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from baselayer.app.env import load_env
from skyportal.tests import api

env, cfg = load_env()
endpoint = cfg['app.sedm_endpoint']
sedm_isonline = requests.get(endpoint, timeout=5).status_code in [200, 400]


def add_telescope_and_instrument(instrument_name, token):
    status, data = api("GET", f"instrument?name={instrument_name}", token=token)
    if len(data["data"]) == 1:
        return data["data"][0]

    telescope_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "telescope",
        data={
            "name": telescope_name,
            "nickname": telescope_name,
            "lat": 0.0,
            "lon": 0.0,
            "elevation": 0.0,
            "diameter": 10.0,
            "robotic": True,
        },
        token=token,
    )
    assert status == 200
    assert data["status"] == "success"
    telescope_id = data["data"]["id"]

    status, data = api(
        "POST",
        "instrument",
        data={
            "name": instrument_name,
            "type": "imager",
            "band": "Optical",
            "telescope_id": telescope_id,
            "filters": ["ztfg"],
            "api_classname": "SEDMAPI",
        },
        token=token,
    )
    assert status == 200
    assert data["status"] == "success"
    return data["data"]


def add_allocation(instrument_id, group_id, token):
    status, data = api(
        "POST",
        "allocation",
        data={
            "group_id": group_id,
            "instrument_id": instrument_id,
            "hours_allocated": 100,
            "pi": "Ed Hubble",
        },
        token=token,
    )
    assert status == 200
    assert data["status"] == "success"
    return data["data"]


def add_followup_request_using_frontend_and_verify(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""

    idata = add_telescope_and_instrument("SEDM", super_admin_token)
    add_allocation(idata['id'], public_group.id, super_admin_token)

    driver.get(f"/become_user/{super_admin_user.id}")

    for _ in range(2):
        try:
            driver.get(f"/source/{public_source.id}")
            # wait for the plots to load
            driver.wait_for_xpath('//div[@class="bk-root"]//span[text()="Flux"]')
            # this waits for the spectroscopy plot by looking for the element Mg
            driver.wait_for_xpath('//div[@class="bk-root"]//label[text()="Mg"]')
        except TimeoutException:
            continue
        else:
            break

    submit_button = driver.wait_for_xpath(
        '//form[@class="rjsf"]//button[@type="submit"]'
    )

    driver.save_screenshot('test_01.png')
    mode_select = driver.wait_for_xpath('//*[@id="root_observation_type"]')
    driver.save_screenshot('test_02.png')
    driver.scroll_to_element(mode_select)
    driver.save_screenshot('test_03.png')
    ActionChains(driver).move_to_element(mode_select).pause(1).click().perform()
    driver.save_screenshot('test_04.png')

    time.sleep(1)
    driver.save_screenshot('test_05.png')
    time.sleep(1)
    driver.save_screenshot('test_06.png')
    time.sleep(1)
    driver.save_screenshot('test_07.png')
    time.sleep(1)
    driver.save_screenshot('test_08.png')

    with open("test_09.png", "w") as f:
        f.write(driver.page_source)

    mix_n_match_option = driver.wait_for_xpath('''//li[@data-value="Mix 'n Match"]''')
    driver.scroll_to_element_and_click(mix_n_match_option)

    u_band_option = driver.wait_for_xpath('//input[@id="root_observation_choices_0"]')

    driver.scroll_to_element_and_click(u_band_option)

    ifu_option = driver.wait_for_xpath('//input[@id="root_observation_choices_4"]')

    driver.scroll_to_element_and_click(ifu_option)

    driver.save_screenshot('test_1.png')
    driver.scroll_to_element_and_click(submit_button)
    driver.save_screenshot('test_2.png')
    time.sleep(1)
    driver.save_screenshot('test_3.png')
    time.sleep(1)
    driver.save_screenshot('test_4.png')
    time.sleep(1)
    driver.save_screenshot('test_5.png')
    time.sleep(1)
    driver.save_screenshot('test_6.png')
    time.sleep(1)
    driver.save_screenshot('test_7.png')
    time.sleep(1)
    driver.save_screenshot('test_8.png')

    with open("test_9.png", "w") as f:
        f.write(driver.page_source)

    driver.wait_for_xpath(
        f'//table[contains(@data-testid, "followupRequestTable")]//td[contains(., "Mix \'n Match")]'
    )
    driver.wait_for_xpath(
        f'''//table[contains(@data-testid, "followupRequestTable")]//td[contains(., "u,IFU")]'''
    )
    driver.wait_for_xpath(
        f'''//table[contains(@data-testid, "followupRequestTable")]//td[contains(., "1")]'''
    )
    driver.wait_for_xpath(
        f'''//table[contains(@data-testid, "followupRequestTable")]//td[contains(., "submitted")]'''
    )


@pytest.mark.skipif(not sedm_isonline, reason="SEDM server down")
def test_submit_new_followup_request(
    driver, super_admin_user, public_source, super_admin_token, public_group
):

    add_followup_request_using_frontend_and_verify(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )


@pytest.mark.skipif(not sedm_isonline, reason="SEDM server down")
def test_edit_existing_followup_request(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )
    edit_button = driver.wait_for_xpath(f'//button[contains(@name, "editRequest")]')
    driver.scroll_to_element_and_click(edit_button)
    mode_select = driver.wait_for_xpath(
        '//div[@role="dialog"]//div[@id="root_observation_type"]'
    )
    ActionChains(driver).move_to_element(mode_select).pause(1).click().perform()

    mix_n_match_option = driver.wait_for_xpath('''//li[@data-value="IFU"]''')
    driver.scroll_to_element_and_click(mix_n_match_option)

    submit_button = driver.wait_for_xpath(
        '//form[@class="rjsf"]//button[@type="submit"]'
    )

    driver.scroll_to_element_and_click(submit_button)

    driver.wait_for_xpath(
        '//table[contains(@data-testid, "followupRequestTable")]//td[contains(., "IFU")]'
    )
    driver.wait_for_xpath(
        '''//table[contains(@data-testid, "followupRequestTable")]//td[contains(., "1")]'''
    )
    driver.wait_for_xpath(
        '''//table[contains(@data-testid, "followupRequestTable")]//td[contains(., "submitted")]'''
    )


@pytest.mark.skipif(not sedm_isonline, reason='SEDM server down')
def test_delete_followup_request(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )
    delete_button = driver.wait_for_xpath(f'//button[contains(@name, "deleteRequest")]')
    driver.scroll_to_element_and_click(delete_button)

    driver.wait_for_xpath_to_disappear(
        '''//table[contains(@data-testid, "followupRequestTable")]//td[contains(., "u,IFU")]'''
    )
    driver.wait_for_xpath_to_disappear(
        '''//table[contains(@data-testid, "followupRequestTable")]//td[contains(., "1")]'''
    )
    driver.wait_for_xpath_to_disappear(
        '''//table[contains(@data-testid, "followupRequestTable")]//td[contains(., "submitted")]'''
    )
