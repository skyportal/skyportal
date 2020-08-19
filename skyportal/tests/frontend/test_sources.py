import os
from os.path import join as pjoin
import uuid
from io import BytesIO
import pytest
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from PIL import Image, ImageChops

from baselayer.app.config import load_config
from skyportal.tests import api, IS_CI_BUILD


cfg = load_config()


def test_public_source_page(driver, user, public_source, public_group):
    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    driver.wait_for_xpath(
        '//label[contains(text(), "band")]', 10
    )  # TODO how to check plot?
    driver.wait_for_xpath('//label[contains(text(), "Fe III")]')
    driver.wait_for_xpath(f'//span[text()="{public_group.name}"]')


@pytest.mark.flaky(reruns=3)
def test_classifications(driver, user, taxonomy_token, public_group, public_source):
    if IS_CI_BUILD:
        pytest.xfail("Xfailing this test on CI builds.")

    simple = {
        'class': 'Cepheid',
        'tags': ['giant/supergiant', 'instability strip', 'standard candle'],
        'other names': ['Cep', 'CEP'],
        'subclasses': [
            {'class': 'Anomolous', 'other names': ['Anomolous Cepheid', 'BLBOO']},
            {
                'class': 'Mult-mode',
                'other names': ['Double-mode Cepheid', 'Multi-mode Cepheid', 'CEP(B)'],
            },
            {
                'class': 'Classical',
                'tags': [],
                'other names': [
                    'Population I Cepheid',
                    'Type I Cepheid',
                    'DCEP',
                    'Delta Cepheid',
                    'Classical Cepheid',
                ],
                'subclasses': [
                    {
                        'class': 'Symmetrical',
                        'other names': ['DCEPS', 'Delta Cep-type Symmetrical'],
                    }
                ],
            },
        ],
    }

    tax_name = str(uuid.uuid4())
    tax_version = "test0.1"

    status, data = api(
        'POST',
        'taxonomy',
        data={
            'name': tax_name,
            'hierarchy': simple,
            'group_ids': [public_group.id],
            'version': tax_version,
        },
        token=taxonomy_token,
    )
    assert status == 200

    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    driver.click_xpath('//div[@id="tax-select"]')
    driver.click_xpath(f'//*[text()="{tax_name} ({tax_version})"]')
    driver.click_xpath('//*[@id="classification"]')
    driver.wait_for_xpath('//*[@id="classification"]').send_keys(
        "Symmetrical", Keys.ENTER
    )
    driver.click_xpath("//*[@id='classificationSubmitButton']")
    # Notification
    driver.wait_for_xpath("//*[text()='Classification saved']")

    # Button at top of source page
    driver.wait_for_xpath(
        "//span[contains(@class, 'MuiButton-label') and text()='Symmetrical']"
    )

    # Scroll up to get entire classifications list component in view
    add_comments = driver.find_element_by_xpath("//h6[contains(text(), 'Add comment')]")
    driver.scroll_to_element(add_comments)

    del_button_xpath = "//button[starts-with(@name, 'deleteClassificationButton')]"
    ActionChains(driver).move_to_element(
        driver.wait_for_xpath(del_button_xpath)
    ).perform()
    driver.click_xpath(del_button_xpath, wait_clickable=False)
    driver.wait_for_xpath_to_disappear("//*[contains(text(), '(P=1)')]")
    driver.wait_for_xpath_to_disappear(f"//i[text()='{tax_name}']")
    driver.wait_for_xpath_to_disappear(
        "//span[contains(@class, 'MuiButton-label') and text()='Symmetrical']"
    )


