import uuid
import pytest
import requests
from selenium.webdriver.common.action_chains import ActionChains
from baselayer.app.env import load_env
from skyportal.tests import api
import glob
import os


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
            "filters": ["sdssu", "sdssg", 'sdssr', 'sdssi', 'sdssz'],
            "api_classname": f"{instrument_name.upper()}API",
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


def add_followup_request_using_frontend_and_verify_SEDM(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""

    idata = add_telescope_and_instrument("SEDM", super_admin_token)
    add_allocation(idata['id'], public_group.id, super_admin_token)

    driver.get(f"/become_user/{super_admin_user.id}")

    driver.get(f"/source/{public_source.id}")
    # wait for the plots to load
    driver.wait_for_xpath('//div[@class="bk-root"]//span[text()="Flux"]', timeout=20)
    # this waits for the spectroscopy plot by looking for the element Mg
    driver.wait_for_xpath('//div[@class="bk-root"]//label[text()="Mg"]', timeout=20)

    submit_button = driver.wait_for_xpath(
        '//form[@class="rjsf"]//button[@type="submit"]'
    )

    mode_select = driver.wait_for_xpath('//*[@id="root_observation_type"]')
    driver.scroll_to_element(mode_select)
    ActionChains(driver).move_to_element(mode_select).pause(1).click().perform()

    mix_n_match_option = driver.wait_for_xpath('''//li[@data-value="Mix 'n Match"]''')
    driver.scroll_to_element_and_click(mix_n_match_option)

    u_band_option = driver.wait_for_xpath('//input[@id="root_observation_choices_0"]')

    driver.scroll_to_element_and_click(u_band_option)

    ifu_option = driver.wait_for_xpath('//input[@id="root_observation_choices_4"]')

    driver.scroll_to_element_and_click(ifu_option)
    driver.scroll_to_element_and_click(submit_button)

    driver.wait_for_xpath(
        '//table[contains(@data-testid, "followupRequestTable")]//td[contains(., "Mix \'n Match")]'
    )
    driver.wait_for_xpath(
        '''//table[contains(@data-testid, "followupRequestTable")]//td[contains(., "u,IFU")]'''
    )
    driver.wait_for_xpath(
        '''//table[contains(@data-testid, "followupRequestTable")]//td[contains(., "1")]'''
    )
    driver.wait_for_xpath(
        '''//table[contains(@data-testid, "followupRequestTable")]//td[contains(., "submitted")]'''
    )


def add_followup_request_using_frontend_and_verify_IOO(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    """Adds a new followup request and makes sure it renders properly."""

    idata = add_telescope_and_instrument("IOO", super_admin_token)
    add_allocation(idata['id'], public_group.id, super_admin_token)

    driver.get(f"/become_user/{super_admin_user.id}")

    driver.get(f"/source/{public_source.id}")
    # wait for the plots to load
    driver.wait_for_xpath('//div[@class="bk-root"]//span[text()="Flux"]', timeout=20)
    # this waits for the spectroscopy plot by looking for the element Mg
    driver.wait_for_xpath('//div[@class="bk-root"]//label[text()="Mg"]', timeout=20)

    submit_button = driver.wait_for_xpath(
        '//form[@class="rjsf"]//button[@type="submit"]'
    )

    select_box = driver.find_element_by_id(
        "mui-component-select-followupRequestAllocationSelect"
    )
    select_box.click()

    driver.wait_for_xpath('//li[@data-value="1"]')
    for ii in range(1, 10):
        allocation = driver.wait_for_xpath('//li[@data-value="%d"]' % ii)
        if "IOO" in allocation.text:
            allocation.click()
            break

    photometric_option = driver.wait_for_xpath('//input[@id="root_photometric"]')
    driver.scroll_to_element_and_click(photometric_option)

    mode_select = driver.wait_for_xpath('//div[@id="root_exposure_type"]')
    driver.scroll_to_element(mode_select)

    mode_select = driver.wait_for_xpath('//div[@id="root_observation_type"]')
    driver.scroll_to_element(mode_select)
    ActionChains(driver).move_to_element(mode_select).pause(1).click().perform()

    gri_option = driver.wait_for_xpath('''//li[@data-value="gri"]''')
    driver.scroll_to_element_and_click(gri_option)

    mode_select = driver.wait_for_xpath('//div[@id="root_exposure_type"]')
    driver.scroll_to_element(mode_select)
    ActionChains(driver).move_to_element(mode_select).pause(1).click().perform()

    exp_option = driver.wait_for_xpath('''//li[@data-value="2x150s"]''')
    driver.scroll_to_element_and_click(exp_option)

    proposal_option = driver.wait_for_xpath('//input[@id="root_LT_proposalID"]')
    proposal_option.send_keys('GrowthTest')

    driver.scroll_to_element_and_click(submit_button)

    driver.wait_for_xpath(
        '//table[contains(@data-testid, "followupRequestTable")]//td[contains(., "gri")]'
    )
    driver.wait_for_xpath(
        '''//table[contains(@data-testid, "followupRequestTable")]//td[contains(., "2x150s")]'''
    )
    driver.wait_for_xpath(
        '''//table[contains(@data-testid, "followupRequestTable")]//td[contains(., "GrowthTest")]'''
    )
    driver.wait_for_xpath(
        '''//table[contains(@data-testid, "followupRequestTable")]//td[contains(., "submission")]'''
    )


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not sedm_isonline, reason="SEDM server down")
def test_submit_new_followup_request_SEDM(
    driver, super_admin_user, public_source, super_admin_token, public_group
):

    add_followup_request_using_frontend_and_verify_SEDM(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )


# @pytest.mark.flaky(reruns=2)
def test_submit_new_followup_request_IOO(
    driver, super_admin_user, public_source, super_admin_token, public_group
):

    add_followup_request_using_frontend_and_verify_IOO(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not sedm_isonline, reason="SEDM server down")
def test_edit_existing_followup_request(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_SEDM(
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
        '//div[@role="dialog"]//form[@class="rjsf"]//button[@type="submit"]'
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


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not sedm_isonline, reason='SEDM server down')
def test_delete_followup_request_SEDM(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_SEDM(
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


@pytest.mark.flaky(reruns=2)
@pytest.mark.skipif(not sedm_isonline, reason="SEDM server down")
def test_submit_new_followup_request_two_groups(
    driver,
    super_admin_user,
    public_source_two_groups,
    super_admin_token,
    public_group,
    public_group2,
    view_only_token_group2,
    user_group2,
):

    idata = add_telescope_and_instrument("SEDM", super_admin_token)
    add_allocation(idata['id'], public_group.id, super_admin_token)

    driver.get(f"/become_user/{super_admin_user.id}")

    driver.get(f"/source/{public_source_two_groups.id}")
    # wait for the plots to load
    driver.wait_for_xpath('//div[@class="bk-root"]//span[text()="Flux"]', timeout=20)
    # this waits for the spectroscopy plot by looking for the element Mg
    driver.wait_for_xpath('//div[@class="bk-root"]//label[text()="Mg"]', timeout=20)

    submit_button = driver.wait_for_xpath(
        '//form[@class="rjsf"]//button[@type="submit"]'
    )

    group_select = driver.wait_for_xpath('//*[@id="selectGroups"]')
    driver.scroll_to_element_and_click(group_select)

    group1 = driver.wait_for_xpath(f'//*[@data-testid="group_{public_group.id}"]')
    driver.scroll_to_element_and_click(group1)

    group2 = driver.wait_for_xpath(f'//*[@data-testid="group_{public_group2.id}"]')
    driver.scroll_to_element_and_click(group2)

    body = driver.wait_for_xpath('//body')
    driver.scroll_to_element_and_click(body)

    mode_select = driver.wait_for_xpath('//*[@id="root_observation_type"]')
    driver.scroll_to_element(mode_select)
    ActionChains(driver).move_to_element(mode_select).pause(1).click().perform()

    mix_n_match_option = driver.wait_for_xpath('''//li[@data-value="Mix 'n Match"]''')
    driver.scroll_to_element_and_click(mix_n_match_option)

    u_band_option = driver.wait_for_xpath('//input[@id="root_observation_choices_0"]')

    driver.scroll_to_element_and_click(u_band_option)

    ifu_option = driver.wait_for_xpath('//input[@id="root_observation_choices_4"]')

    driver.scroll_to_element_and_click(ifu_option)

    driver.scroll_to_element_and_click(submit_button)

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

    filename = glob.glob(
        f'{os.path.dirname(__file__)}/../data/ZTF20abwdwoa_20200902_P60_v1.ascii'
    )[0]
    with open(filename, 'r') as f:
        ascii = f.read()

    status, data = api(
        'GET', f'sources/{public_source_two_groups.id}', token=super_admin_token
    )

    assert status == 200
    assert data['status'] == 'success'

    status, data = api(
        "POST",
        'spectrum/ascii',
        data={
            'obj_id': str(public_source_two_groups.id),
            'observed_at': '2020-01-01T00:00:00',
            'instrument_id': idata['id'],
            'fluxerr_column': 2,
            'followup_request_id': data['data']['followup_requests'][0]['id'],
            'ascii': ascii,
            'filename': os.path.basename(filename),
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data['status'] == 'success'

    sid = data['data']['id']
    status, data = api('GET', f'spectrum/{sid}', token=view_only_token_group2)

    assert status == 200
    assert data['status'] == 'success'


@pytest.mark.flaky(reruns=2)
def test_delete_followup_request_IOO(
    driver, super_admin_user, public_source, super_admin_token, public_group
):
    add_followup_request_using_frontend_and_verify_IOO(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )

    delete_button = driver.wait_for_xpath(f'//button[contains(@name, "deleteRequest")]')
    driver.scroll_to_element_and_click(delete_button)
    driver.refresh()

    driver.wait_for_xpath_to_disappear(
        '''//table[contains(@data-testid, "followupRequestTable")]//td[contains(., "2x150s")]'''
    )
    driver.wait_for_xpath_to_disappear(
        '''//table[contains(@data-testid, "followupRequestTable")]//td[contains(., "gri")]'''
    )
    driver.wait_for_xpath_to_disappear(
        '''//table[contains(@data-testid, "followupRequestTable")]//td[contains(., "submission")]'''
    )
