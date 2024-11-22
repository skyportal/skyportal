import pytest
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys


@pytest.mark.flaky(reruns=2)
def test_upload_photometry_csv(
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
    driver.click_xpath('//*[@aria-labelledby="instrumentSelectLabel"]')
    driver.click_xpath(f'//li[@data-value="{inst_id}"]', scroll_parent=True)

    # Click somewhere outside to remove focus from instrument select
    header = driver.wait_for_xpath("//header")
    ActionChains(driver).move_to_element(header).click().perform()

    # group select
    driver.click_xpath('//div[@id="selectGroups"]')
    driver.click_xpath(f'//li[@data-value="{public_group.id}"]', scroll_parent=True)

    # Click somewhere outside to remove focus from group select
    header = driver.wait_for_xpath("//header")
    ActionChains(driver).move_to_element(header).click().perform()

    driver.click_xpath('//*[text()="Preview in Tabular Form"]')
    driver.wait_for_xpath('//div[text()="58001"]')
    driver.click_xpath('//*[text()="Upload Photometry"]', scroll_parent=True)
    driver.wait_for_xpath('//*[contains(.,"Upload successful. Your upload ID is")]')


@pytest.mark.flaky(reruns=2)
def test_upload_photometry_csv_multiple_groups(
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
    driver.click_xpath('//*[@aria-labelledby="instrumentSelectLabel"]')
    driver.click_xpath(f'//li[@data-value="{inst_id}"]', scroll_parent=True)

    # Click somewhere outside to remove focus from instrument select
    header = driver.wait_for_xpath("//header")
    ActionChains(driver).move_to_element(header).click().perform()

    # group select
    driver.click_xpath('//div[@id="selectGroups"]')
    driver.click_xpath(f'//li[@data-value="{public_group.id}"]', scroll_parent=True)
    driver.click_xpath(f'//li[@data-value="{public_group2.id}"]', scroll_parent=True)

    # Click somewhere outside to remove focus from group select
    header = driver.wait_for_xpath("//header")
    ActionChains(driver).move_to_element(header).click().perform()

    driver.click_xpath('//*[text()="Preview in Tabular Form"]')
    driver.wait_for_xpath('//div[text()="58001"]')
    driver.click_xpath('//*[text()="Upload Photometry"]')
    driver.wait_for_xpath('//*[contains(.,"Upload successful. Your upload ID is")]')


@pytest.mark.flaky(reruns=2)
def test_upload_photometry_csv_with_altdata(
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
    driver.click_xpath('//*[@aria-labelledby="instrumentSelectLabel"]')
    driver.click_xpath(f'//li[@data-value="{inst_id}"]', scroll_parent=True)

    # Click somewhere outside to remove focus from instrument select
    header = driver.wait_for_xpath("//header")
    ActionChains(driver).move_to_element(header).click().perform()

    # group select
    driver.click_xpath('//div[@id="selectGroups"]')
    driver.click_xpath(f'//li[@data-value="{public_group.id}"]', scroll_parent=True)

    # Click somewhere outside to remove focus from group select
    header = driver.wait_for_xpath("//header")
    ActionChains(driver).move_to_element(header).click().perform()

    driver.click_xpath('//*[text()="Preview in Tabular Form"]')
    driver.wait_for_xpath('//div[text()="58001"]')
    driver.click_xpath('//*[text()="Upload Photometry"]')
    driver.wait_for_xpath('//*[contains(.,"Upload successful. Your upload ID is")]')


@pytest.mark.flaky(reruns=2)
def test_upload_photometry_csv_form_validation(
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
    driver.click_xpath('//*[@aria-labelledby="instrumentSelectLabel"]')
    driver.click_xpath(f'//li[@data-value="{inst_id}"]', scroll_parent=True)

    # Click somewhere outside to remove focus from instrument select
    header = driver.wait_for_xpath("//header")
    ActionChains(driver).move_to_element(header).click().perform()

    # group select
    driver.click_xpath('//div[@id="selectGroups"]')
    driver.click_xpath(f'//li[@data-value="{public_group.id}"]', scroll_parent=True)

    driver.click_xpath('//*[text()="Preview in Tabular Form"]')
    driver.wait_for_xpath('//div[text()="58001"]')


@pytest.mark.flaky(reruns=2)
def test_upload_photometry_form(driver, sedm, super_admin_user, public_source):
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/upload_photometry/{public_source.id}")

    button = driver.wait_for_xpath('//*[contains(text(), "Using Form (one)")]')
    button.click()

    # instrument select
    driver.click_xpath('//*[@aria-labelledby="instrumentSelectLabel"]')
    driver.click_xpath(f'//li[@data-value="{sedm.id}"]', scroll_parent=True)
    # wait for the modal to disappear
    driver.wait_for_xpath_to_disappear(f'//li[@data-value="{sedm.id}"]')

    groups_dropdown = driver.wait_for_xpath('//*[@id="root_group_ids"]')
    driver.scroll_to_element_and_click(groups_dropdown)
    # click on the first group
    driver.wait_for_xpath('//*[@aria-labelledby="root_group_ids-label"]/li[1]').click()
    groups_dropdown.send_keys(Keys.ESCAPE)

    driver.wait_for_xpath_to_disappear(
        '//*[@aria-labelledby="root_group_ids-label"]/li[1]'
    )

    driver.wait_for_xpath('//*[@id="root_obsdate"]').send_keys("2017-05-09T12:34:56")
    driver.wait_for_xpath('//*[@id="root_mag"]').send_keys("12.3")
    driver.wait_for_xpath('//*[@id="root_magerr"]').send_keys("0.1")
    driver.wait_for_xpath('//*[@id="root_limiting_mag"]').send_keys("20.0")

    driver.wait_for_xpath('//*[@id="root_origin"]').send_keys("test")
    driver.wait_for_xpath('//*[@id="root_nb_exposure"]').send_keys("6")
    driver.wait_for_xpath('//*[@id="root_exposure_time"]').send_keys("60")

    coordinates_option = driver.wait_for_xpath('//*[@id="root_coordinates"]')
    driver.scroll_to_element_and_click(coordinates_option)
    driver.wait_for_xpath('//*[@id="root_ra"]').send_keys("10.625")
    driver.wait_for_xpath('//*[@id="root_dec"]').send_keys("41.2")

    filter_dropdown = driver.wait_for_xpath('//*[@id="root_filter"]')
    driver.scroll_to_element_and_click(filter_dropdown)
    driver.wait_for_xpath('//*[text()="sdssg"]').click()

    submit = driver.wait_for_xpath('//*[text()="Submit"]')
    driver.scroll_to_element_and_click(submit)

    driver.wait_for_xpath('//*[contains(text(), "Photometry added successfully")]')