@pytest.mark.flaky(reruns=2)
def test_comments(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_box = driver.wait_for_xpath("//input[@name='text']")
    comment_text = str(uuid.uuid4())
    comment_box.send_keys(comment_text)
    driver.click_xpath('//*[@name="submitCommentButton"]')
    try:
        driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
        driver.wait_for_xpath('//span[text()="a few seconds ago"]')
    except TimeoutException:
        driver.refresh()
        comment_box = driver.wait_for_xpath("//input[@name='text']")
        comment_text = str(uuid.uuid4())
        comment_box.send_keys(comment_text)
        driver.click_xpath('//*[@name="submitCommentButton"]')
        driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
        driver.wait_for_xpath('//span[text()="a few seconds ago"]')


@pytest.mark.flaky(reruns=2)
def test_comment_groups_validation(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_box = driver.wait_for_xpath("//input[@name='text']")
    comment_text = str(uuid.uuid4())
    comment_box.send_keys(comment_text)
    driver.wait_for_xpath("//*[text()='Customize Group Access']").click()
    group_checkbox = driver.wait_for_xpath("//input[@name='group_ids[0]']")
    assert group_checkbox.is_selected()
    group_checkbox.click()
    driver.click_xpath('//*[@name="submitCommentButton"]')
    driver.wait_for_xpath('//div[contains(.,"Select at least one group")]')
    group_checkbox.click()
    driver.wait_for_xpath_to_disappear('//div[contains(.,"Select at least one group")]')
    driver.click_xpath('//*[@name="submitCommentButton"]')
    try:
        driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
        driver.wait_for_xpath('//span[text()="a few seconds ago"]')
    except TimeoutException:
        driver.refresh()
        driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
        driver.wait_for_xpath('//span[text()="a few seconds ago"]')


@pytest.mark.flaky(reruns=2)
def test_upload_download_comment_attachment(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_box = driver.wait_for_xpath("//input[@name='text']")
    comment_text = str(uuid.uuid4())
    comment_box.send_keys(comment_text)
    attachment_file = driver.find_element_by_css_selector('input[type=file]')
    attachment_file.send_keys(
        pjoin(os.path.dirname(os.path.dirname(__file__)), 'data', 'spec.csv')
    )
    driver.click_xpath('//*[@name="submitCommentButton"]')
    try:
        comment_text_div = driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
    except TimeoutException:
        driver.refresh()
        comment_text_div = driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
    comment_div = comment_text_div.find_element_by_xpath("..")
    driver.execute_script("arguments[0].scrollIntoView();", comment_div)
    ActionChains(driver).move_to_element(comment_div).perform()
    driver.click_xpath('//a[text()="spec.csv"]')
    fpath = str(os.path.abspath(pjoin(cfg['paths.downloads_folder'], 'spec.csv')))
    try_count = 1
    while not os.path.exists(fpath) and try_count <= 3:
        try_count += 1
        driver.execute_script("arguments[0].scrollIntoView();", comment_div)
        ActionChains(driver).move_to_element(comment_div).perform()
        driver.click_xpath('//a[text()="spec.csv"]')
        if os.path.exists(fpath):
            break
    else:
        assert os.path.exists(fpath)

    try:
        with open(fpath) as f:
            lines = f.read()
        assert lines.split('\n')[0] == 'wavelengths,fluxes,instrument_id'
    finally:
        os.remove(fpath)


def test_view_only_user_cannot_comment(driver, view_only_user, public_source):
    driver.get(f"/become_user/{view_only_user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    driver.wait_for_xpath_to_disappear('//input[@name="text"]')


@pytest.mark.flaky(reruns=2)
def test_delete_comment(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_box = driver.wait_for_xpath("//input[@name='text']")
    comment_text = str(uuid.uuid4())
    comment_box.send_keys(comment_text)
    driver.click_xpath('//*[@name="submitCommentButton"]')
    try:
        comment_text_div = driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
    except TimeoutException:
        driver.refresh()
        comment_text_div = driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
    comment_div = comment_text_div.find_element_by_xpath("..")
    comment_id = comment_div.get_attribute("name").split("commentDiv")[-1]
    delete_button = comment_div.find_element_by_xpath(
        f"//*[@name='deleteCommentButton{comment_id}']"
    )
    driver.execute_script("arguments[0].scrollIntoView();", comment_div)
    ActionChains(driver).move_to_element(comment_div).perform()
    driver.execute_script("arguments[0].click();", delete_button)
    try:
        driver.wait_for_xpath_to_disappear(f'//div[text()="{comment_text}"]')
    except TimeoutException:
        driver.refresh()
        try:
            comment_text_div = driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
        except TimeoutException:
            return
        else:
            comment_div = comment_text_div.find_element_by_xpath("..")
            comment_id = comment_div.get_attribute("name").split("commentDiv")[-1]
            delete_button = comment_div.find_element_by_xpath(
                f"//*[@name='deleteCommentButton{comment_id}']"
            )
            driver.execute_script("arguments[0].scrollIntoView();", comment_div)
            ActionChains(driver).move_to_element(comment_div).perform()
            driver.execute_script("arguments[0].click();", delete_button)
            driver.wait_for_xpath_to_disappear(f'//div[text()="{comment_text}"]')


@pytest.mark.flaky(reruns=2)
def test_regular_user_cannot_delete_unowned_comment(
    driver, super_admin_user, user, public_source
):
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_box = driver.wait_for_xpath("//input[@name='text']")
    comment_text = str(uuid.uuid4())
    comment_box.send_keys(comment_text)
    submit_button = driver.find_element_by_xpath('//*[@name="submitCommentButton"]')
    submit_button.click()
    try:
        comment_text_div = driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
    except TimeoutException:
        driver.refresh()
        comment_text_div = driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    comment_text_div = driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
    comment_div = comment_text_div.find_element_by_xpath("..")
    comment_id = comment_div.get_attribute("name").split("commentDiv")[-1]
    delete_button = comment_div.find_element_by_xpath(
        f"//*[@name='deleteCommentButton{comment_id}']"
    )
    driver.execute_script("arguments[0].scrollIntoView();", comment_div)
    ActionChains(driver).move_to_element(comment_div).perform()
    assert not delete_button.is_displayed()


@pytest.mark.flaky(reruns=2)
def test_super_user_can_delete_unowned_comment(
    driver, super_admin_user, user, public_source
):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_box = driver.wait_for_xpath("//input[@name='text']")
    comment_text = str(uuid.uuid4())
    comment_box.send_keys(comment_text)
    driver.scroll_to_element_and_click(
        driver.find_element_by_xpath('//*[@name="submitCommentButton"]')
    )
    try:
        comment_text_div = driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
    except TimeoutException:
        driver.refresh()
        comment_text_div = driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.refresh()
    comment_text_div = driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
    comment_div = comment_text_div.find_element_by_xpath("..")
    comment_id = comment_div.get_attribute("name").split("commentDiv")[-1]
    delete_button = comment_div.find_element_by_xpath(
        f"//*[@name='deleteCommentButton{comment_id}']"
    )
    driver.execute_script("arguments[0].scrollIntoView();", comment_div)
    ActionChains(driver).move_to_element(comment_div).perform()
    driver.execute_script("arguments[0].click();", delete_button)
    try:
        driver.wait_for_xpath_to_disappear(f'//div[text()="{comment_text}"]')
    except TimeoutException:
        driver.refresh()
        driver.wait_for_xpath_to_disappear(f'//div[text()="{comment_text}"]')


def test_show_starlist(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    button = driver.wait_for_xpath(f'//span[text()="Show Starlist"]')
    button.click()
    driver.wait_for_xpath(f'//code[contains(text(), _off1)]')


@pytest.mark.flaky(reruns=2)
def test_centroid_plot(
    driver, user, public_source, public_group, ztf_camera, upload_data_token
):
    # Put in some actual photometry data first
    status, data = api(
        'POST',
        'photometry',
        data={
            'obj_id': str(public_source.id),
            'mjd': [58000.0, 58001.0, 58002.0],
            'instrument_id': ztf_camera.id,
            'flux': [12.24, 15.24, 12.24],
            'fluxerr': [0.031, 0.029, 0.030],
            'filter': ['ztfg', 'ztfg', 'ztfg'],
            'zp': [25.0, 30.0, 21.2],
            'magsys': ['ab', 'ab', 'ab'],
            'ra': [264.19482957057863, 264.1948483167286, 264.19475131195185],
            'ra_unc': 0.17,
            'dec': [50.54773905413207, 50.547910537435854, 50.547856056708355],
            'dec_unc': 0.2,
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    assert len(data['data']['ids']) == 3

    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")

    try:
        # Look for Suspense fallback to show
        loading_text = "Loading centroid plot..."
        driver.wait_for_xpath(f'//div[text()="{loading_text}"]')
        driver.wait_for_xpath_to_disappear(f'//div[text()="{loading_text}"]')

    except TimeoutException:
        # The plot may have loaded too quickly to catch the Suspense div
        driver.wait_for_xpath_to_disappear(f'//div[text()="{loading_text}"]')

    finally:
        component_class_xpath = "//div[contains(concat(' ', normalize-space(@class), ' '), ' centroid-plot-div ')]"
        vegaplot_div = driver.wait_for_xpath(component_class_xpath)
        assert vegaplot_div.is_displayed()

        # Since Vega uses a <canvas> element, we can't examine individual
        # components of the plot through the DOM, so just compare an image of
        # the plot to the saved baseline
        generated_plot_data = vegaplot_div.screenshot_as_png
        generated_plot = Image.open(BytesIO(generated_plot_data))

        expected_plot_path = os.path.abspath(
            "skyportal/tests/data/centroid_plot_expected.png"
        )
        if not os.path.exists(expected_plot_path):
            pytest.fail("Missing centroid plot baseline image for comparison")
        expected_plot = Image.open(expected_plot_path)

        difference = ImageChops.difference(generated_plot, expected_plot)
        assert difference.getbbox() is None
