import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
import uuid
import time


def test_user_info(driver, user):
    driver.get(f'/become_user/{user.id}')
    driver.get(f'/user/{user.id}')
    driver.wait_for_xpath(f'//div[contains(.,"{user.username}")]')
    driver.wait_for_xpath('//li[contains(.,"<b>created_at:</b>")]')
    for acl in user.acls:
        driver.wait_for_xpath(f'//li[contains(.,"{acl}")]')
