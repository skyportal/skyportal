import uuid
import pytest
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from skyportal.tests import api


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
            "api_classname": "%sAPI" % instrument_name,
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

    idata = add_telescope_and_instrument("IOO", super_admin_token)
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

    select_box = driver.find_element_by_id(
        "mui-component-select-followupRequestAllocationSelect"
    )
    select_box.click()
    select_box = driver.find_element_by_id("menu-followupRequestAllocationSelect")

    allocations = select_box.find_elements_by_class_name("MuiButtonBase-root")
    for allocation in allocations:
        if "IOO" in allocation.text:
            allocation.click()
            break

    photometric_option = driver.wait_for_xpath('//input[@id="root_photometric"]')
    driver.scroll_to_element_and_click(photometric_option)

    mode_select = driver.wait_for_xpath('//div[@id="root_observation_type"]')
    ActionChains(driver).move_to_element(mode_select).pause(1).click().perform()

    gri_option = driver.wait_for_xpath('''//li[@data-value="gri"]''')
    driver.scroll_to_element_and_click(gri_option)

    mode_select = driver.wait_for_xpath('//div[@id="root_exposure_type"]')
    ActionChains(driver).move_to_element(mode_select).pause(1).click().perform()

    exp_option = driver.wait_for_xpath('''//li[@data-value="2x150s"]''')
    driver.scroll_to_element_and_click(exp_option)

    proposal_option = driver.wait_for_xpath('//input[@id="root_LT_proposalID"]')
    proposal_option.send_keys('GrowthTest')
    driver.scroll_to_element_and_click(submit_button)


@pytest.mark.flaky(reruns=2)
def test_submit_new_followup_request(
    driver, super_admin_user, public_source, super_admin_token, public_group
):

    add_followup_request_using_frontend_and_verify(
        driver, super_admin_user, public_source, super_admin_token, public_group
    )
