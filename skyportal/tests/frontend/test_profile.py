import pytest
from selenium.webdriver.support.ui import Select
import time


def test_token_acls_options_rendering1(driver, user):
    driver.get(f'/become_user/{user.id}')
    driver.get('/profile')
    driver.wait_for_xpath('//input[@name="acls[0]"]')
    driver.wait_for_xpath('//input[@name="acls[1]"]')
    driver.wait_for_xpath('//input[@name="acls[2]"]')
    driver.wait_for_xpath_to_disappear('//input[@name="acls[3]"]')


def test_token_acls_options_rendering2(driver, super_admin_user):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/profile')
    for i in range(5):
        driver.wait_for_xpath(f'//input[@name="acls[{i}]"]')
