import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
import uuid
import time


def test_user_info(driver, super_admin_user):
    user = super_admin_user
    driver.get(f'/become_user/{user.id}')
    driver.get(f'/user/{user.id}')
    driver.wait_for_xpath(f'//div[contains(.,"{user.username}")]')
    pg_src = driver.page_source
    assert 'created_at:' in pg_src
    for acl in user.acls:
        assert acl.id in pg_src


def test_user_info_forbidden(driver, user):
    driver.get(f'/become_user/{user.id}')
    driver.get(f'/user/{user.id}')
    driver.wait_for_xpath('//div[contains(.,"Backend error")]')
