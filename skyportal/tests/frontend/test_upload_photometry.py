import pytest
from selenium.common.exceptions import ElementClickInterceptedException

from skyportal.tests import api

from .test_followup_requests import add_telescope_and_instrument


@pytest.mark.flaky(reruns=2)
def test_upload_photometry(
    driver, super_admin_user, public_group, public_source, super_admin_token
):
    data = add_telescope_and_instrument(
        "P60 Camera", [public_group.id], super_admin_token
    )
    inst_id = data["id"]
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/upload_photometry/{public_source.id}")
    csv_text_input = driver.wait_for_xpath('//textarea[@name="csvData"]')
    csv_text_input.send_keys(
        "mjd,flux,fluxerr,zp,magsys,filter\n"
        "58001,55,1,25,ab,ztfg\n"
        "58002,53,1,25,ab,ztfg"
    )
    driver.wait_for_xpath('//*[@id="mui-component-select-instrumentID"]').click()
    driver.wait_for_xpath_to_be_clickable(
        f'//span[text()="P60 Camera (ID: {inst_id})"]'
    ).click()
    try:
        driver.wait_for_xpath_to_be_clickable('//div[@id="selectGroups"]').click()
    except ElementClickInterceptedException:
        try:
            driver.wait_for_xpath_to_be_clickable('//div[@id="selectGroups"]').click()
        except ElementClickInterceptedException:
            raise
    driver.wait_for_xpath_to_be_clickable(f'//li[text()="{public_group.name}"]').click()
    driver.execute_script(
        "arguments[0].click();",
        driver.wait_for_xpath('//*[text()="Preview in Tabular Form"]')
    )
    driver.wait_for_xpath('//div[text()="58001"]')
    driver.execute_script(
        "arguments[0].click();", driver.wait_for_xpath('//*[text()="Upload Photometry"]')
    )
    driver.wait_for_xpath(
        '//*[contains(.,"Upload successful. Your upload ID is")]'
    )


@pytest.mark.flaky(reruns=2)
def test_upload_photometry_multiple_groups(
    driver,
    super_admin_user_two_groups,
    public_group,
    public_group2,
    public_source_two_groups,
    super_admin_token,
):
    user = super_admin_user_two_groups
    public_source = public_source_two_groups
    data = add_telescope_and_instrument(
        "P60 Camera", [public_group.id], super_admin_token
    )
    inst_id = data["id"]
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/upload_photometry/{public_source.id}")
    csv_text_input = driver.wait_for_xpath('//textarea[@name="csvData"]')
    csv_text_input.send_keys(
        "mjd,flux,fluxerr,zp,magsys,filter\n"
        "58001,55,1,25,ab,ztfg\n"
        "58002,53,1,25,ab,ztfg"
    )
    driver.wait_for_xpath('//*[@id="mui-component-select-instrumentID"]').click()
    driver.wait_for_xpath(f'//span[text()="P60 Camera (ID: {inst_id})"]').click()
    try:
        driver.wait_for_xpath_to_be_clickable('//div[@id="selectGroups"]').click()
    except ElementClickInterceptedException:
        try:
            driver.wait_for_xpath_to_be_clickable('//div[@id="selectGroups"]').click()
        except ElementClickInterceptedException:
            raise
    driver.wait_for_xpath_to_be_clickable(f'//li[text()="{public_group.name}"]').click()
    driver.wait_for_xpath_to_be_clickable(
        f'//li[text()="{public_group2.name}"]'
    ).click()
    driver.execute_script(
        "arguments[0].click();",
        driver.wait_for_xpath('//*[text()="Preview in Tabular Form"]')
    )
    driver.wait_for_xpath('//div[text()="58001"]')
    driver.execute_script(
        "arguments[0].click();", driver.wait_for_xpath('//*[text()="Upload Photometry"]')
    )
    driver.wait_for_xpath(
        '//*[contains(.,"Upload successful. Your upload ID is")]'
    )


