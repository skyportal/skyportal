import uuid
import pytest
from selenium.webdriver.common.keys import Keys


def test_public_groups_list(driver, user, public_group):
    driver.get(f'/become_user/{user.id}')  # TODO decorator/context manager?
    driver.get('/groups')
    driver.wait_for_xpath('//h6[text()="My Groups"]')
    driver.wait_for_xpath(f'//a[contains(.,"{public_group.name}")]')


def test_super_admin_groups_list(driver, super_admin_user, public_group):
    driver.get(f'/become_user/{super_admin_user.id}')  # TODO decorator/context manager?
    driver.get('/groups')
    driver.wait_for_xpath('//h6[text()="All Groups"]')
    driver.wait_for_xpath(f'//a[contains(.,"{public_group.name}")]')
    # TODO: Make sure ALL groups are actually displayed here - not sure how to
    # get list of names of previously created groups here


@pytest.mark.flaky(reruns=2)
def test_add_new_group(driver, super_admin_user, user):
    test_proj_name = str(uuid.uuid4())
    driver.get(f'/become_user/{super_admin_user.id}')  # TODO decorator/context manager?
    driver.get('/')
    driver.refresh()
    driver.get('/groups')
    driver.wait_for_xpath('//input[@name="name"]').send_keys(test_proj_name)
    driver.wait_for_xpath('//input[@name="groupAdmins"]').send_keys(user.username)
    driver.save_screenshot('/tmp/screenshot1.png')
    driver.click_xpath('//input[@value="Create Group"]')
    driver.wait_for_xpath(f'//a[contains(.,"{test_proj_name}")]')


@pytest.mark.flaky(reruns=2)
def test_add_new_group_explicit_self_admin(driver, super_admin_user, user):
    test_proj_name = str(uuid.uuid4())
    driver.get(f'/become_user/{super_admin_user.id}')  # TODO decorator/context manager?
    driver.get('/')
    driver.refresh()
    driver.get('/groups')
    driver.wait_for_xpath('//input[@name="name"]').send_keys(test_proj_name)
    driver.wait_for_xpath('//input[@name="groupAdmins"]').send_keys(
        super_admin_user.username
    )
    driver.save_screenshot('/tmp/screenshot1.png')
    driver.click_xpath('//input[@value="Create Group"]')
    driver.wait_for_xpath(f'//a[contains(.,"{test_proj_name}")]')


def test_add_new_group_user_admin(driver, super_admin_user, user, public_group):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h6[text()="All Groups"]')
    el = driver.wait_for_xpath(f'//a[contains(.,"{public_group.name}")]')
    driver.execute_script("arguments[0].click();", el)
    driver.click_xpath(f'//a[contains(.,"{user.username}")]/../button')
    driver.wait_for_xpath('//input[@id="newUserEmail"]').send_keys(
        user.username, Keys.ENTER
    )
    driver.click_xpath('//input[@type="checkbox"]')
    driver.click_xpath('//input[@value="Add user"]')
    driver.wait_for_xpath(f'//a[contains(.,"{user.username}")]')
    assert (
        len(
            driver.find_elements_by_xpath(
                f'//a[contains(.,"{user.username}")]/..//span'
            )
        )
        == 1
    )


def test_add_new_group_user_nonadmin(driver, super_admin_user, user, public_group):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h6[text()="All Groups"]')
    el = driver.wait_for_xpath(f'//a[contains(.,"{public_group.name}")]')
    driver.execute_script("arguments[0].click();", el)
    driver.click_xpath(f'//a[contains(.,"{user.username}")]/../button')
    driver.wait_for_xpath('//input[@id="newUserEmail"]').send_keys(
        user.username, Keys.ENTER
    )
    driver.click_xpath('//input[@value="Add user"]')
    driver.wait_for_xpath(f'//a[contains(.,"{user.username}")]')
    assert (
        len(
            driver.find_elements_by_xpath(
                f'//a[contains(.,"{user.username}")]/..//span'
            )
        )
        == 0
    )


def test_add_new_group_user_new_username(driver, super_admin_user, user, public_group):
    new_username = str(uuid.uuid4())
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h6[text()="All Groups"]')
    el = driver.wait_for_xpath(f'//a[contains(.,"{public_group.name}")]')
    driver.execute_script("arguments[0].click();", el)
    driver.click_xpath(f'//a[contains(.,"{user.username}")]/../button')
    driver.wait_for_xpath('//input[@id="newUserEmail"]').send_keys(
        new_username, Keys.ENTER
    )
    driver.click_xpath('//input[@value="Add user"]')
    driver.wait_for_xpath(f'//a[contains(.,"{new_username}")]')


def test_delete_group_user(driver, super_admin_user, user, public_group):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h6[text()="All Groups"]')
    el = driver.wait_for_xpath(f'//a[contains(.,"{public_group.name}")]')
    driver.execute_script("arguments[0].click();", el)
    driver.click_xpath(f'//a[contains(.,"{user.username}")]/../button')
    assert (
        len(driver.find_elements_by_xpath(f'//a[contains(.,"{user.username}")]')) == 0
    )


def test_delete_group(driver, super_admin_user, user, public_group):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h6[text()="All Groups"]')
    el = driver.wait_for_xpath(f'//a[contains(.,"{public_group.name}")]')
    driver.execute_script("arguments[0].click();", el)
    driver.click_xpath('//input[@value="Delete Group"]')
    driver.wait_for_xpath('//div[contains(.,"Could not load group")]')
