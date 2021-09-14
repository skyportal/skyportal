import os


def test_upload_spectroscopy(
    driver, sedm, super_admin_user, public_source, super_admin_token
):
    inst_id = sedm.id
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/upload_spectrum/{public_source.id}")

    filename = "ZTF20abucjsa_20200909_LT_v1.ascii"

    attachment_file = driver.wait_for_xpath('//input[@type="file"]')
    attachment_file.send_keys(
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'data',
            filename,
        ),
    )

    driver.wait_for_xpath(f'//*[contains(., "{filename}")]')

    mjd_element = driver.wait_for_xpath('//*[@id="root_mjd"]')
    driver.scroll_to_element_and_click(mjd_element)
    mjd_element.send_keys('51232.')

    instrument_id_element_xpath = '//*[@id="root_instrument_id"]'
    driver.click_xpath(instrument_id_element_xpath)

    sedm_element_xpath = f'//li[@data-value="{inst_id}"]'
    driver.click_xpath(sedm_element_xpath, scroll_parent=True)

    preview_button_xpath = '//button[contains(.,"Preview")]'
    driver.click_xpath(preview_button_xpath)

    submit_button_xpath = '//button[contains(.,"Upload Spectrum")]'
    driver.click_xpath(submit_button_xpath)

    driver.wait_for_xpath('//*[contains(.,"successful")]')

    # Go to "Manage Data" page to look for the spectrum, since we can't easily
    #  look into the Bokeh <canvas> tag on the Source page.
    driver.get(f"/manage_data/{public_source.id}")

    driver.wait_for_xpath(f'//*[contains(.,"{sedm.name}")]', 20)
