import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
import time


def test_front_page(driver, user, public_source, private_source):
    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?
    assert 'localhost' in driver.current_url
    driver.get('/')
    driver.wait_for_xpath("//div[contains(@title,'connected')]")
    driver.wait_for_xpath('//h2[contains(text(), "Sources")]')
    driver.wait_for_xpath(f'//a[text()="{public_source.id}"]')
    driver.wait_for_xpath(f'//td[text()="{public_source.simbad_class}"]')
    driver.wait_for_xpath_missing(f'//a[text()="{private_source.id}"]')
    driver.wait_for_xpath_missing('//button[text()="View Next 100 Sources"]')
    driver.wait_for_xpath_missing('//button[text()="View Previous 100 Sources"]')


def test_front_page_pagination(driver, user, public_sources_205):
    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?
    assert 'localhost' in driver.current_url
    driver.get('/')
    driver.wait_for_xpath("//div[contains(@title,'connected')]")
    driver.wait_for_xpath('//h2[contains(text(), "Sources")]')
    driver.wait_for_xpath(f'//td[text()="{public_sources_205[0].simbad_class}"]')
    next_button = driver.wait_for_xpath('//button[text()="View Next 100 Sources"]')
    driver.wait_for_xpath_missing('//button[text()="View Previous 100 Sources"]')
    next_button.click()
    time.sleep(1)
    prev_button = driver.wait_for_xpath('//button[text()="View Previous 100 Sources"]')
    next_button.click()
    time.sleep(1)
    driver.wait_for_xpath_missing('//button[text()="View Next 100 Sources"]')
    prev_button.click()
    time.sleep(1)
    driver.wait_for_xpath('//button[text()="View Next 100 Sources"]')
    prev_button.click()
    time.sleep(1)
    driver.wait_for_xpath_missing('//button[text()="View Previous 100 Sources"]')
