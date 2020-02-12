import pytest
import uuid
import os
from os.path import join as pjoin
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
import requests
import numpy.testing as npt

from skyportal.models import Source, DBSession
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
    comment_text = 'Test comment'
    comment_box.send_keys(comment_text)
    driver.find_element_by_css_selector('[type=submit]').click()
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
    comment_text = 'Test comment'
    comment_box.send_keys(comment_text)
    attachment_file = driver.find_element_by_css_selector('input[type=file]')
    attachment_file.send_keys(pjoin(os.path.dirname(os.path.dirname(__file__)),
                                    'data', 'spec.csv'))
    driver.find_element_by_css_selector('[type=submit]').click()
    driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
    driver.wait_for_xpath('//a[text()="spec.csv"]')


def test_download_comment_attachment(driver, user, public_source):
    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_box = driver.find_element_by_css_selector('[name=comment]')
    comment_text = 'Test comment'
    comment_box.send_keys(comment_text)
    attachment_file = driver.find_element_by_css_selector('input[type=file]')
    attachment_file.send_keys(pjoin(os.path.dirname(os.path.dirname(__file__)),
                                    'data', 'spec.csv'))
    driver.find_element_by_css_selector('[type=submit]').click()
    driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
    driver.wait_for_xpath('//a[text()="spec.csv"]').click()
    time.sleep(0.5)
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
    comment_text = 'Test comment'
    comment_box.send_keys(comment_text)
    driver.find_element_by_css_selector('[type=submit]').click()
    driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
    driver.wait_for_xpath('//span[contains(@class,"commentTime")]')
    driver.wait_for_xpath('//button[text()="Delete Comment"]').click()
    driver.wait_for_xpath_to_disappear(f'//div[text()="{comment_text}"]')


def test_regular_user_cannot_delete_unowned_comment(driver, super_admin_user,
                                                    user, public_source):
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_box = driver.find_element_by_css_selector('[name=comment]')
    comment_text = 'Test comment'
    comment_box.send_keys(comment_text)
    driver.find_element_by_css_selector('[type=submit]').click()
    driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
    driver.wait_for_xpath('//span[contains(@class,"commentTime")]')
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    driver.wait_for_xpath_to_disappear('//button[text()="Delete Comment"]', timeout=0)


def test_super_user_can_delete_unowned_comment(driver, super_admin_user,
                                               user, public_source):
    driver.get(f"/become_user/{user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    comment_box = driver.find_element_by_css_selector('[name=comment]')
    comment_text = 'Test comment'
    comment_box.send_keys(comment_text)
    driver.find_element_by_css_selector('[type=submit]').click()
    driver.wait_for_xpath(f'//div[text()="{comment_text}"]')
    driver.wait_for_xpath('//span[contains(@class,"commentTime")]')
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    driver.wait_for_xpath('//button[text()="Delete Comment"]')
