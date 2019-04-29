import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
import uuid
import time
import requests

from skyportal.model_util import create_token


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
    driver.wait_for_xpath('//input[@name="name"]').send_keys(test_proj_name)
    driver.wait_for_xpath('//input[@name="groupAdmins"]').send_keys(user.username)
    driver.save_screenshot('/tmp/screenshot1.png')
    driver.wait_for_xpath('//input[@value="Create Group"]').click()
    try:
        driver.wait_for_xpath(f'//a[contains(.,"{test_proj_name}")]')
    except:
        driver.save_screenshot('/tmp/screenshot2.png')
        raise


def test_add_new_group_user_admin(driver, super_admin_user, user, public_group):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h2[text()="All Groups"]')
    driver.wait_for_xpath(f'//a[contains(.,"{public_group.name}")]').click()
    driver.wait_for_xpath(f'//a[contains(.,"{user.username}")]/../input').click()
    time.sleep(0.5)
    driver.wait_for_xpath('//input[@id="newUserEmail"]').send_keys(user.username)
    driver.wait_for_xpath('//input[@type="checkbox"]').click()
    driver.wait_for_xpath('//input[@value="Add user"]').click()
    driver.wait_for_xpath(f'//a[contains(.,"{user.username}")]')
    print(user.username)
    assert len(driver.find_elements_by_xpath(
        f'//a[contains(.,"{user.username}")]/..//span')) == 1


def test_add_new_group_user_nonadmin(driver, super_admin_user, user, public_group):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h2[text()="All Groups"]')
    driver.wait_for_xpath(f'//a[contains(.,"{public_group.name}")]').click()
    driver.wait_for_xpath(f'//a[contains(.,"{user.username}")]/../input').click()
    time.sleep(0.5)
    driver.wait_for_xpath('//input[@id="newUserEmail"]').send_keys(user.username)
    driver.wait_for_xpath('//input[@value="Add user"]').click()
    driver.wait_for_xpath(f'//a[contains(.,"{user.username}")]')
    assert len(driver.find_elements_by_xpath(
        f'//a[contains(.,"{user.username}")]/..//span')) == 0


def test_delete_group_user(driver, super_admin_user, user, public_group):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h2[text()="All Groups"]')
    driver.wait_for_xpath(f'//a[contains(.,"{public_group.name}")]').click()
    driver.wait_for_xpath(f'//a[contains(.,"{user.username}")]/../input').click()
    time.sleep(0.5)
    assert len(driver.find_elements_by_xpath(
        f'//a[contains(.,"{user.username}")]')) == 0


def test_token_user_update_group(driver, super_admin_user, public_group):
    auth_token = create_token(public_group.id, ['Manage groups'])
    response = requests.put(
        f'{driver.server_url}/api/groups/{public_group.id}',
        json={'name': 'new name'},
        headers={'Authorization': f'token {auth_token}'}
    ).json()
    assert response['status'] == 'success'

    response = requests.get(
        f'{driver.server_url}/api/groups/{public_group.id}',
        headers={'Authorization': f'token {auth_token}'}
    ).json()
    assert response['status'] == 'success'
    assert response['data']['name'] == 'new name'
