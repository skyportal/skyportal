import os
from os.path import join as pjoin
import uuid
import pytest
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException

from baselayer.app.config import load_config


cfg = load_config()


def test_public_source_page(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    driver.wait_for_xpath('//label[contains(text(), "band")]')  # TODO how to check plot?
    driver.wait_for_xpath('//label[contains(text(), "Fe III")]')


@pytest.mark.flaky(reruns=2)
def test_comments(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_box = driver.wait_for_xpath("//input[@name='text']")
    comment_text = str(uuid.uuid4())
    comment_box.send_keys(comment_text)
    driver.scroll_to_element_and_click(
        driver.find_element_by_xpath('//*[@name="submitCommentButton"]'))
    try:
        driver.wait_for_xpath(f'//div[text()="{comment_text}"]', timeout=30)
        driver.wait_for_xpath('//span[text()="a few seconds ago"]')
    except TimeoutException:
        driver.refresh()
        comment_box = driver.wait_for_xpath("//input[@name='text']")
        comment_text = str(uuid.uuid4())
        comment_box.send_keys(comment_text)
        driver.scroll_to_element_and_click(
            driver.find_element_by_xpath('//*[@name="submitCommentButton"]'))
        driver.wait_for_xpath(f'//div[text()="{comment_text}"]', timeout=30)
        driver.wait_for_xpath('//span[text()="a few seconds ago"]')


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
    driver.scroll_to_element_and_click(
        driver.find_element_by_xpath('//*[@name="submitCommentButton"]'))
    driver.wait_for_xpath('//div[contains(.,"Select at least one group")]')
    group_checkbox.click()
    driver.wait_for_xpath_to_disappear('//div[contains(.,"Select at least one group")]')
    driver.scroll_to_element_and_click(
        driver.find_element_by_xpath('//*[@name="submitCommentButton"]'))
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
    attachment_file.send_keys(pjoin(os.path.dirname(os.path.dirname(__file__)),
                                    'data', 'spec.csv'))
    driver.scroll_to_element_and_click(
        driver.find_element_by_xpath('//*[@name="submitCommentButton"]'))
    try:
        comment_text_div = driver.wait_for_xpath(f'//div[text()="{comment_text}"]', timeout=30)
    except TimeoutException:
        driver.refresh()
        comment_text_div = driver.wait_for_xpath(f'//div[text()="{comment_text}"]', timeout=30)
    comment_div = comment_text_div.find_element_by_xpath("..")
    driver.execute_script("arguments[0].scrollIntoView();", comment_div)
    ActionChains(driver).move_to_element(comment_div).perform()
    download_link = driver.wait_for_xpath_to_be_clickable('//a[text()="spec.csv"]')
    driver.execute_script("arguments[0].click();", download_link)
    fpath = str(os.path.abspath(pjoin(cfg['paths.downloads_folder'], 'spec.csv')))
    try_count = 1
    while not os.path.exists(fpath) and try_count <= 3:
        try_count += 1
        driver.execute_script("arguments[0].scrollIntoView();", comment_div)
        ActionChains(driver).move_to_element(comment_div).perform()
        driver.execute_script("arguments[0].click();", download_link)
        if os.path.exists(fpath):
            break
    else:
        assert os.path.exists(fpath)

    try:
        with open(fpath) as f:
            l = f.read()
        assert l.split('\n')[0] == 'wavelength,flux,instrument_id'
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
    driver.scroll_to_element_and_click(
        driver.find_element_by_xpath('//*[@name="submitCommentButton"]'))
    try:
        comment_text_div = driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
    except TimeoutException:
        driver.refresh()
        comment_text_div = driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
    comment_div = comment_text_div.find_element_by_xpath("..")
    comment_id = comment_div.get_attribute("name").split("commentDiv")[-1]
    delete_button = comment_div.find_element_by_xpath(
        f"//*[@name='deleteCommentButton{comment_id}']")
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
                f"//*[@name='deleteCommentButton{comment_id}']")
            driver.execute_script("arguments[0].scrollIntoView();", comment_div)
            ActionChains(driver).move_to_element(comment_div).perform()
            driver.execute_script("arguments[0].click();", delete_button)
            driver.wait_for_xpath_to_disappear(f'//div[text()="{comment_text}"]')


@pytest.mark.flaky(reruns=2)
def test_regular_user_cannot_delete_unowned_comment(driver, super_admin_user,
                                                    user, public_source):
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
        f"//*[@name='deleteCommentButton{comment_id}']")
    driver.execute_script("arguments[0].scrollIntoView();", comment_div)
    ActionChains(driver).move_to_element(comment_div).perform()
    assert not delete_button.is_displayed()


@pytest.mark.flaky(reruns=2)
def test_super_user_can_delete_unowned_comment(driver, super_admin_user,
                                               user, public_source):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_box = driver.wait_for_xpath("//input[@name='text']")
    comment_text = str(uuid.uuid4())
    comment_box.send_keys(comment_text)
    driver.scroll_to_element_and_click(
        driver.find_element_by_xpath('//*[@name="submitCommentButton"]'))
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
        f"//*[@name='deleteCommentButton{comment_id}']")
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