@pytest.mark.flaky(reruns=2)
def test_upload_photometry_with_altdata(
    driver, super_admin_user, public_group, public_source, super_admin_token
):
    data = add_telescope_and_instrument(
        "P60 Camera", [public_group.id], super_admin_token
    )
    inst_id = data["id"]
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/upload_photometry/{public_source.id}")
    csv_text_input = driver.wait_for_xpath('//textarea[@name="csvData"]')
    csv_text_input.send_keys(
        "mjd,flux,fluxerr,zp,magsys,filter,altdata.meta1,altdata.meta2\n"
        "58001,55,1,25,ab,ztfg,44.4,\"abc,abc\"\n"
        "58002,53,1,25,ab,ztfg,44.2,\"edf,edf\""
    )
    driver.wait_for_xpath('//*[@id="mui-component-select-instrumentID"]').click()
    driver.wait_for_xpath(f'//span[text()="P60 Camera (ID: {inst_id})"]').click()
    try:
        driver.wait_for_xpath_to_be_clickable('//div[@id="selectGroups"]').click()
    except ElementClickInterceptedException:
        try:
            driver.wait_for_xpath_to_be_clickable('//div[@id="selectGroups"]').click()
        except ElementClickInterceptedException:
            raise
    driver.wait_for_xpath_to_be_clickable(f'//li[text()="{public_group.name}"]').click()
    driver.execute_script(
        "arguments[0].click();",
        driver.wait_for_xpath('//*[text()="Preview in Tabular Form"]')
    )
    driver.wait_for_xpath('//div[text()="58001"]')
    driver.execute_script(
        "arguments[0].click();", driver.wait_for_xpath('//*[text()="Upload Photometry"]')
    )
    driver.wait_for_xpath(
        '//*[contains(.,"Upload successful. Your upload ID is")]'
    )


@pytest.mark.flaky(reruns=2)
def test_upload_photometry_form_validation(
    driver, super_admin_user, public_group, public_source, super_admin_token
):
    data = add_telescope_and_instrument(
        "P60 Camera", [public_group.id], super_admin_token
    )
    inst_id = data["id"]
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/upload_photometry/{public_source.id}")
    csv_text_input = driver.wait_for_xpath('//textarea[@name="csvData"]')
    csv_text_input.send_keys(
        "mjd,flux,fluxerr,zp,magsys,OTHER\n"
        "58001,55,1,25,ab,ztfg\n"
        "58002,53,1,25,ab,ztfg"
    )
    driver.wait_for_xpath('//*[text()="Preview in Tabular Form"]').click()
    driver.wait_for_xpath(
        '//div[contains(.,"Invalid input: Missing required column: filter")]'
    )
    csv_text_input.clear()
    csv_text_input.send_keys(
        "mjd,flux,fluxerr,zp,magsys,filter\n"
        "58001,55,1,25,ab,ztfg\n"
        "58002,53,1,25,ab"
    )
    driver.wait_for_xpath(
        '//div[contains(.,"Invalid input: All data rows must have the same number of columns as header row")]'
    )
    csv_text_input.clear()
    csv_text_input.send_keys("mjd,flux,fluxerr,zp,magsys,filter")
    driver.wait_for_xpath(
        '//div[contains(.,"Invalid input: There must be a header row and one or more data rows")]'
    )
    csv_text_input.clear()
    csv_text_input.send_keys(
        "mjd,flux,fluxerr,zp,magsys,filter\n"
        "58001,55,1,25,ab,ztfg\n"
        "58002,53,1,25,ab,ztfg"
    )
    driver.wait_for_xpath('//div[contains(.,"Select an instrument")]')
    driver.wait_for_xpath('//*[@id="mui-component-select-instrumentID"]').click()
    driver.wait_for_xpath(f'//span[text()="P60 Camera (ID: {inst_id})"]').click()
    driver.wait_for_xpath('//div[contains(.,"Select at least one group")]')
    try:
        driver.wait_for_xpath_to_be_clickable('//div[@id="selectGroups"]').click()
    except ElementClickInterceptedException:
        try:
            driver.wait_for_xpath_to_be_clickable('//div[@id="selectGroups"]').click()
        except ElementClickInterceptedException:
            raise
    driver.wait_for_xpath_to_be_clickable(f'//li[text()="{public_group.name}"]').click()
    driver.execute_script(
        "arguments[0].click();",
        driver.wait_for_xpath('//*[text()="Preview in Tabular Form"]')
    )
    driver.wait_for_xpath('//div[text()="58001"]')
