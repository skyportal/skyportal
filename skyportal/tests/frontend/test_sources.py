import os
from os.path import join as pjoin
import time
import uuid
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

from baselayer.app.config import load_config


cfg = load_config()


def test_public_source_page(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    driver.wait_for_xpath('//label[contains(text(), "band")]')  # TODO how to check plot?
    driver.wait_for_xpath('//label[contains(text(), "Fe III")]')


def test_comments(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_box = driver.find_element_by_css_selector('[name=comment]')
    comment_text = str(uuid.uuid4())
    comment_box.send_keys(comment_text)
    driver.scroll_to_element_and_click(driver.find_element_by_css_selector('[type=submit]'))
    driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
    driver.wait_for_xpath('//span[contains(@class,"commentTime")]')
    timestamp_text = driver.find_element(By.XPATH,
                                         '//span[contains(@class,"commentTime")]').text
    assert timestamp_text == 'a few seconds ago'


def test_upload_comment_attachment(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_box = driver.find_element_by_css_selector('[name=comment]')
    comment_text = str(uuid.uuid4())
    comment_box.send_keys(comment_text)
    attachment_file = driver.find_element_by_css_selector('input[type=file]')
    attachment_file.send_keys(pjoin(os.path.dirname(os.path.dirname(__file__)),
                                    'data', 'spec.csv'))
    driver.scroll_to_element_and_click(driver.find_element_by_css_selector('[type=submit]'))
    driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
    driver.wait_for_xpath('//a[text()="spec.csv"]')


def test_download_comment_attachment(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_box = driver.find_element_by_css_selector('[name=comment]')
    comment_text = str(uuid.uuid4())
    comment_box.send_keys(comment_text)
    attachment_file = driver.find_element_by_css_selector('input[type=file]')
    attachment_file.send_keys(pjoin(os.path.dirname(os.path.dirname(__file__)),
                                    'data', 'spec.csv'))
    driver.scroll_to_element_and_click(driver.find_element_by_css_selector('[type=submit]'))
    comment_text_div = driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
    comment_div = comment_text_div.find_element_by_xpath("..")
    driver.execute_script("arguments[0].scrollIntoView();", comment_div)
    ActionChains(driver).move_to_element(comment_div).perform()
    time.sleep(0.1)
    driver.wait_for_xpath_to_be_clickable('//a[text()="spec.csv"]').click()
    time.sleep(1)
    fpath = str(os.path.abspath(pjoin(cfg['paths.downloads_folder'], 'spec.csv')))
    assert(os.path.exists(fpath))
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
    driver.wait_for_xpath_to_disappear('//input[@name="comment"]')


def test_delete_comment(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_box = driver.find_element_by_css_selector('[name=comment]')
    comment_text = str(uuid.uuid4())
    comment_box.send_keys(comment_text)
    driver.scroll_to_element_and_click(driver.find_element_by_css_selector('[type=submit]'))
    comment_text_div = driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
    comment_div = comment_text_div.find_element_by_xpath("..")
    driver.execute_script("arguments[0].scrollIntoView();", comment_div)
    ActionChains(driver).move_to_element(comment_div).perform()
    time.sleep(0.1)
    delete_button = comment_div.find_element_by_tag_name("button")
    assert delete_button.is_displayed()
    delete_button.click()
    driver.wait_for_xpath_to_disappear(f'//div[text()="{comment_text}"]')


def test_regular_user_cannot_delete_unowned_comment(driver, super_admin_user,
                                                    user, public_source):
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_box = driver.find_element_by_css_selector('[name=comment]')
    comment_text = str(uuid.uuid4())
    comment_box.send_keys(comment_text)
    submit_button = driver.find_element_by_css_selector('[type=submit]')
    driver.scroll_to_element_and_click(submit_button)
    comment_text_div = driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    comment_text_div = driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
    comment_div = comment_text_div.find_element_by_xpath("..")
    driver.execute_script("arguments[0].scrollIntoView();", comment_div)
    ActionChains(driver).move_to_element(comment_div).perform()
    time.sleep(0.1)
    delete_button = comment_div.find_element_by_tag_name("button")
    assert not delete_button.is_displayed()


def test_super_user_can_delete_unowned_comment(driver, super_admin_user,
                                               user, public_source):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_box = driver.find_element_by_css_selector('[name=comment]')
    comment_text = str(uuid.uuid4())
    comment_box.send_keys(comment_text)
    driver.scroll_to_element_and_click(driver.find_element_by_css_selector('[type=submit]'))
    comment_text_div = driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/source/{public_source.id}")
    comment_text_div = driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
    comment_div = comment_text_div.find_element_by_xpath("..")
    driver.execute_script("arguments[0].scrollIntoView();", comment_div)
    ActionChains(driver).move_to_element(comment_div).perform()
    time.sleep(0.1)
    delete_button = comment_div.find_element_by_tag_name("button")
    assert delete_button.is_displayed()
