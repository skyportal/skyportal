import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By


def test_source_page(driver, user, public_source):
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
