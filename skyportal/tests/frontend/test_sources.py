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
from skyportal.tests import api
from skyportal.models import DBSession


cfg = load_config()


def enter_comment_text(driver, comment_text):
    comment_xpath = "//div[@data-testid='comments-accordion']//input[@name='text']"
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
        driver.wait_for_xpath(f'//p[text()="{comment_text}"]', timeout=20)
    except TimeoutException:
        driver.refresh()
        driver.wait_for_xpath(f'//p[text()="{comment_text}"]')


@pytest.mark.flaky(reruns=2)
def test_public_source_page(driver, user, public_source, public_group):
    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    driver.wait_for_xpath('//*[text()="Export Bold Light Curve to CSV"]', 20)
    driver.wait_for_xpath('//span[contains(text(), "Fe III")]')
    driver.wait_for_xpath(f'//span[text()="{public_group.name}"]')


@pytest.mark.flaky(reruns=2)
def test_public_source_page_null_z(driver, user, public_source, public_group):
    public_source.redshift = None
    DBSession().add(public_source)
    DBSession().commit()

    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    driver.wait_for_xpath('//*[text()="Export Bold Light Curve to CSV"]', 20)
    driver.wait_for_xpath('//span[contains(text(), "Fe III")]')
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
    driver.click_xpath('//div[@id="root_taxonomy"]')
    driver.click_xpath(
        f'//*[text()="{tax_name} ({tax_version})"]',
        wait_clickable=False,
        scroll_parent=True,
    )
    driver.click_xpath('//*[@id="classification"]')
    driver.click_xpath('//li[contains(@data-value, "Symmetrical")]', scroll_parent=True)
    driver.click_xpath('//*[@id="probability"]')
    driver.wait_for_xpath('//*[@id="probability"]').send_keys("1", Keys.ENTER)
    driver.click_xpath(
        "//*[@id='classifications-content']//span[text()='Submit']",
        wait_clickable=False,
    )
    # Notification
    driver.wait_for_xpath("//*[text()='Classification saved']")

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
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_text = str(uuid.uuid4())
    add_comment_and_wait_for_display(driver, comment_text)


