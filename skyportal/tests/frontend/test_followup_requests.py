import uuid
import time
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import ElementClickInterceptedException

from skyportal.tests import api


def add_telescope_and_instrument(instrument_name, group_ids, token):
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
            "group_ids": group_ids,
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
            "type": "type",
            "band": "Optical",
            "telescope_id": telescope_id,
            "filters": ["ztfg"]
        },
        token=token,
    )
    assert status == 200
    assert data["status"] == "success"
    return data


def test_submit_new_followup_request(
    driver, user, public_source, public_group, super_admin_token
):
    add_telescope_and_instrument("P60 Camera", [public_group.id], super_admin_token)
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    instrument_select_element = driver.wait_for_xpath('//select[@name="instrument_id"]')
    instrument_select = Select(instrument_select_element)
    # Need to wait for plots to render & then scroll down again
    time.sleep(1.5)
    driver.execute_script("arguments[0].scrollIntoView();", instrument_select_element)
    try:
        instrument_select.select_by_visible_text("P60 Camera")
    except ElementClickInterceptedException:
        driver.scroll_to_element_and_click(instrument_select_element)
        instrument_select.select_by_visible_text("P60 Camera")

    submit_button = driver.wait_for_xpath(
        '//*[@name="createNewFollowupRequestSubmitButton"]')
    driver.execute_script("arguments[0].scrollIntoView();", submit_button)
    driver.scroll_to_element_and_click(
        driver.wait_for_xpath('//input[@name="start_date"]')
    )
    driver.scroll_to_element_and_click(
        driver.wait_for_xpath(
            '//div[contains(@class,"react-datepicker__day react-datepicker__day--013")]'
        )
    )
    driver.scroll_to_element_and_click(
        driver.wait_for_xpath('//input[@name="end_date"]')
    )
    driver.scroll_to_element_and_click(
        driver.wait_for_xpath(
            '//div[contains(@class,"react-datepicker__day react-datepicker__day--014")]'
        )
    )
    driver.wait_for_xpath('//input[@value="sdssu"]').click()
    exposure_select = Select(driver.wait_for_xpath('//select[@name="exposure_time"]'))
    exposure_select.select_by_visible_text("120s")
    priority_select = Select(driver.wait_for_xpath('//select[@name="priority"]'))
    priority_select.select_by_visible_text("1")
    driver.scroll_to_element_and_click(submit_button)
    driver.wait_for_xpath("//td[contains(.,'P60 Camera')]")
    driver.wait_for_xpath("//td[contains(.,'pending')]")
    driver.wait_for_xpath("//td[contains(.,'1')]")


def test_edit_existing_followup_request(
    driver, user, public_source, public_group, super_admin_token
):
    add_telescope_and_instrument("P60 Camera", [public_group.id], super_admin_token)

    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    instrument_select_element = driver.wait_for_xpath('//select[@name="instrument_id"]')
    instrument_select = Select(instrument_select_element)
    # Need to wait for plots to render & then scroll down again
    time.sleep(1.5)
    driver.execute_script("arguments[0].scrollIntoView();", instrument_select_element)
    try:
        instrument_select.select_by_visible_text("P60 Camera")
    except:
        driver.execute_script("arguments[0].scrollIntoView();", instrument_select_element)
        instrument_select.select_by_visible_text("P60 Camera")

    submit_button = driver.wait_for_xpath(
        '//*[@name="createNewFollowupRequestSubmitButton"]')
    driver.execute_script("arguments[0].scrollIntoView();", submit_button)
    driver.scroll_to_element_and_click(
        driver.wait_for_xpath('//input[@name="start_date"]')
    )
    driver.scroll_to_element_and_click(
        driver.wait_for_xpath(
            '//div[contains(@class,"react-datepicker__day react-datepicker__day--013")]'
        )
    )
    driver.scroll_to_element_and_click(
        driver.wait_for_xpath('//input[@name="end_date"]')
    )
    driver.scroll_to_element_and_click(
        driver.wait_for_xpath(
            '//div[contains(@class,"react-datepicker__day react-datepicker__day--014")]'
        )
    )
    driver.wait_for_xpath('//input[@value="sdssu"]').click()
    exposure_select = Select(driver.wait_for_xpath('//select[@name="exposure_time"]'))
    exposure_select.select_by_visible_text("120s")
    priority_select = Select(driver.wait_for_xpath('//select[@name="priority"]'))
    priority_select.select_by_visible_text("1")
    submit_button.click()
    driver.wait_for_xpath("//td[contains(.,'1')]")
    driver.scroll_to_element_and_click(driver.wait_for_xpath('//button[text()="Edit"]'))
    priority_select = Select(driver.wait_for_xpath('//select[@name="priority"]'))
    priority_select.select_by_visible_text("5")
    submit_button = driver.wait_for_xpath(
        '//*[@name="editExistingFollowupRequestSubmitButton"]')
    driver.execute_script("arguments[0].click();", submit_button)
    try:
        driver.wait_for_xpath("//td[contains(.,'5')]")
    except:
        driver.refresh()
        driver.wait_for_xpath("//td[contains(.,'5')]")


