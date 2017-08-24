import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By


def test_front_page(driver, public_source, private_source):
    driver.get("/")
    assert 'localhost' in driver.current_url
    driver.wait_for_xpath("//div[contains(@title,'connected')]")
    driver.wait_for_xpath('//h2[contains(text(), "List of Sources")]')
    driver.wait_for_xpath('//a[text()="public_source"]')
    driver.wait_for_xpath_missing('//a[text()="private_source"]')
