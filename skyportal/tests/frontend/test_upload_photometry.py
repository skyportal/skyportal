import pytest
from selenium.webdriver import ActionChains


# @pytest.mark.flaky(reruns=2)
def test_upload_photometry(
    driver, sedm, super_admin_user, public_source, super_admin_token, public_group
):
    inst_id = sedm.id
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/upload_photometry/{public_source.id}")
    csv_text_input = driver.wait_for_xpath('//textarea[@name="csvData"]')
    csv_text_input.send_keys(
        "mjd,flux,fluxerr,zp,magsys,filter\n"
        "58001,55,1,25,ab,sdssg\n"
        "58002,53,1,25,ab,sdssg"
    )

    # instrument select
    driver.click_xpath('//*[@id="mui-component-select-instrumentID"]')
    driver.click_xpath(f'//li[@data-value="{inst_id}"]', scroll_parent=True)

    # Click somewhere outside to remove focus from instrument select
    header = driver.wait_for_xpath("//header")
    ActionChains(driver).move_to_element(header).click().perform()

    # group select
    driver.click_xpath('//div[@id="selectGroups"]')
    driver.click_xpath(f'//li[text()="{public_group.name}"]', scroll_parent=True)

    driver.click_xpath('//*[text()="Preview in Tabular Form"]')
    driver.wait_for_xpath('//div[text()="58001"]')
    driver.click_xpath('//*[text()="Upload Photometry"]')
    driver.wait_for_xpath('//*[contains(.,"Upload successful. Your upload ID is")]')


@pytest.mark.flaky(reruns=2)
def test_upload_photometry_multiple_groups(
    driver,
    sedm,
    super_admin_user_two_groups,
    public_group,
    public_group2,
    public_source_two_groups,
    super_admin_token,
):
    user = super_admin_user_two_groups
    public_source = public_source_two_groups
    inst_id = sedm.id
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/upload_photometry/{public_source.id}")
    csv_text_input = driver.wait_for_xpath('//textarea[@name="csvData"]')
    csv_text_input.send_keys(
        "mjd,flux,fluxerr,zp,magsys,filter\n"
        "58001,55,1,25,ab,sdssg\n"
        "58002,53,1,25,ab,sdssg"
    )
    # instrument select
    driver.click_xpath('//*[@id="mui-component-select-instrumentID"]')
    driver.click_xpath(f'//li[@data-value="{inst_id}"]', scroll_parent=True)

    # Click somewhere outside to remove focus from instrument select
    header = driver.wait_for_xpath("//header")
    ActionChains(driver).move_to_element(header).click().perform()

    # group select
    driver.click_xpath('//div[@id="selectGroups"]')
    driver.click_xpath(f'//li[text()="{public_group.name}"]', scroll_parent=True)
    driver.click_xpath(f'//li[text()="{public_group2.name}"]', scroll_parent=True)

    driver.click_xpath('//*[text()="Preview in Tabular Form"]')
    driver.wait_for_xpath('//div[text()="58001"]')
    driver.click_xpath('//*[text()="Upload Photometry"]')
    driver.wait_for_xpath('//*[contains(.,"Upload successful. Your upload ID is")]')


@pytest.mark.flaky(reruns=2)
def test_upload_photometry_with_altdata(
    driver, sedm, super_admin_user, public_source, super_admin_token, public_group
):
    inst_id = sedm.id
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/upload_photometry/{public_source.id}")
    csv_text_input = driver.wait_for_xpath('//textarea[@name="csvData"]')
    csv_text_input.send_keys(
        "mjd,flux,fluxerr,zp,magsys,filter,altdata.meta1,altdata.meta2\n"
        "58001,55,1,25,ab,sdssg,44.4,\"abc,abc\"\n"
        "58002,53,1,25,ab,sdssg,44.2,\"edf,edf\""
    )
    # instrument select
    driver.click_xpath('//*[@id="mui-component-select-instrumentID"]')
    driver.click_xpath(f'//li[@data-value="{inst_id}"]', scroll_parent=True)

    # Click somewhere outside to remove focus from instrument select
    header = driver.wait_for_xpath("//header")
    ActionChains(driver).move_to_element(header).click().perform()

    # group select
    driver.click_xpath('//div[@id="selectGroups"]')
    driver.click_xpath(f'//li[text()="{public_group.name}"]', scroll_parent=True)

    driver.click_xpath('//*[text()="Preview in Tabular Form"]')
    driver.wait_for_xpath('//div[text()="58001"]')
    driver.click_xpath('//*[text()="Upload Photometry"]')
    driver.wait_for_xpath('//*[contains(.,"Upload successful. Your upload ID is")]')


@pytest.mark.flaky(reruns=2)
def test_upload_photometry_form_validation(
    driver, sedm, super_admin_user, public_source, super_admin_token, public_group
):
    inst_id = sedm.id
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/upload_photometry/{public_source.id}")
    csv_text_input = driver.wait_for_xpath('//textarea[@name="csvData"]')
    csv_text_input.send_keys(
        "mjd,flux,fluxerr,zp,magsys,OTHER\n"
        "58001,55,1,25,ab,sdssg\n"
        "58002,53,1,25,ab,sdssg"
    )
    driver.wait_for_xpath('//*[text()="Preview in Tabular Form"]').click()
    driver.wait_for_xpath(
        '//div[contains(.,"Invalid input: Missing required column: filter")]'
    )
    csv_text_input.clear()
    csv_text_input.send_keys(
        "mjd,flux,fluxerr,zp,magsys,filter\n"
        "58001,55,1,25,ab,sdssg\n"
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
        "58001,55,1,25,ab,sdssg\n"
        "58002,53,1,25,ab,sdssg"
    )
    driver.wait_for_xpath('//div[contains(.,"Select an instrument")]')

    # instrument select
    driver.click_xpath('//*[@id="mui-component-select-instrumentID"]')
    driver.click_xpath(f'//li[@data-value="{inst_id}"]', scroll_parent=True)

    # Click somewhere outside to remove focus from instrument select
    header = driver.wait_for_xpath("//header")
    ActionChains(driver).move_to_element(header).click().perform()

    driver.wait_for_xpath('//div[contains(.,"Select at least one group")]')

    # group select
    driver.click_xpath('//div[@id="selectGroups"]')
    driver.click_xpath(f'//li[text()="{public_group.name}"]', scroll_parent=True)

    driver.click_xpath('//*[text()="Preview in Tabular Form"]')
    driver.wait_for_xpath('//div[text()="58001"]')