@pytest.mark.flaky(reruns=2)
def test_comment_groups_validation(
    driver, user, super_admin_token, public_source, public_group
):
    _, data = api("GET", "groups/public", token=super_admin_token)
    sitewide_group_id = data["data"]["id"]
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_text = str(uuid.uuid4())
    enter_comment_text(driver, comment_text)
    driver.click_xpath(
        "//div[@data-testid='comments-accordion']//*[text()='Customize Group Access']"
    )

    # sitewide_group
    group_checkbox_xpath = f"//div[@data-testid='comments-accordion']//*[@data-testid='commentGroupCheckBox{sitewide_group_id}']"
    driver.click_xpath(group_checkbox_xpath, wait_clickable=False)

    # public_group that user belongs to
    group_checkbox_xpath = f"//div[@data-testid='comments-accordion']//*[@data-testid='commentGroupCheckBox{public_group.id}']"
    driver.click_xpath(group_checkbox_xpath, wait_clickable=False)
    driver.click_xpath(
        '//div[@data-testid="comments-accordion"]//*[@name="submitCommentButton"]'
    )
    driver.wait_for_xpath(
        '//div[@data-testid="comments-accordion"]//div[contains(.,"Select at least one group")]'
    )
    driver.click_xpath(group_checkbox_xpath, wait_clickable=False)
    driver.click_xpath(
        '//div[@data-testid="comments-accordion"]//*[@name="submitCommentButton"]'
    )
    driver.wait_for_xpath_to_disappear(
        '//div[@data-testid="comments-accordion"]//div[contains(.,"Select at least one group")]'
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


@pytest.mark.flaky(reruns=2)
def test_upload_download_comment_attachment(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_text = str(uuid.uuid4())
    enter_comment_text(driver, comment_text)
    # attachment_file = driver.find_element_by_css_selector('input[type=file]')
    attachment_file = driver.wait_for_xpath(
        "//div[@data-testid='comments-accordion']//input[@name='attachment']"
    )
    attachment_file.send_keys(
        pjoin(os.path.dirname(os.path.dirname(__file__)), 'data', 'spec.csv')
    )
    driver.click_xpath(
        '//div[@data-testid="comments-accordion"]//*[@name="submitCommentButton"]'
    )
    try:
        comment_text_p = driver.wait_for_xpath(
            f'//div[@data-testid="comments-accordion"]//p[text()="{comment_text}"]',
            timeout=20,
        )
    except TimeoutException:
        driver.refresh()
        comment_text_p = driver.wait_for_xpath(
            f'//div[@data-testid="comments-accordion"]//p[text()="{comment_text}"]'
        )
    comment_div = comment_text_p.find_element_by_xpath("../..")
    driver.execute_script("arguments[0].scrollIntoView();", comment_div)
    ActionChains(driver).move_to_element(comment_div).perform()

    # Scroll up to top of comments list
    comments = driver.wait_for_xpath(
        "//div[@data-testid='comments-accordion']//p[text()='Comments']"
    )
    driver.scroll_to_element(comments)

    attachment_div = driver.wait_for_xpath(
        "//div[@data-testid='comments-accordion']//div[contains(text(), 'Attachment:')]"
    )
    attachment_button = driver.wait_for_xpath(
        '//div[@data-testid="comments-accordion"]//button[@data-testid="attachmentButton_spec"]'
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
    comment_text = str(uuid.uuid4())
    add_comment_and_wait_for_display(driver, comment_text)
    comment_text_p = driver.wait_for_xpath(f'//p[text()="{comment_text}"]')
    comment_div = comment_text_p.find_element_by_xpath("../..")
    comment_id = comment_div.get_attribute("name").split("commentDiv")[-1]
    delete_button = comment_div.find_element_by_xpath(
        f"//*[@name='deleteCommentButton{comment_id}']"
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
            comment_div = comment_text_div.find_element_by_xpath("..")
            comment_id = comment_div.get_attribute("name").split("commentDiv")[-1]
            delete_button = comment_div.find_element_by_xpath(
                f"//*[@name='deleteCommentButton{comment_id}']"
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
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_text = str(uuid.uuid4())
    add_comment_and_wait_for_display(driver, comment_text)
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    comment_text_p = driver.wait_for_xpath(f'//p[text()="{comment_text}"]')
    comment_div = comment_text_p.find_element_by_xpath("../..")
    comment_id = comment_div.get_attribute("name").split("commentDiv")[-1]
    delete_button = comment_div.find_element_by_xpath(
        f"//*[@name='deleteCommentButton{comment_id}']"
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
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_text = str(uuid.uuid4())
    add_comment_and_wait_for_display(driver, comment_text)

    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/source/{public_source.id}")

    comment_text_p = driver.wait_for_xpath(f'//p[text()="{comment_text}"]')
    comment_div = comment_text_p.find_element_by_xpath("../..")
    comment_id = comment_div.get_attribute("name").split("commentDiv")[-1]

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
    button = driver.wait_for_xpath('//span[text()="Show Starlist"]')
    button.click()
    driver.wait_for_xpath("//code/div/pre[text()[contains(., '_o1')]]", timeout=45)


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

        difference = ImageChops.difference(
            generated_plot.convert('RGB'), expected_plot.convert('RGB')
        )
        assert difference.getbbox() is None


def test_dropdown_facility_change(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?
    driver.get(f"/source/{public_source.id}")
    driver.click_xpath('//*[text()="Show Starlist"]')
    driver.wait_for_xpath("//code/div/pre[text()[contains(., 'raoffset')]]", timeout=45)
    driver.click_xpath('//*[@id="mui-component-select-StarListSelectElement"]')
    driver.click_xpath('//li[@data-value="P200"]')
    driver.wait_for_xpath("//code/div/pre[text()[contains(., 'dist')]]", timeout=45)


@pytest.mark.flaky(reruns=2)
def test_source_notification(driver, user, public_group, public_source):
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
    driver.click_xpath(
        f'//*[@data-testid="unsaveGroupCheckbox_{public_group2.id}"]',
        scroll_parent=True,
    )
    driver.click_xpath(f'//button[@name="editSourceGroupsButton_{public_source.id}"]')
    driver.wait_for_xpath('//*[text()="Source groups updated successfully"]')
    driver.wait_for_xpath_to_disappear(
        f'//div[@data-testid="groupChip_{public_group2.id}"]'
    )


@pytest.mark.flaky(reruns=2)
def test_request_group_to_save_then_save(
    driver, user, user_two_groups, public_source, public_group2
):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    driver.click_xpath(f'//*[@data-testid="editGroups_{public_source.id}"]')
    driver.click_xpath(
        f'//*[@data-testid="inviteGroupCheckbox_{public_group2.id}"]',
        scroll_parent=True,
    )
    driver.click_xpath(
        f'//button[@name="editSourceGroupsButton_{public_source.id}"]',
        scroll_parent=True,
    )
    driver.wait_for_xpath('//*[text()="Source groups updated successfully"]')
    driver.get(f"/become_user/{user_two_groups.id}")
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
        "//*[@data-testid='redshiftHistoryIconButton']", wait_clickable=False
    )
    driver.wait_for_xpath("//th[text()='Set By']")
    driver.wait_for_xpath("//td[text()='0.9999']")
    driver.wait_for_xpath("//td[text()='0.0001']")
    driver.wait_for_xpath(f"//td[text()='{user.username}']")


def test_update_redshift_and_history_without_error(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
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


def test_obj_page_unsaved_source(public_obj, driver, user):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_obj.id}")

    # wait for the plots to load
    driver.wait_for_xpath('//*[text()="Export Bold Light Curve to CSV"]', 20)
    # this waits for the spectroscopy plot by looking for the element Mg
    driver.wait_for_xpath('//span[text()="Mg I"]', timeout=20)

    driver.wait_for_xpath_to_disappear('//div[contains(@data-testid, "groupChip")]')


def test_show_photometry_table(public_source, driver, user):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")

    # wait for the plots to load
    driver.wait_for_xpath('//*[text()="Export Bold Light Curve to CSV"]', 20)
    # this waits for the spectroscopy plot by looking for the element Mg
    driver.wait_for_xpath('//span[text()="Mg I"]')

    driver.click_xpath('//*[@data-testid="show-photometry-table-button"]')
    driver.wait_for_xpath(f'//*[contains(text(), "Photometry of {public_source.id}")]')

    driver.click_xpath('//*[@data-testid="close-photometry-table-button"]')
    driver.wait_for_xpath_to_disappear(
        '//*[@data-testid="close-photometry-table-button"]'
    )


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
        'annotation',
        data={
            'obj_id': public_source.id,
            'origin': 'cross_match1',
            'data': {
                'gaia': {'Mag_G': 11.3, 'Mag_Bp': 11.8, 'Mag_Rp': 11.0, 'Plx': 20}
            },
        },
        token=annotation_token,
    )
    assert status == 200

    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    driver.wait_for_xpath('//*[text()="Export Bold Light Curve to CSV"]', 20)
    driver.wait_for_xpath('//span[contains(text(), "Fe III")]')

    driver.wait_for_xpath('//*[@id="hr-diagram-content"]')

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
        # generated_plot.save(expected_plot_path)

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
    driver.click_xpath(f'//button//span[text()="{obj_id2}"]')
    driver.wait_for_xpath(f'//div[text()="{obj_id2}"]')
