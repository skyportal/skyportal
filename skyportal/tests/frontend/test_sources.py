import os
from os.path import join as pjoin
import uuid
from io import BytesIO
import pytest
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from PIL import Image, ImageChops
import responses

from baselayer.app.config import load_config
from skyportal.tests import api


cfg = load_config()


@pytest.mark.flaky(reruns=2)
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
    driver.click_xpath(
        f'//*[text()="{tax_name} ({tax_version})"]',
        wait_clickable=False,
        scroll_parent=True,
    )
    driver.click_xpath('//*[@id="classification"]')
    driver.wait_for_xpath('//*[@id="classification"]').send_keys(
        "Symmetrical", Keys.ENTER
    )
    driver.click_xpath("//*[@id='classificationSubmitButton']")
    # Notification
    driver.wait_for_xpath("//*[text()='Classification saved']")

    # Button at top of source page
    driver.wait_for_xpath("//span[text()[contains(., 'Save')]]")

    # Scroll up to get top of classifications list component in view
    classifications = driver.find_element_by_xpath(
        "//div[@id='classifications-header']"
    )
    driver.scroll_to_element(classifications)

    del_button_xpath = "//button[starts-with(@name, 'deleteClassificationButton')]"
    driver.click_xpath(del_button_xpath, wait_clickable=False)
    driver.wait_for_xpath_to_disappear("//*[contains(text(), '(P=1)')]")
    driver.wait_for_xpath_to_disappear(f"//i[text()='{tax_name}']")
    driver.wait_for_xpath_to_disappear(
        "//span[contains(@class, 'MuiButton-label') and text()='Symmetrical']"
    )


@pytest.mark.flaky(reruns=2)
def test_comments(driver, user, public_source):
    if "TRAVIS" in os.environ:
        pytest.xfail("Xfailing this test on Travis builds.")
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_box = driver.wait_for_xpath("//input[@name='text']")
    comment_text = str(uuid.uuid4())
    comment_box.send_keys(comment_text)
    driver.click_xpath('//*[@name="submitCommentButton"]')
    try:
        driver.wait_for_xpath(f'//p[text()="{comment_text}"]')
        driver.wait_for_xpath('//span[text()="a few seconds ago"]')
    except TimeoutException:
        driver.refresh()
        comment_box = driver.wait_for_xpath("//input[@name='text']")
        comment_text = str(uuid.uuid4())
        comment_box.send_keys(comment_text)
        driver.click_xpath('//*[@name="submitCommentButton"]')
        driver.wait_for_xpath(f'//p[text()="{comment_text}"]')
        driver.wait_for_xpath('//span[text()="a few seconds ago"]')


@pytest.mark.flaky(reruns=2)
def test_comment_groups_validation(
    driver, user, super_admin_token, public_source, public_group
):
    _, data = api("GET", "groups/public", token=super_admin_token)
    sitewide_group_id = data["data"]["id"]
    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_box = driver.wait_for_xpath("//input[@name='text']")
    comment_text = str(uuid.uuid4())
    comment_box.send_keys(comment_text)
    driver.click_xpath("//*[text()='Customize Group Access']")

    # sitewide_group
    group_checkbox_xpath = (
        f"//*[@data-testid='commentGroupCheckBox{sitewide_group_id}']"
    )
    driver.click_xpath(group_checkbox_xpath, wait_clickable=False)

    # public_group that user belongs to
    group_checkbox_xpath = f"//*[@data-testid='commentGroupCheckBox{public_group.id}']"
    driver.click_xpath(group_checkbox_xpath, wait_clickable=False)
    driver.click_xpath('//*[@name="submitCommentButton"]')
    driver.wait_for_xpath('//div[contains(.,"Select at least one group")]')
    driver.click_xpath(group_checkbox_xpath, wait_clickable=False)
    driver.click_xpath('//*[@name="submitCommentButton"]')
    driver.wait_for_xpath_to_disappear('//div[contains(.,"Select at least one group")]')
    try:
        driver.wait_for_xpath(f'//p[text()="{comment_text}"]')
        driver.wait_for_xpath('//span[text()="a few seconds ago"]')
    except TimeoutException:
        driver.refresh()
        driver.wait_for_xpath(f'//p[text()="{comment_text}"]')
        driver.wait_for_xpath('//span[text()="a few seconds ago"]')


