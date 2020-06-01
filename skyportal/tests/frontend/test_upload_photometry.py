from skyportal.tests import api

from .test_followup_requests import add_telescope_and_instrument


def test_upload_photometry(
    driver, user, public_group, public_source, super_admin_token
):
    add_telescope_and_instrument("P60 Camera", [public_group.id], super_admin_token)
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/upload_photometry/{public_source.id}")
    csv_text_input = driver.wait_for_xpath('//textarea[@name="csvData"]')
    csv_text_input.send_keys(
        "mjd,flux,fluxerr,zp,magsys,filter\n"
        "58001,55,1,25,ab,ztfg\n"
        "58002,53,1,25,ab,ztfg"
    )
    driver.wait_for_xpath('//*[@id="mui-component-select-instrumentID"]').click()
    driver.wait_for_xpath('//li[text()="P60 Camera"]').click()
    driver.wait_for_xpath('//*[text()="Preview in Tabular Form"]').click()
    driver.wait_for_xpath('//td[text()="58001"]')
    driver.wait_for_xpath('//*[text()="Upload Photometry"]').click()
    driver.wait_for_xpath(
        '//*[contains(.,"Upload successful. Your bulk upload ID is")]'
    )


def test_upload_photometry_form_validation(
    driver, user, public_group, public_source, super_admin_token
):
    add_telescope_and_instrument("P60 Camera", [public_group.id], super_admin_token)
    driver.get(f"/become_user/{user.id}")
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
    driver.wait_for_xpath('//li[text()="P60 Camera"]').click()
    driver.wait_for_xpath('//*[text()="Preview in Tabular Form"]').click()
    driver.wait_for_xpath('//td[text()="58001"]')
