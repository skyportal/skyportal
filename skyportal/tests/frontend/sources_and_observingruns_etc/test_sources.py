import os
import uuid
import json
import time

from io import BytesIO
import pytest
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from PIL import Image, ImageChops

from baselayer.app.config import load_config
from skyportal.tests import api
from skyportal.models import DBSession

analysis_port = 6802


cfg = load_config()


def enter_comment_text(driver, comment_text):
    comment_xpath = "//div[@data-testid='comments-accordion']//textarea[@name='text']"
    comment_box = driver.wait_for_xpath(comment_xpath)
    driver.click_xpath(comment_xpath)
    comment_box.send_keys(comment_text)


def add_comment(driver, comment_text):
    enter_comment_text(driver, comment_text)
    driver.click_xpath(
        '//div[@data-testid="comments-accordion"]//*[@name="submitCommentButton"]'
    )


def add_comment_and_wait_for_display(driver, comment_text):
    add_comment(driver, comment_text)
    try:
        driver.wait_for_xpath(f'//p[contains(text(), "{comment_text}")]', timeout=20)
    except TimeoutException:
        driver.refresh()
        # little triangle you push to expand the table
        driver.click_xpath("//*[@id='expandable-button']")
        driver.wait_for_xpath(f'//p[contains(text(), "{comment_text}")]')


@pytest.mark.flaky(reruns=2)
def test_public_source_page(driver, user, public_source, public_group):
    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//h6[text()="{public_source.id}"]')

    driver.wait_for_xpath(f'//span[text()="{public_group.name}"]')


