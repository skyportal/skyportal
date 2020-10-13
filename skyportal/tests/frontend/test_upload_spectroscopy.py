import os


def test_upload_spectroscopy(
    driver, sedm, super_admin_user, public_source, super_admin_token, public_group
):
    inst_id = sedm.id
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/upload_spectrum/{public_source.id}")

    attachment_file = driver.wait_for_xpath('//input[@type="file"]')
    attachment_file.send_keys(
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'data',
            'ZTF20abucjsa_20200909_LT_v1.ascii',
        )
    )

    mjd_element = driver.wait_for_xpath(f'//*[@id="root_mjd"]')
    driver.scroll_to_element_and_click(mjd_element)
    mjd_element.send_keys('51232.')

    instrument_id_element = driver.wait_for_xpath(f'//*[@id="root_instrument_id"]')
    driver.scroll_to_element_and_click(instrument_id_element)

    sedm_element = driver.wait_for_xpath(f'//li[@data-value="{inst_id}"]')
    driver.scroll_to_element_and_click(sedm_element)

    preview_button = driver.wait_for_xpath(f'//button[contains(.,"Preview")]')
    driver.scroll_to_element_and_click(preview_button)

    submit_button = driver.wait_for_xpath(f'//button[contains(.,"Upload Spectrum")]')
    driver.scroll_to_element_and_click(submit_button)

    driver.wait_for_xpath('//*[contains(.,"uccessful")]')

    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//*[contains(.,"{sedm.telescope.nickname}/{sedm.name}")]')
