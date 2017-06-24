import pytest
from selenium import webdriver


def test_front_page(driver):
    driver.get("/")
    assert 'localhost' in driver.current_url
    driver.wait_for_xpath("//div[contains(@title,'connected')]")
    driver.wait_for_xpath('//h1[contains(text(), SkyPortal)]')
