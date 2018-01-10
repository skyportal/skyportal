import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
import uuid
import time


def test_public_groups_list(driver, user, public_group):
    driver.get(f'/become_user/{user.id}')  # TODO decorator/context manager?
    driver.get('/groups')
    driver.wait_for_xpath('//h2[text()="My Groups"]')
    driver.wait_for_xpath(f'//a[contains(.,"{public_group.name}")]')


def test_super_admin_groups_list(driver, super_admin_user, public_group):
    driver.get(f'/become_user/{super_admin_user.id}')  # TODO decorator/context manager?
    driver.get('/groups')
    driver.wait_for_xpath('//h2[text()="All Groups"]')
    driver.wait_for_xpath(f'//a[contains(.,"{public_group.name}")]')
    # TODO: Make sure ALL groups are actually displayed here - not sure how to
    # get list of names of previously created groups here


def test_add_new_group(driver, super_admin_user, user):
    test_proj_name = str(uuid.uuid4())
    driver.get(f'/become_user/{super_admin_user.id}')  # TODO decorator/context manager?
    driver.get('/')
    driver.refresh()
    driver.get('/groups')
    driver.wait_for_xpath('//input[@name="groupName"]').send_keys(test_proj_name)
    driver.wait_for_xpath('//input[@name="groupAdmins"]').send_keys(user.username)
    driver.save_screenshot('/tmp/screenshot1.png')
    driver.wait_for_xpath('//input[@value="Create Group"]').click()
    try:
        driver.wait_for_xpath(f'//a[contains(.,"{test_proj_name}")]')
    except:
        driver.save_screenshot('/tmp/screenshot2.png')
        raise
