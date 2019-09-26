import pytest
from selenium.webdriver.support.ui import Select
import time


def test_token_acls_options_rendering1(driver, user):
    driver.get(f'/become_user/{user.id}')
    driver.get('/profile')
    driver.wait_for_xpath('//input[@name="acls_Comment"]')
    driver.wait_for_xpath('//input[@name="acls_Upload data"]')
    driver.wait_for_xpath_to_disappear('//input[@name="acls_Manage sources"]')

def test_token_acls_options_rendering2(driver, super_admin_user):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/profile')
    driver.wait_for_xpath('//input[@name="acls_Comment"]')
    driver.wait_for_xpath('//input[@name="acls_Upload data"]')
    driver.wait_for_xpath('//input[@name="acls_Manage sources"]')
    driver.wait_for_xpath('//input[@name="acls_Manage groups"]')
    driver.wait_for_xpath('//input[@name="acls_Become user"]')
    driver.wait_for_xpath('//input[@name="acls_System admin"]')
