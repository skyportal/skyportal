import os
import uuid

import pytest
from selenium.common.exceptions import TimeoutException
from io import BytesIO
from PIL import Image, ImageChops

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
        driver.wait_for_xpath(f'//p[text()="{comment_text}"]', timeout=20)
    except TimeoutException:
        driver.refresh()
        driver.wait_for_xpath(f'//p[text()="{comment_text}"]')


@pytest.mark.flaky(reruns=2)
def test_comments(driver, user, public_source):

    driver.get(f"/become_user/{user.id}")

    comment_text = str(uuid.uuid4())

    # now test the Manage Data page
    driver.get(f"/manage_data/{public_source.id}")

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

    # ----> now test the Manage Data page <----
    driver.get(f"/manage_data/{public_source.id}")

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


def test_spectrum_plot(driver, public_source, lris, upload_data_token):
    status, data = api(
        'POST',
        'spectrum',
        data={
            'obj_id': str(public_source.id),
            'observed_at': '2020-01-10T00:00:00',
            'instrument_id': lris.id,
            'wavelengths': [664, 665, 666],
            'fluxes': [234.2, 232.1, 235.3],
            'group_ids': [],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'

    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')

    spectrum_plot_div = driver.wait_for_xpath(
        "//div[contains(@data-testid, 'spectrum_bokeh_plot')]"
    )
    generated_plot_data = spectrum_plot_div.screenshot_as_png
    generated_plot = Image.open(BytesIO(generated_plot_data))

    expected_plot_path = os.path.abspath(
        "skyportal/tests/data/spectrum_plot_expected.png"
    )

    # Use this commented line to save a new version of the expected plot
    # if changes have been made to the component:
    # temporarily generate the plot we will test against
    # generated_plot.save(expected_plot_path)

    if not os.path.exists(expected_plot_path):
        pytest.fail("Missing spectrum bokeh baseline image for comparison")
    expected_plot = Image.open(expected_plot_path)

    difference = ImageChops.difference(
        generated_plot.convert('RGB'), expected_plot.convert('RGB')
    )
    assert difference.getbbox() is None
