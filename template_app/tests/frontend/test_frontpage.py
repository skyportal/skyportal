import pytest
from selenium import webdriver


def test_front_page(driver):
    driver.get("/")
    assert 'localhost' in driver.current_url
    button = driver.wait_for_xpath("//div[contains(@title,'connected')]")
    link = driver.find_element_by_partial_link_text('Click here')
    link.click()
    driver.wait_for_xpath("//div[contains(text(),'Hello')]")
