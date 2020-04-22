import uuid
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
import time

import skyportal
from skyportal.tests import api


def test_source_list(driver, user, public_source, private_source):
    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?
    assert 'localhost' in driver.current_url
    driver.get('/')
    driver.wait_for_xpath("//div[contains(@title,'connected')]")
    driver.wait_for_xpath('//h2[contains(text(), "Sources")]')
    driver.wait_for_xpath(f'//a[text()="{public_source.id}"]')
    driver.wait_for_xpath(f'//td[text()="{public_source.simbad_class}"]')
    driver.wait_for_xpath_to_disappear(f'//a[text()="{private_source.id}"]')
    el = driver.wait_for_xpath('//button[text()="View Next 100 Sources"]')
    assert not el.is_enabled()
    el = driver.wait_for_xpath('//button[text()="View Previous 100 Sources"]')
    assert not el.is_enabled()


def test_source_filtering_and_pagination(driver, user, public_group, upload_data_token):
    source_id = str(uuid.uuid4())
    for i in range(205):
        status, data = api('POST', 'sources',
                           data={'id': f'{source_id}_{i}',
                                 'ra': 234.22,
                                 'dec': -22.33,
                                 'redshift': 3,
                                 'simbad_class': 'RRLyr',
                                 'transient': False,
                                 'ra_dis': 2.3,
                                 'group_ids': [public_group.id]},
                           token=upload_data_token)
        assert status == 200
        assert data['data']['id'] == f'{source_id}_{i}'

    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?
    assert 'localhost' in driver.current_url
    driver.get('/')
    driver.wait_for_xpath("//div[contains(@title,'connected')]")
    driver.wait_for_xpath('//h2[contains(text(), "Sources")]')
    driver.wait_for_xpath(f'//td[text()="RRLyr"]')
    # Pagination
    next_button = driver.wait_for_xpath('//button[text()="View Next 100 Sources"]')
    prev_button = driver.wait_for_xpath('//button[text()="View Previous 100 Sources"]')
    assert next_button.is_enabled()
    assert not prev_button.is_enabled()
    next_button.click()
    time.sleep(0.5)
    assert prev_button.is_enabled()
    next_button.click()
    time.sleep(0.5)
    assert not next_button.is_enabled()
    prev_button.click()
    time.sleep(0.5)
    assert next_button.is_enabled()
    prev_button.click()
    time.sleep(0.5)
    assert not prev_button.is_enabled()
    # Jump to page
    jump_to_page_input = driver.wait_for_xpath("//input[@name='jumpToPageInputField']")
    jump_to_page_input.clear()
    jump_to_page_input.send_keys('3')
    jump_to_page_button = driver.wait_for_xpath('//button[text()="Jump to page:"]')
    jump_to_page_button.click()
    time.sleep(0.5)
    #driver.wait_for_xpath('//div[contains(text(), "Displaying 1-100")]')
    assert prev_button.is_enabled()
    assert not next_button.is_enabled()
    jump_to_page_input.clear()
    jump_to_page_input.send_keys('1')
    jump_to_page_button.click()
    time.sleep(0.5)
    assert next_button.is_enabled()
    assert not prev_button.is_enabled()
    # Source filtering
    assert next_button.is_enabled()
    source_id = driver.wait_for_xpath("//input[@name='sourceID']")
    source_id.clear()
    source_id.send_keys('aaaa')
    submit = driver.wait_for_xpath("//input[@id='submitQueryButton']")
    submit.click()
    time.sleep(1)
    assert not next_button.is_enabled()


def test_jump_to_page_invalid_values(driver):
    driver.get('/')
    jump_to_page_input = driver.wait_for_xpath("//input[@name='jumpToPageInputField']")
    jump_to_page_input.clear()
    jump_to_page_input.send_keys('3')
    jump_to_page_button = driver.wait_for_xpath('//button[text()="Jump to page:"]')
    jump_to_page_button.click()
    driver.wait_for_xpath('//div[contains(.,"Backend error: Page number out of range")]')
    jump_to_page_input.clear()
    jump_to_page_input.send_keys('0')
    jump_to_page_button.click()
    driver.wait_for_xpath('//div[contains(.,"Backend error: Page number out of range")]')
    jump_to_page_input.clear()
    jump_to_page_input.send_keys('abc')
    jump_to_page_button.click()
    driver.wait_for_xpath('//div[contains(.,"Backend error: Invalid page number value")]')


def test_skyportal_version_displayed(driver):
    driver.get('/')
    driver.wait_for_xpath(f"//div[contains(.,'SkyPortal v{skyportal.__version__}')]")
