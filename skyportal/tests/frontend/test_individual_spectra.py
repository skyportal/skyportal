import uuid

from selenium.common.exceptions import TimeoutException

from skyportal.tests import api


def enter_comment_text(driver, comment_text):
    comment_xpath = "//div[contains(@data-testid, 'individual-spectrum-id_')]//textarea[@name='text']"
    comment_box = driver.wait_for_xpath(comment_xpath)
    driver.click_xpath(comment_xpath)
    comment_box.send_keys(comment_text)


def add_comment(driver, comment_text):
    enter_comment_text(driver, comment_text)
    driver.click_xpath(
        "//div[contains(@data-testid, 'individual-spectrum-id_')]//*[@name='submitCommentButton']"
    )


def add_comment_and_wait_for_display(driver, comment_text):
    add_comment(driver, comment_text)

    try:
        driver.wait_for_xpath(f'//*[contains(text(), "{comment_text}")]', timeout=20)
    except TimeoutException:
        driver.refresh()
        driver.wait_for_xpath(f'//*[contains(text(), "{comment_text}")]', timeout=20)


def test_comments(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")

    comment_text = str(uuid.uuid4())

    # now test the Share data page
    driver.get(f"/share_data/{public_source.id}")

    # little triangle you push to expand the table
    driver.click_xpath("//*[@id='expandable-button']")

    add_comment_and_wait_for_display(driver, comment_text)

    # Make sure individual spectra comments appear on the Source page
    driver.get(f"/source/{public_source.id}")

    driver.wait_for_xpath(f'//p[contains(text(), "{comment_text}")]')


def test_annotations(
    driver, user, annotation_token, upload_data_token, public_source, lris
):
    driver.get(f"/become_user/{user.id}")
    annotation_data = str(uuid.uuid4())

    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': str(public_source.id),
            'observed_at': '2021-11-02 12:00:00',
            'instrument_id': lris.id,
            'wavelengths': [664, 665, 666],
            'fluxes': [234.2, 232.1, 235.3],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    spectrum_id = data["data"]["id"]

    status, data = api(
        'POST',
        f'spectra/{spectrum_id}/annotations',
        data={
            'origin': 'kowalski',
            'data': {'useful_info': annotation_data},
        },
        token=annotation_token,
    )

    assert status == 200

    # ----> now test the Share data page <----
    driver.get(f"/share_data/{public_source.id}")

    # need to filter out only the new spectrum we've added
    # open the filter menu
    driver.click_xpath(
        "//*[@data-testid='spectrum-div']//button[@data-testid='Filter Table-iconButton']"
    )

    # click the filter on ID button
    driver.click_xpath("//div[@id='mui-component-select-id']", scroll_parent=True)

    # choose the one we've added based on ID
    driver.click_xpath(f"//li[@data-value='{spectrum_id}']", scroll_parent=True)

    # close the filter menu
    driver.click_xpath("//*[contains(@class, 'filterClose')]")

    # push the little triangle to expand the table
    driver.click_xpath("//*[@data-testid='spectrum-div']//*[@id='expandable-button']")
    driver.wait_for_xpath(f'//div[text()="{annotation_data}"]')

    # ----> now go to the source page <----
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath('//div[text()="Spectrum Obs. at"]')

    # filter once more for only this spectrum
    driver.click_xpath(
        "//*[@id='annotations-content']//button[@data-testid='Filter Table-iconButton']"
    )

    # click the filter on ID button
    driver.click_xpath(
        "//div[@id='mui-component-select-observed_at']", scroll_parent=True
    )

    # choose the one we've added based on ID
    driver.click_xpath("//li[@data-value='2021-11-02.5']", scroll_parent=True)

    # close the filter menu
    driver.click_xpath("//*[contains(@class, 'filterClose')]")

    driver.wait_for_xpath('//div[text()="2021-11-02.5"]')
    driver.wait_for_xpath(f'//div[text()="{annotation_data}"]')
