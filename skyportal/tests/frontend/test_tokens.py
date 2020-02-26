import pytest
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
import uuid


def test_add_token(driver, user, public_group):
    token_name = str(uuid.uuid4())
    driver.get(f'/become_user/{user.id}')
    driver.get('/profile')
    driver.wait_for_xpath('//input[@name="acls_Comment"]').click()
    driver.wait_for_xpath('//input[@name="acls_Upload data"]').click()
    group_select = Select(driver.wait_for_xpath('//select[@name="group_id"]'))
    group_select.select_by_value(str(public_group.id))
    driver.wait_for_xpath('//input[@name="name"]').send_keys(token_name)
    driver.wait_for_xpath('//input[@value="Generate Token"]').click()
    driver.wait_for_xpath(f'//td[contains(.,"{token_name}")]')


def test_delete_token(driver, user, public_group, view_only_token):
    driver.get(f'/become_user/{user.id}')
    driver.get('/profile')
    driver.wait_for_xpath(f'//input[@value="{view_only_token}"]')
    driver.wait_for_xpath('//a[contains(text(),"Delete")]').click()
    driver.wait_for_xpath_to_disappear(f'//input[@value="{view_only_token}"]')


def test_add_duplicate_token_error_message(driver, user, public_group):
    token_name = str(uuid.uuid4())
    driver.get(f'/become_user/{user.id}')
    driver.get('/profile')
    driver.wait_for_xpath('//input[@name="acls_Comment"]').click()
    driver.wait_for_xpath('//input[@name="acls_Upload data"]').click()
    group_select = Select(driver.wait_for_xpath('//select[@name="group_id"]'))
    group_select.select_by_value(str(public_group.id))
    driver.wait_for_xpath('//input[@name="name"]').send_keys(token_name)
    driver.wait_for_xpath('//input[@value="Generate Token"]').click()
    driver.wait_for_xpath(f'//td[contains(.,"{token_name}")]')

    driver.wait_for_xpath('//input[@name="acls_Comment"]').click()
    driver.wait_for_xpath('//input[@name="acls_Upload data"]').click()
    group_select.select_by_value(str(public_group.id))
    driver.wait_for_xpath('//input[@name="name"]').send_keys(token_name)
    driver.wait_for_xpath('//input[@value="Generate Token"]').click()
    driver.wait_for_xpath('//div[contains(.,"Backend error: Duplicate token name")]')
