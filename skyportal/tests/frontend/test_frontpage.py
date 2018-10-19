import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By


def test_front_page(driver, user, public_source, private_source):
    driver.get(f"/become_user/{user.id}")  # TODO decorator/context manager?
    assert 'localhost' in driver.current_url
    driver.wait_for_xpath("//div[contains(@title,'connected')]")
    driver.wait_for_xpath('//h2[contains(text(), "Sources")]')
    driver.wait_for_xpath(f'//a[text()="{public_source.id}"]')
    driver.wait_for_xpath(f'//td[text()="{public_source.simbad_class}"]')
    driver.wait_for_xpath_missing('//a[text()="{private_source.id}"]')
