import pytest
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
import uuid


def test_add_token(driver, user, public_group):
    token_name = str(uuid.uuid4())
    driver.get(f'/become_user/{user.id}')
    driver.get('/profile')
    driver.wait_for_xpath('//input[@name="acls[0]"]').click()
    driver.wait_for_xpath('//input[@name="acls[1]"]').click()
    driver.wait_for_xpath('//input[@name="name"]').send_keys(token_name)
    driver.wait_for_xpath('//button[contains(.,"Generate Token")]').click()
    driver.wait_for_xpath(f'//td[contains(.,"{token_name}")]')


def test_delete_token(driver, user, public_group, view_only_token):
    driver.get(f'/become_user/{user.id}')
    driver.get('/profile')
    driver.wait_for_xpath(f'//input[@value="{view_only_token}"]')
    driver.scroll_to_element_and_click(driver.wait_for_xpath('//a[contains(text(),"Delete")]'))
    driver.wait_for_xpath_to_disappear(f'//input[@value="{view_only_token}"]')


def test_add_duplicate_token_error_message(driver, user, public_group):
    token_name = str(uuid.uuid4())
    driver.get(f'/become_user/{user.id}')
    driver.get('/profile')
    driver.wait_for_xpath('//input[@name="acls[0]"]').click()
    driver.wait_for_xpath('//input[@name="acls[1]"]').click()
    driver.wait_for_xpath('//input[@name="name"]').send_keys(token_name)
    driver.wait_for_xpath('//button[contains(.,"Generate Token")]').click()
    driver.wait_for_xpath(f'//td[contains(.,"{token_name}")]')

    driver.wait_for_xpath('//input[@name="name"]').send_keys(token_name)
    driver.wait_for_xpath('//button[contains(.,"Generate Token")]').click()
    driver.wait_for_xpath('//div[contains(.,"Duplicate token name")]')