@pytest.mark.flaky(reruns=2)
def test_comment_username_autosuggestion(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//h6[text()="{public_source.id}"]')
    comment_text = f"hey @{user.username[:5]}"
    enter_comment_text(driver, comment_text)
    matchButtonXpath = (
        f'//button[text()="{user.username} {user.first_name} {user.last_name}"]'
    )
    driver.wait_for_xpath(matchButtonXpath)
    driver.click_xpath(matchButtonXpath)
    driver.wait_for_xpath_to_disappear(matchButtonXpath)
    driver.click_xpath(
        '//div[@data-testid="comments-accordion"]//*[@name="submitCommentButton"]'
    )
    driver.wait_for_xpath(f'//p[text()="hey @{user.username}"]')


@pytest.mark.flaky(reruns=2)
def test_comment_user_last_name_autosuggestion(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//h6[text()="{public_source.id}"]')
    comment_text = f"hey @{user.last_name[:5]}"
    enter_comment_text(driver, comment_text)
    matchButtonXpath = (
        f'//button[text()="{user.username} {user.first_name} {user.last_name}"]'
    )
    driver.wait_for_xpath(matchButtonXpath)
    driver.click_xpath(matchButtonXpath)
    driver.wait_for_xpath_to_disappear(matchButtonXpath)
    driver.click_xpath(
        '//div[@data-testid="comments-accordion"]//*[@name="submitCommentButton"]'
    )
    driver.wait_for_xpath(f'//p[text()="hey @{user.username}"]')


@pytest.mark.flaky(reruns=2)
def test_comment_user_first_name_autosuggestion(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//h6[text()="{public_source.id}"]')
    comment_text = f"hey @{user.first_name[:5]}"
    enter_comment_text(driver, comment_text)
    matchButtonXpath = (
        f'//button[text()="{user.username} {user.first_name} {user.last_name}"]'
    )
    driver.wait_for_xpath(matchButtonXpath)
    driver.click_xpath(matchButtonXpath)
    driver.wait_for_xpath_to_disappear(matchButtonXpath)
    driver.click_xpath(
        '//div[@data-testid="comments-accordion"]//*[@name="submitCommentButton"]'
    )
    driver.wait_for_xpath(f'//p[text()="hey @{user.username}"]')


@pytest.mark.flaky(reruns=2)
def test_public_source_page_null_z(driver, user, public_source, public_group):
    public_source.redshift = None
    DBSession().add(public_source)
    DBSession().commit()

    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//h6[text()="{public_source.id}"]')

    driver.wait_for_xpath(f'//span[text()="{public_group.name}"]')


@pytest.mark.flaky(reruns=3)
def test_analysis_start(
    driver, user, public_source, analysis_service_token, public_group
):
    name = str(uuid.uuid4())
    optional_analysis_parameters = {}

    post_data = {
        'name': name,
        'display_name': "test analysis service name",
        'description': "A test analysis service description",
        'version': "1.0",
        'contact_name': "Vera Rubin",
        'contact_email': "vr@ls.st",
        # this is the URL/port of the SN analysis service that will be running during testing
        'url': f"http://localhost:{analysis_port}/analysis/demo_analysis",
        'optional_analysis_parameters': json.dumps(optional_analysis_parameters),
        'authentication_type': "none",
        'analysis_type': 'lightcurve_fitting',
        'input_data_types': ['photometry', 'redshift'],
        'timeout': 60,
        'group_ids': [public_group.id],
    }

    status, data = api(
        'POST', 'analysis_service', data=post_data, token=analysis_service_token
    )
    assert status == 200
    assert data['status'] == 'success'

    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//h6[text()="{public_source.id}"]')
    driver.wait_for_xpath('//*[text()="External Analysis"]')

    driver.click_xpath('//div[@data-testid="analysisServiceSelect"]')
    driver.click_xpath(
        '//div[@data-testid="analysis-service-request-form"]//*[@type="submit"]'
    )
    driver.wait_for_xpath(
        f"//*[text()='Sending data to analysis service {name} to start the analysis.']"
    )


@pytest.mark.flaky(reruns=3)
def test_analysis_with_file_input_start(
    driver, user, public_source, analysis_service_token, public_group
):
    name = str(uuid.uuid4())

    optional_analysis_parameters = {
        "image_data": {"type": "file", "required": "True", "description": "Image data"},
        "fluxcal_data": {"type": "file", "description": "Fluxcal data"},
        "centroid_X": {"type": "number"},
        "centroid_Y": {"type": "number"},
        "spaxel_buffer": {"type": "number"},
    }

    post_data = {
        'name': name,
        'display_name': "Spectral_Cube_Analysis",
        'description': "Spectral_Cube_Analysis description",
        'version': "1.0",
        'contact_name': "Michael Coughlin",
        # this is the URL/port of the Spectral_Cube_Analysis service that will be running during testing
        'url': "http://localhost:7003/analysis/spectral_cube_analysis",
        'optional_analysis_parameters': json.dumps(optional_analysis_parameters),
        'authentication_type': "none",
        'analysis_type': 'spectrum_fitting',
        'input_data_types': [],
        'timeout': 60,
        'group_ids': [public_group.id],
    }

    status, data = api(
        'POST', 'analysis_service', data=post_data, token=analysis_service_token
    )
    assert status == 200
    assert data['status'] == 'success'

    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//h6[text()="{public_source.id}"]')
    driver.wait_for_xpath('//*[text()="External Analysis"]')

    driver.click_xpath('//div[@data-testid="analysisServiceSelect"]')

    # look for an element list with a text with the uuid name of the analysis service
    driver.click_xpath(f'//li[text()="{name}"]', timeout=30)

    # look for an input element with id root_image_data
    image_data = driver.wait_for_xpath('//input[@id="root_image_data"]')

    image_data.send_keys(
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            '../data',
            'spectral_cube_analysis.fits',
        ),
    )

    driver.click_xpath(
        '//div[@data-testid="analysis-service-request-form"]//*[@type="submit"]'
    )
    driver.wait_for_xpath(
        f"//*[text()='Sending data to analysis service {name} to start the analysis.']"
    )


# @pytest.mark.flaky(reruns=3)
def test_classifications(driver, user, taxonomy_token, public_group, public_source):
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

    status, _ = api(
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
    driver.wait_for_xpath(f'//h6[text()="{public_source.id}"]')

    # wait for plots to load
    try:
        driver.wait_for_xpath(
            '//div[@id="photometry-plot"]/div/div/div[@class="plot-container plotly"]',
            timeout=5,
        )
        driver.wait_for_xpath(
            '//div[@id="spectroscopy-plot"]/div/div/div[@class="plot-container plotly"]',
            timeout=5,
        )
    except TimeoutException:
        pass

    driver.click_xpath('//div[@id="root_taxonomy"]')
    driver.click_xpath(
        f'//*[text()="{tax_name} ({tax_version})"]',
        wait_clickable=False,
        scroll_parent=True,
    )

    # Click somewhere outside to remove focus from taxonomy select
    header = driver.wait_for_xpath("//header")
    ActionChains(driver).move_to_element(header).click().perform()

    driver.click_xpath('//*[@id="classification"]')
    # type "Mult-mode" into the classification select text box
    classification_textbox = driver.wait_for_xpath('//*[@id="classification"]')
    classification_textbox.send_keys("Symmetrical")
    driver.click_xpath('//div[contains(@id, "Symmetrical")]', scroll_parent=True)

    # Click somewhere outside to remove focus from classification select
    header = driver.wait_for_xpath("//header")
    ActionChains(driver).move_to_element(header).click().perform()

    probability_input = driver.wait_for_xpath('//*[@id="probability"]')
    driver.scroll_to_element_and_click(probability_input, scroll_parent=True)
    driver.wait_for_xpath('//*[@id="probability"]').send_keys("1")

    driver.click_xpath("//*[text()='Submit']", wait_clickable=False)
    # Notification
    driver.wait_for_xpath("//*[text()='Classification saved']")
    # Scroll up to get top of classifications list component in view
    classifications = driver.find_element(
        By.XPATH, "//div[@id='classifications-header']"
    )
    driver.scroll_to_element(classifications)

    del_button_xpath = "//button[starts-with(@name, 'deleteClassificationButton')]"
    driver.wait_for_xpath(del_button_xpath, timeout=20)
    driver.scroll_to_element(driver.wait_for_xpath(del_button_xpath))

    driver.click_xpath(del_button_xpath)
    driver.click_xpath("//*[text()='Confirm']", wait_clickable=False)
    driver.wait_for_xpath_to_disappear("//*[contains(text(), '(P=1)')]")
    driver.wait_for_xpath_to_disappear(f"//i[text()='{tax_name}']")
    driver.wait_for_xpath_to_disappear(
        "//span[contains(@class, 'MuiButton-label') and text()='Symmetrical']"
    )

    # ensure low probability classifications have a question mark on the label

    driver.click_xpath('//div[@id="root_taxonomy"]')
    driver.click_xpath(
        f'//*[text()="{tax_name} ({tax_version})"]',
        wait_clickable=False,
        scroll_parent=True,
    )
    # Click somewhere outside to remove focus from taxonomy select
    header = driver.wait_for_xpath("//header")
    ActionChains(driver).move_to_element(header).click().perform()

    driver.click_xpath('//*[@id="classification"]')
    # type "Mult-mode" into the classification select text box
    classification_textbox = driver.wait_for_xpath('//*[@id="classification"]')
    classification_textbox.send_keys("Mult-mode")
    driver.click_xpath('//div[contains(@id, "Mult-mode")]', scroll_parent=True)

    # Click somewhere outside to remove focus from classification select
    header = driver.wait_for_xpath("//header")
    ActionChains(driver).move_to_element(header).click().perform()

    # empty the probability text box
    probability_input = driver.wait_for_xpath('//*[@id="probability"]')
    driver.scroll_to_element_and_click(probability_input, scroll_parent=True)
    probability_input.send_keys(Keys.BACKSPACE)

    driver.wait_for_xpath('//*[@id="probability"]').send_keys("0.02")
    driver.click_xpath("//*[text()='Submit']", wait_clickable=False)
    driver.wait_for_xpath("//*[text()='Classification saved']")

    driver.wait_for_xpath(
        "//span[text()='Mult-mode?']",
    )
    driver.wait_for_xpath(
        "//span[text()='(P=0.02)']",
    )


@pytest.mark.flaky(reruns=2)
def test_comments(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//h6[text()="{public_source.id}"]')
    comment_text = str(uuid.uuid4())
    add_comment_and_wait_for_display(driver, comment_text)


# @pytest.mark.flaky(reruns=2)
def test_comment_groups_validation(
    driver, user, super_admin_token, public_source, public_group
):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//h6[text()="{public_source.id}"]')

    # fist post a classification without specifying anything
    # (publicly accessible if no group is selected should be the default)
    comment_text = str(uuid.uuid4())
    enter_comment_text(driver, comment_text)
    driver.click_xpath(
        '//div[@data-testid="comments-accordion"]//*[@name="submitCommentButton"]'
    )
    try:
        driver.wait_for_xpath(
            f'//div[@data-testid="comments-accordion"]//p[text()="{comment_text}"]',
            timeout=20,
        )
        driver.wait_for_xpath(
            '//div[@data-testid="comments-accordion"]//span[text()="a few seconds ago"]'
        )
    except TimeoutException:
        driver.refresh()
        driver.wait_for_xpath(
            f'//div[@data-testid="comments-accordion"]//p[text()="{comment_text}"]'
        )
        driver.wait_for_xpath(
            '//div[@data-testid="comments-accordion"]//span[text()="a few seconds ago"]'
        )

    # then post a classification to a specific group
    enter_comment_text(driver, "")
    comment_text = str(uuid.uuid4())
    enter_comment_text(driver, comment_text)
    driver.click_xpath(
        "//div[@data-testid='comments-accordion']//*[text()='Customize Group Access (public if not specified)']"
    )
    group_checkbox_xpath = f"//div[@data-testid='comments-accordion']//*[@data-testid='commentGroupCheckBox{public_group.id}']"
    driver.click_xpath(group_checkbox_xpath, wait_clickable=False)
    driver.click_xpath(
        '//div[@data-testid="comments-accordion"]//*[@name="submitCommentButton"]'
    )
    try:
        driver.wait_for_xpath(
            f'//div[@data-testid="comments-accordion"]//p[text()="{comment_text}"]',
            timeout=20,
        )
        driver.wait_for_xpath(
            '//div[@data-testid="comments-accordion"]//span[text()="a few seconds ago"]'
        )
    except TimeoutException:
        driver.refresh()
        driver.wait_for_xpath(
            f'//div[@data-testid="comments-accordion"]//p[text()="{comment_text}"]'
        )
        driver.wait_for_xpath(
            '//div[@data-testid="comments-accordion"]//span[text()="a few seconds ago"]'
        )


def test_view_only_user_cannot_comment(driver, view_only_user, public_source):
    driver.get(f"/become_user/{view_only_user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//h6[text()="{public_source.id}"]')
    driver.wait_for_xpath_to_disappear('//textarea[@name="text"]')


@pytest.mark.flaky(reruns=2)
def test_delete_comment(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//h6[text()="{public_source.id}"]')
    comment_text = str(uuid.uuid4())
    add_comment_and_wait_for_display(driver, comment_text)
    comment_text_p = driver.wait_for_xpath(f'//p[text()="{comment_text}"]')
    comment_div = comment_text_p.find_element(By.XPATH, "../..")
    comment_id = comment_div.get_attribute("name").split("commentDivSource")[-1]
    delete_button = comment_div.find_element(
        By.XPATH, f"//*[@name='deleteCommentButton{comment_id}']"
    )
    driver.execute_script("arguments[0].scrollIntoView();", comment_div)
    ActionChains(driver).move_to_element(comment_div).pause(0.1).perform()
    driver.execute_script("arguments[0].click();", delete_button)
    try:
        driver.wait_for_xpath_to_disappear(f'//p[text()="{comment_text}"]')
    except TimeoutException:
        driver.refresh()
        try:
            comment_text_div = driver.wait_for_xpath(
                f'//div[./p[text()="{comment_text}"]]'
            )
        except TimeoutException:
            return
        else:
            comment_div = comment_text_div.find_element(By.XPATH, "..")
            comment_id = comment_div.get_attribute("name").split("commentDivSource")[-1]
            delete_button = comment_div.find_element(
                By.XPATH, f"//*[@name='deleteCommentButton{comment_id}']"
            )
            driver.execute_script("arguments[0].scrollIntoView();", comment_div)
            ActionChains(driver).move_to_element(comment_div).pause(0.1).perform()
            driver.execute_script("arguments[0].click();", delete_button)
            driver.wait_for_xpath_to_disappear(f'//p[text()="{comment_text}"]')


@pytest.mark.flaky(reruns=2)
def test_regular_user_cannot_delete_unowned_comment(
    driver, super_admin_user, user, public_source
):
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//h6[text()="{public_source.id}"]')
    comment_text = str(uuid.uuid4())
    add_comment_and_wait_for_display(driver, comment_text)
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    comment_text_p = driver.wait_for_xpath(f'//p[text()="{comment_text}"]')
    comment_div = comment_text_p.find_element(By.XPATH, "../..")
    comment_id = comment_div.get_attribute("name").split("commentDivSource")[-1]
    delete_button = comment_div.find_element(
        By.XPATH, f"//*[@name='deleteCommentButton{comment_id}']"
    )
    driver.execute_script("arguments[0].scrollIntoView();", comment_div)
    ActionChains(driver).move_to_element(comment_div).pause(0.1).perform()
    assert not delete_button.is_displayed()


@pytest.mark.flaky(reruns=2)
def test_super_user_can_delete_unowned_comment(
    driver, super_admin_user, user, public_source
):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//h6[text()="{public_source.id}"]')
    comment_text = str(uuid.uuid4())
    add_comment_and_wait_for_display(driver, comment_text)

    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/source/{public_source.id}")

    comment_text_p = driver.wait_for_xpath(f'//p[text()="{comment_text}"]')
    comment_div = comment_text_p.find_element(By.XPATH, "../..")
    comment_id = comment_div.get_attribute("name").split("commentDivSource")[-1]

    # wait for delete button to become interactible - hence pause 0.1
    driver.scroll_to_element(comment_text_p)
    ActionChains(driver).move_to_element(comment_text_p).pause(0.1).perform()

    delete_button = driver.wait_for_xpath(
        f"//*[@name='deleteCommentButton{comment_id}']"
    )
    ActionChains(driver).move_to_element(delete_button).pause(0.1).click().perform()
    driver.wait_for_xpath_to_disappear(f'//p[text()="{comment_text}"]')


def test_show_starlist(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    button = driver.wait_for_xpath('//button[text()="Show Starlist"]')
    button.click()
    driver.wait_for_xpath("//code/div/pre[text()[contains(., '_o1')]]", timeout=45)


@pytest.mark.flaky(reruns=2)
def test_centroid_plot(
    driver, user, public_source, public_group, ztf_camera, upload_data_token
):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")

    driver.wait_for_xpath('//div[@id="no-centroid-plot"]')

    discovery_ra = public_source.ra
    discovery_dec = public_source.dec
    # Put in some actual photometry data first
    status, data = api(
        'POST',
        'photometry?refresh=true',
        data={
            'obj_id': str(public_source.id),
            'mjd': [58000.0, 58001.0, 58002.0],
            'instrument_id': ztf_camera.id,
            'flux': [12.24, 15.24, 12.24],
            'fluxerr': [0.031, 0.029, 0.030],
            'filter': ['ztfg', 'ztfg', 'ztfg'],
            'zp': [25.0, 30.0, 21.2],
            'magsys': ['ab', 'ab', 'ab'],
            'ra': [discovery_ra + 0.0001, discovery_ra + 0.0002, discovery_ra + 0.0003],
            'ra_unc': 0.17,
            'dec': [
                discovery_dec + 0.0001,
                discovery_dec + 0.0002,
                discovery_dec + 0.0003,
            ],
            'dec_unc': 0.2,
            'group_ids': [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data['status'] == 'success'
    assert len(data['data']['ids']) == 3

    driver.wait_for_xpath('//div[@id="centroid-plot"]/div[@class="js-plotly-plot"]')


def test_dropdown_facility_change(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?
    driver.get(f"/source/{public_source.id}")
    driver.click_xpath('//*[text()="Show Starlist"]')
    driver.wait_for_xpath("//code/div/pre[text()[contains(., 'raoffset')]]", timeout=45)
    driver.click_xpath('//*[@id="mui-component-select-StarListSelectElement"]')
    driver.click_xpath('//li[@data-value="P200"]')
    driver.wait_for_xpath("//code/div/pre[text()[contains(., 'dist')]]", timeout=45)


def test_source_notification(driver, user, public_group, public_source):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//h6[text()="{public_source.id}"]')

    # Choose a group and click something outside/not covered by the multi-select
    # popup to close it, and retry a few times in case the page loads slowly
    n_retries = 0
    while n_retries < 3:
        try:
            group_select = driver.wait_for_xpath("//div[@id='selectGroups']", timeout=1)
            driver.scroll_to_element_and_click(group_select)
            driver.click_xpath(
                f'//div[@data-testid="group_{public_group.id}"]',
                scroll_parent=True,
            )
            break
        except Exception:
            n_retries += 1
            time.sleep(1)
            continue

    assert n_retries < 3

    header = driver.wait_for_xpath("//header")
    driver.scroll_to_element_and_click(header)
    driver.click_xpath("//label[@data-testid='soft']")
    driver.click_xpath("//button[@data-testid='sendNotificationButton']")
    driver.wait_for_xpath("//*[text()='Notification queued up successfully']")


@pytest.mark.flaky(reruns=2)
def test_unsave_from_group(
    driver, user_two_groups, public_source_two_groups, public_group2
):
    public_source = public_source_two_groups
    driver.get(f"/become_user/{user_two_groups.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//h6[text()="{public_source.id}"]')
    driver.click_xpath(f'//*[@data-testid="editGroups_{public_source.id}"]')
    driver.click_xpath(
        f'//*[@data-testid="unsaveGroupCheckbox_{public_group2.id}"]',
        scroll_parent=True,
    )
    driver.click_xpath(f'//button[@name="editSourceGroupsButton_{public_source.id}"]')
    driver.wait_for_xpath(
        '//*[text()="Source groups updated successfully"]', timeout=10
    )
    driver.wait_for_xpath_to_disappear(
        f'//div[@data-testid="groupChip_{public_group2.id}"]'
    )


@pytest.mark.flaky(reruns=2)
def test_request_group_to_save_then_save(
    driver, user, user_two_groups, public_source, public_group2
):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//h6[text()="{public_source.id}"]')
    driver.click_xpath(f'//*[@data-testid="editGroups_{public_source.id}"]')
    driver.click_xpath(
        f'//*[@data-testid="inviteGroupCheckbox_{public_group2.id}"]',
        scroll_parent=True,
    )
    driver.click_xpath(
        f'//button[@name="editSourceGroupsButton_{public_source.id}"]',
        scroll_parent=True,
    )
    driver.wait_for_xpath(
        '//*[text()="Source groups updated successfully"]', timeout=10
    )
    driver.get(f"/become_user/{user_two_groups.id}")
    driver.get(f"/group_sources/{public_group2.id}")
    driver.click_xpath(f'//button[@data-testid="saveSourceButton_{public_source.id}"]')
    driver.wait_for_xpath_to_disappear(
        f'//button[@data-testid="saveSourceButton_{public_source.id}"]'
    )
    driver.wait_for_xpath(f"//a[contains(@href, '/source/{public_source.id}')]")


@pytest.mark.flaky(reruns=2)
def test_update_redshift_and_history(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//h6[text()="{public_source.id}"]')
    driver.click_xpath("//*[@data-testid='updateRedshiftIconButton']")
    input_field = driver.wait_for_xpath(
        "//div[@data-testid='updateRedshiftTextfield']//input"
    )
    input_field.send_keys("0.9999")
    input_field = driver.wait_for_xpath(
        "//div[@data-testid='updateRedshiftErrorTextfield']//input"
    )
    input_field.send_keys("0.0001")
    driver.click_xpath("//button[@data-testid='updateRedshiftSubmitButton']")
    driver.wait_for_xpath("//*[text()='Source redshift successfully updated.']")
    driver.wait_for_xpath("//body").click()  # Close dialog
    driver.wait_for_xpath("//*[contains(., '0.9999')]")
    driver.wait_for_xpath("//*[contains(., '0.0001')]")

    driver.click_xpath(
        "//*[@data-testid='redshiftHistoryIconButton']",
        wait_clickable=False,
    )
    driver.wait_for_xpath("//th[text()='Set By']", timeout=10)
    driver.wait_for_xpath("//td[text()='0.9999']")
    driver.wait_for_xpath("//td[text()='0.0001']")
    driver.wait_for_xpath(f"//td[text()='{user.username}']")


@pytest.mark.flaky(reruns=2)
def test_update_redshift_and_history_without_error(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//h6[text()="{public_source.id}"]')
    driver.click_xpath("//*[@data-testid='updateRedshiftIconButton']")
    input_field = driver.wait_for_xpath(
        "//div[@data-testid='updateRedshiftTextfield']//input"
    )
    input_field.send_keys("0.9998")
    driver.click_xpath("//button[@data-testid='updateRedshiftSubmitButton']")
    driver.wait_for_xpath("//*[text()='Source redshift successfully updated.']")
    driver.wait_for_xpath("//body").click()  # Close dialog
    driver.wait_for_xpath("//*[contains(., '0.9998')]")

    driver.click_xpath(
        "//*[@data-testid='redshiftHistoryIconButton']", wait_clickable=False
    )
    driver.wait_for_xpath("//th[text()='Set By']")
    driver.wait_for_xpath("//td[text()='0.9998']")
    driver.wait_for_xpath(f"//td[text()='{user.username}']")


@pytest.mark.flaky(reruns=2)
def test_obj_page_unsaved_source(public_obj, driver, user):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_obj.id}")

    driver.wait_for_xpath_to_disappear('//div[contains(@data-testid, "groupChip")]')


def test_show_photometry_table(public_source, driver, user):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")

    photometry_table_button = driver.wait_for_xpath(
        '//*[@data-testid="show-photometry-table-button"]'
    )
    driver.scroll_to_element_and_click(photometry_table_button)
    driver.wait_for_xpath(f'//*[contains(text(), "Photometry of {public_source.id}")]')

    driver.click_xpath('//*[@data-testid="close-photometry-table-button"]')
    driver.wait_for_xpath_to_disappear(
        '//*[@data-testid="close-photometry-table-button"]'
    )


def test_hide_right_panel(public_source, driver, user):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.click_xpath('//*[@data-testid="hide-right-panel-button"]')
    driver.wait_for_xpath_to_disappear('//*[@class="MuiCollapse-entered"]')
    driver.click_xpath('//*[@data-testid="show-right-panel-button"]')
    driver.wait_for_xpath_to_disappear('//*[@class="MuiCollapse-hidden"]')


def test_javascript_sexagesimal_conversion(public_source, driver, user):
    public_source.ra = 342.0708127
    public_source.dec = 56.1130711
    DBSession().commit()
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath('//*[contains(., "22:48:17.00")]')
    driver.wait_for_xpath('//*[contains(., "+56:06:47.06")]')
    public_source.ra = 75.6377796
    public_source.dec = 15.606709
    DBSession().commit()
    driver.refresh()
    driver.wait_for_xpath('//*[contains(., "05:02:33.07")]')
    driver.wait_for_xpath('//*[contains(., "+15:36:24.15")]')


def test_source_hr_diagram(driver, user, public_source, annotation_token):
    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?

    status, data = api(
        'POST',
        f'sources/{public_source.id}/annotations',
        data={
            'obj_id': public_source.id,
            'origin': 'gaiadr3.gaia_source',
            'data': {
                'Mag_G': 11.3,
                'Mag_Bp': 12.8,
                'Mag_Rp': 11.0,
                'Plx': 20,
            },
        },
        token=annotation_token,
    )
    assert status == 200

    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//h6[text()="{public_source.id}"]')

    try:
        # Look for Suspense fallback to show
        loading_text = "Loading HR diagram..."
        driver.wait_for_xpath(f'//div[text()="{loading_text}"]')
        driver.wait_for_xpath_to_disappear(f'//div[text()="{loading_text}"]')

    except TimeoutException:
        # The plot may have loaded too quickly to catch the Suspense div
        driver.wait_for_xpath_to_disappear(f'//div[text()="{loading_text}"]')

    finally:
        component_class_xpath = (
            f"//div[contains(@data-testid, 'hr_diagram_{public_source.id}')]"
        )
        vegaplot_div = driver.wait_for_xpath(component_class_xpath)
        assert vegaplot_div.is_displayed()

        # Since Vega uses a <canvas> element, we can't examine individual
        # components of the plot through the DOM, so just compare an image of
        # the plot to the saved baseline
        generated_plot_data = vegaplot_div.screenshot_as_png
        generated_plot = Image.open(BytesIO(generated_plot_data))

        expected_plot_path = os.path.abspath(
            "skyportal/tests/data/HR_diagram_expected.png"
        )

        # Use this commented line to save a new version of the expected plot
        # if changes have been made to the component:
        # temporarily generate the plot we will test against
        generated_plot.save(expected_plot_path)

        if not os.path.exists(expected_plot_path):
            pytest.fail("Missing HR diagram baseline image for comparison")
        expected_plot = Image.open(expected_plot_path)

        difference = ImageChops.difference(
            generated_plot.convert('RGB'), expected_plot.convert('RGB')
        )
        assert difference.getbbox() is None


def test_duplicate_sources_render(
    driver, public_source, public_group, upload_data_token, user, ztf_camera
):
    obj_id2 = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id2,
            "ra": public_source.ra + 0.0001,
            "dec": public_source.dec + 0.0001,
            "redshift": 3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": obj_id2,
            "mjd": 59801.3,
            "instrument_id": ztf_camera.id,
            "filter": "ztfg",
            "group_ids": [public_group.id],
            "mag": 12.4,
            "magerr": 0.3,
            "limiting_mag": 22,
            "magsys": "ab",
        },
        token=upload_data_token,
    )
    assert status == 200

    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath('//*[contains(text(), "Possible duplicate of:")]')
    driver.click_xpath(f'//*[contains(text(), "{obj_id2}")]')
    driver.wait_for_xpath(f'//*[contains(text(), "{obj_id2}")]', timeout=20)