@pytest.mark.flaky(reruns=2)
def test_upload_download_comment_attachment(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_box = driver.wait_for_xpath("//input[@name='text']")
    driver.scroll_to_element(comment_box)
    comment_text = str(uuid.uuid4())
    comment_box.send_keys(comment_text)
    attachment_file = driver.find_element_by_css_selector('input[type=file]')
    attachment_file.send_keys(
        pjoin(os.path.dirname(os.path.dirname(__file__)), 'data', 'spec.csv')
    )
    driver.click_xpath('//*[@name="submitCommentButton"]')
    try:
        comment_text_div = driver.wait_for_xpath(f'//div[./p[text()="{comment_text}"]]')
    except TimeoutException:
        driver.refresh()
        comment_text_div = driver.wait_for_xpath(f'//div[./p[text()="{comment_text}"]]')
    comment_div = comment_text_div.find_element_by_xpath("..")
    driver.execute_script("arguments[0].scrollIntoView();", comment_div)
    ActionChains(driver).move_to_element(comment_div).perform()

    # Scroll up to top of comments list
    comments = driver.wait_for_xpath("//p[text()='Comments']")
    driver.scroll_to_element(comments)

    attachment_div = driver.wait_for_xpath("//div[contains(text(), 'Attachment:')]")
    attachment_button = driver.wait_for_xpath(
        '//button[@data-testid="attachmentButton_spec"]'
    )
    # Try to open the preview dialog twice before failing to make it more robust
    try:
        ActionChains(driver).move_to_element(attachment_div).pause(0.5).perform()
        ActionChains(driver).move_to_element(attachment_button).pause(
            0.5
        ).click().perform()
        # Preview dialog
        driver.click_xpath('//a[@data-testid="attachmentDownloadButton_spec"]')
    except TimeoutException:
        ActionChains(driver).move_to_element(attachment_div).pause(0.5).perform()
        ActionChains(driver).move_to_element(attachment_button).pause(
            0.5
        ).click().perform()
        # Preview dialog
        driver.click_xpath('//a[@data-testid="attachmentDownloadButton_spec"]')

    fpath = str(os.path.abspath(pjoin(cfg['paths.downloads_folder'], 'spec.csv')))
    try_count = 1
    while not os.path.exists(fpath) and try_count <= 3:
        try_count += 1
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
        comment_text_div = driver.wait_for_xpath(f'//div[./p[text()="{comment_text}"]]')
    except TimeoutException:
        driver.refresh()
        comment_text_div = driver.wait_for_xpath(f'//div[./p[text()="{comment_text}"]]')
    comment_div = comment_text_div.find_element_by_xpath("..")
    comment_id = comment_div.get_attribute("name").split("commentDiv")[-1]
    delete_button = comment_div.find_element_by_xpath(
        f"//*[@name='deleteCommentButton{comment_id}']"
    )
    driver.execute_script("arguments[0].scrollIntoView();", comment_div)
    ActionChains(driver).move_to_element(comment_div).perform()
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
            comment_div = comment_text_div.find_element_by_xpath("..")
            comment_id = comment_div.get_attribute("name").split("commentDiv")[-1]
            delete_button = comment_div.find_element_by_xpath(
                f"//*[@name='deleteCommentButton{comment_id}']"
            )
            driver.execute_script("arguments[0].scrollIntoView();", comment_div)
            ActionChains(driver).move_to_element(comment_div).perform()
            driver.execute_script("arguments[0].click();", delete_button)
            driver.wait_for_xpath_to_disappear(f'//p[text()="{comment_text}"]')


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
        comment_text_div = driver.wait_for_xpath(f'//div[./p[text()="{comment_text}"]]')
    except TimeoutException:
        driver.refresh()
        comment_text_div = driver.wait_for_xpath(f'//div[./p[text()="{comment_text}"]]')
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    comment_text_div = driver.wait_for_xpath(f'//div[./p[text()="{comment_text}"]]')
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
    driver.scroll_to_element_and_click(comment_box)
    comment_box.send_keys(comment_text)
    driver.scroll_to_element_and_click(
        driver.wait_for_xpath('//*[@name="submitCommentButton"]')
    )

    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/source/{public_source.id}")

    comment_text_div = driver.wait_for_xpath(f'//div[./p[text()="{comment_text}"]]')
    comment_div = comment_text_div.find_element_by_xpath("..")
    comment_id = comment_div.get_attribute("name").split("commentDiv")[-1]

    # wait for delete button to become interactible - hence pause 0.1
    driver.scroll_to_element(comment_text_div)
    ActionChains(driver).move_to_element(comment_text_div).pause(0.1).perform()

    delete_button = driver.wait_for_xpath(
        f"//*[@name='deleteCommentButton{comment_id}']"
    )
    ActionChains(driver).move_to_element(delete_button).pause(0.1).click().perform()
    driver.wait_for_xpath_to_disappear(f'//p[text()="{comment_text}"]')


def test_show_starlist(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    button = driver.wait_for_xpath('//span[text()="Show Starlist"]')
    button.click()
    driver.wait_for_xpath("//code/div/pre[text()[contains(., '_o1')]]", timeout=45)


@pytest.mark.flaky(reruns=2)
def test_centroid_plot(
    driver, user, public_source, public_group, ztf_camera, upload_data_token
):
    if "TRAVIS" in os.environ:
        pytest.xfail("Xfailing this test on Travis builds.")
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
        component_class_xpath = "//div[contains(@data-testid, 'centroid-plot-div')]"
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

        # Use this commented line to save a new version of the expected plot
        # if changes have been made to the component:
        # generated_plot.save(expected_plot_path)

        if not os.path.exists(expected_plot_path):
            pytest.fail("Missing centroid plot baseline image for comparison")
        expected_plot = Image.open(expected_plot_path)

        difference = ImageChops.difference(generated_plot, expected_plot)
        assert difference.getbbox() is None


def test_dropdown_facility_change(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?
    driver.get(f"/source/{public_source.id}")
    driver.scroll_to_element_and_click(
        driver.wait_for_xpath('//span[text()="Show Starlist"]')
    )
    driver.wait_for_xpath("//code/div/pre[text()[contains(., 'raoffset')]]", timeout=45)

    xpath = '//*[@id="mui-component-select-StarListSelectElement"]'
    element = driver.wait_for_xpath(xpath)
    ActionChains(driver).move_to_element(element).click_and_hold().perform()
    xpath = '//li[@data-value="P200"]'
    element = driver.wait_for_xpath(xpath)
    ActionChains(driver).move_to_element(element).click_and_hold().perform()
    driver.wait_for_xpath("//code/div/pre[text()[contains(., 'dist')]]", timeout=45)


@pytest.mark.flaky(reruns=2)
@responses.activate
def test_source_notification(driver, user, public_group, public_source):
    # Just test the front-end form and mock out the SkyPortal API call
    responses.add(
        responses.GET,
        "http://localhost:5000/api/source_notifications",
        json={"status": "success"},
        status=200,
    )

    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    # Choose a group and click something outside/not covered by the multi-select
    # popup to close it
    driver.click_xpath("//div[@data-testid='sourceNotification_groupSelect']")
    driver.click_xpath(
        f'//li[@data-testid="notificationGroupSelect_{public_group.id}"]',
        scroll_parent=True,
    )
    header = driver.wait_for_xpath("//header")
    ActionChains(driver).move_to_element(header).click().perform()
    driver.click_xpath("//button[@data-testid='sendNotificationButton']")
    driver.wait_for_xpath("//*[text()='Notification queued up sucessfully']")


def test_unsave_from_group(
    driver, user_two_groups, public_source_two_groups, public_group2
):
    public_source = public_source_two_groups
    driver.get(f"/become_user/{user_two_groups.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    driver.click_xpath(f'//*[@data-testid="editGroups_{public_source.id}"]')
    driver.click_xpath(f'//*[@data-testid="unsaveGroupCheckbox_{public_group2.id}"]')
    driver.click_xpath(f'//button[@name="editSourceGroupsButton_{public_source.id}"]')
    driver.wait_for_xpath('//*[text()="Source groups updated successfully"]')
    driver.wait_for_xpath_to_disappear(
        f'//div[@data-testid="groupChip_{public_group2.id}"]'
    )


def test_request_group_to_save_then_save(
    driver, user_two_groups, public_source, public_group2
):
    driver.get(f"/become_user/{user_two_groups.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    driver.click_xpath(f'//*[@data-testid="editGroups_{public_source.id}"]')
    driver.click_xpath(f'//*[@data-testid="inviteGroupCheckbox_{public_group2.id}"]')
    driver.click_xpath(f'//button[@name="editSourceGroupsButton_{public_source.id}"]')
    driver.wait_for_xpath('//*[text()="Source groups updated successfully"]')
    driver.get(f"/group_sources/{public_group2.id}")
    driver.click_xpath(f'//button[@data-testid="saveSourceButton_{public_source.id}"]')
    driver.wait_for_xpath_to_disappear(
        f'//button[@data-testid="saveSourceButton_{public_source.id}"]'
    )
    driver.wait_for_xpath(f"//a[contains(@href, '/source/{public_source.id}')]")


def test_update_redshift_and_history(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    driver.click_xpath("//*[@data-testid='updateRedshiftIconButton']")
    input_field = driver.wait_for_xpath(
        "//div[@data-testid='updateRedshiftTextfield']//input"
    )
    input_field.send_keys("0.9999")
    driver.click_xpath("//button[@data-testid='updateRedshiftSubmitButton']")
    driver.wait_for_xpath("//*[text()='Source redshift successfully updated.']")
    driver.wait_for_xpath("//body").click()  # Close dialog
    driver.wait_for_xpath("//*[contains(., '0.9999')]")

    driver.click_xpath(
        "//*[@data-testid='redshiftHistoryIconButton']", wait_clickable=False
    )
    driver.wait_for_xpath("//th[text()='Set By']")
    driver.wait_for_xpath("//td[text()='0.9999']")
    driver.wait_for_xpath(f"//td[text()='{user.username}']")


@pytest.mark.flaky(reruns=2)
def test_set_redshift_via_comments_and_history(driver, user, public_source):
    if "TRAVIS" in os.environ:
        pytest.xfail("Xfailing this test on Travis builds.")
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_box = driver.wait_for_xpath("//input[@name='text']")
    comment_text = "z=0.3131"
    comment_box.send_keys(comment_text)
    driver.click_xpath('//*[@name="submitCommentButton"]')

    driver.click_xpath(
        "//*[@data-testid='redshiftHistoryIconButton']", wait_clickable=False
    )
    driver.wait_for_xpath("//th[text()='Set By']")
    driver.wait_for_xpath("//td[text()='0.3131']")
    driver.wait_for_xpath(f"//td[text()='{user.username}']")