def test_delete_followup_request(
    driver, user, public_source, public_group, super_admin_token
):
    add_telescope_and_instrument("P60 Camera", [public_group.id], super_admin_token)

    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    instrument_select_element = driver.wait_for_xpath('//select[@name="instrument_id"]')
    instrument_select = Select(instrument_select_element)
    # Need to wait for plots to render & then scroll down again
    time.sleep(1.5)
    driver.execute_script("arguments[0].scrollIntoView();", instrument_select_element)
    try:
        instrument_select.select_by_visible_text("P60 Camera")
    except:
        driver.execute_script("arguments[0].scrollIntoView();", instrument_select_element)
        instrument_select.select_by_visible_text("P60 Camera")

    submit_button = driver.wait_for_xpath(
        '//*[@name="createNewFollowupRequestSubmitButton"]')
    driver.execute_script("arguments[0].scrollIntoView();", submit_button)
    driver.scroll_to_element_and_click(
        driver.wait_for_xpath('//input[@name="start_date"]')
    )
    driver.scroll_to_element_and_click(
        driver.wait_for_xpath(
            '//div[contains(@class,"react-datepicker__day react-datepicker__day--013")]'
        )
    )
    driver.scroll_to_element_and_click(
        driver.wait_for_xpath('//input[@name="end_date"]')
    )
    driver.scroll_to_element_and_click(
        driver.wait_for_xpath(
            '//div[contains(@class,"react-datepicker__day react-datepicker__day--014")]'
        )
    )
    driver.wait_for_xpath('//input[@value="sdssu"]').click()
    exposure_select = Select(driver.wait_for_xpath('//select[@name="exposure_time"]'))
    exposure_select.select_by_visible_text("120s")
    priority_select = Select(driver.wait_for_xpath('//select[@name="priority"]'))
    priority_select.select_by_visible_text("1")
    driver.execute_script("arguments[0].click();", submit_button)
    driver.wait_for_xpath("//td[contains(.,'P60 Camera')]")
    driver.wait_for_xpath("//td[contains(.,'pending')]")
    driver.wait_for_xpath("//td[contains(.,'1')]")
    driver.scroll_to_element_and_click(
        driver.wait_for_xpath('//button[text()="Delete"]')
    )
    driver.wait_for_xpath_to_disappear('//button[text()="Delete"]')


def test_cannot_edit_uneditable_followup_request(
    driver, user, public_source, public_group, super_admin_token
):
    add_telescope_and_instrument("ALFOSC", [public_group.id], super_admin_token)

    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    instrument_select_element = driver.wait_for_xpath('//select[@name="instrument_id"]')
    instrument_select = Select(instrument_select_element)
    # Need to wait for plots to render & then scroll down again
    time.sleep(1.5)
    driver.execute_script("arguments[0].scrollIntoView();", instrument_select_element)
    try:
        instrument_select.select_by_visible_text("ALFOSC")
    except:
        driver.execute_script("arguments[0].scrollIntoView();", instrument_select_element)
        instrument_select.select_by_visible_text("ALFOSC")

    submit_button = driver.wait_for_xpath(
        '//*[@name="createNewFollowupRequestSubmitButton"]')
    driver.execute_script("arguments[0].scrollIntoView();", submit_button)
    driver.wait_for_xpath(
        '//*[contains(.,"WARNING: You will not be able to edit or delete this request once submitted.")]'
    )
    driver.scroll_to_element_and_click(
        driver.wait_for_xpath('//input[@name="start_date"]')
    )
    driver.scroll_to_element_and_click(
        driver.wait_for_xpath(
            '//div[contains(@class,"react-datepicker__day react-datepicker__day--013")]'
        )
    )
    driver.scroll_to_element_and_click(
        driver.wait_for_xpath('//input[@name="end_date"]')
    )
    driver.scroll_to_element_and_click(
        driver.wait_for_xpath(
            '//div[contains(@class,"react-datepicker__day react-datepicker__day--014")]'
        )
    )
    filter_select = Select(driver.wait_for_xpath('//select[@name="filters"]'))
    filter_select.select_by_visible_text("sdssu")
    priority_select = Select(driver.wait_for_xpath('//select[@name="priority"]'))
    priority_select.select_by_visible_text("1")
    driver.execute_script("arguments[0].click();", submit_button)
    driver.wait_for_xpath("//td[contains(.,'1')]")
    driver.wait_for_xpath_to_disappear('//button[text()="Edit"]')
