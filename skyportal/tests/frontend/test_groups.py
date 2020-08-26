import uuid
import pytest
from selenium.webdriver.common.keys import Keys


def test_public_groups_list(driver, user, public_group):
    driver.get(f'/become_user/{user.id}')  # TODO decorator/context manager?
    driver.get('/groups')
    driver.wait_for_xpath('//h5[text()="My Groups"]')
    driver.wait_for_xpath(f'//a[contains(.,"{public_group.name}")]')


def test_super_admin_groups_list(driver, super_admin_user, public_group):
    driver.get(f'/become_user/{super_admin_user.id}')  # TODO decorator/context manager?
    driver.get('/groups')
    driver.wait_for_xpath('//h5[text()="All Groups"]')
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


@pytest.mark.flaky(reruns=2)
def test_add_new_group_user_admin(
    driver, super_admin_user, user_no_groups, public_group
):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h5[text()="All Groups"]')
    el = driver.wait_for_xpath(f'//a[contains(.,"{public_group.name}")]')
    driver.execute_script("arguments[0].click();", el)
    el_input = driver.wait_for_xpath('//input[@id="newUserEmail"]', timeout=10)
    el_input.clear()
    el_input.send_keys(user_no_groups.username, Keys.ENTER)

    driver.wait_for_xpath('//input[@type="checkbox"]').click()
    driver.wait_for_xpath('//input[@value="Add user"]').click()
    driver.wait_for_xpath(f'//a[contains(.,"{user_no_groups.username}")]')
    assert (
        len(
            driver.find_elements_by_xpath(
                f'//div[@id="{user_no_groups.id}-admin-chip"]'
            )
        )
        == 1
    )


@pytest.mark.flaky(reruns=2)
def test_add_new_group_user_nonadmin(
    driver, super_admin_user, user_no_groups, public_group
):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h5[text()="All Groups"]')
    el = driver.wait_for_xpath(f'//a[contains(.,"{public_group.name}")]')
    driver.execute_script("arguments[0].click();", el)
    el_input = driver.wait_for_xpath('//input[@id="newUserEmail"]', timeout=10)
    el_input.clear()
    el_input.send_keys(user_no_groups.username, Keys.ENTER)
    driver.wait_for_xpath('//input[@value="Add user"]').click()
    driver.wait_for_xpath(f'//a[contains(.,"{user_no_groups.username}")]')
    assert (
        len(
            driver.find_elements_by_xpath(
                f'//div[@id="{user_no_groups.id}-admin-chip"]'
            )
        )
        == 0
    )


@pytest.mark.flaky(reruns=2)
def test_add_new_group_user_new_username(driver, super_admin_user, user, public_group):
    new_username = str(uuid.uuid4())
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h5[text()="All Groups"]')
    el = driver.wait_for_xpath(f'//a[contains(.,"{public_group.name}")]')
    driver.execute_script("arguments[0].click();", el)
    driver.wait_for_xpath('//input[@id="newUserEmail"]', timeout=10).send_keys(
        new_username, Keys.ENTER
    )
    driver.click_xpath('//input[@value="Add user"]')
    driver.wait_for_xpath(f'//a[contains(.,"{new_username}")]')


@pytest.mark.flaky(reruns=2)
def test_delete_group_user(driver, super_admin_user, user, public_group):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h5[text()="All Groups"]')
    el = driver.wait_for_xpath(f'//a[contains(.,"{public_group.name}")]')
    driver.execute_script("arguments[0].click();", el)
    delete_button = driver.wait_for_xpath(f'//a[contains(.,"{user.username}")]')
    delete_button = delete_button.find_elements_by_xpath("../*/button")
    delete_button[0].click()
    driver.wait_for_xpath_to_disappear(f'//a[contains(.,"{user.username}")]')


@pytest.mark.flaky(reruns=2)
@pytest.mark.xfail(strict=False)
def test_delete_group(driver, super_admin_user, user, public_group):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h5[text()="All Groups"]')
    el = driver.wait_for_xpath(f'//a[contains(.,"{public_group.name}")]')
    driver.execute_script("arguments[0].click();", el)
    driver.scroll_to_element_and_click(
        driver.wait_for_xpath(f'//button[contains(.,"Delete Group")]')
    )
    driver.wait_for_xpath(f'//button[contains(.,"Confirm")]').click()
    driver.wait_for_xpath_to_disappear(f'//a[contains(.,"{public_group.name}")]')


@pytest.mark.flaky(reruns=2)
@pytest.mark.xfail(strict=False)
def test_add_stream_filter_group(
    driver, super_admin_user, user, public_group, public_stream
):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h5[text()="All Groups"]')
    el = driver.wait_for_xpath(f'//a[contains(.,"{public_group.name}")]')
    driver.execute_script("arguments[0].click();", el)
    # add stream
    driver.wait_for_xpath(f'//button[contains(.,"Add stream")]').click()
    driver.wait_for_xpath('//input[@name="stream_id"]/..', timeout=10).click()
    driver.wait_for_xpath(f'//li[contains(.,"{public_stream.id}")]', timeout=10)
    stream = driver.switch_to.active_element
    stream.click()
    add_stream = driver.wait_for_xpath_to_be_clickable(f'//button[@type="submit"]')
    driver.execute_script("arguments[0].click();", add_stream)

    # add filter
    filter_name = str(uuid.uuid4())
    driver.wait_for_xpath_to_be_clickable(
        f'//button[contains(.,"Add filter")]', timeout=10
    )
    flt = driver.switch_to.active_element
    flt.click()
    driver.wait_for_xpath(f'//button[contains(.,"Add filter")]').click()
    driver.wait_for_xpath('//input[@name="filter_name"]/..', timeout=10).click()
    driver.wait_for_xpath('//input[@name="filter_name"]').send_keys(filter_name)
    driver.wait_for_xpath('//input[@name="filter_stream_id"]/..', timeout=10).click()
    driver.wait_for_xpath(f'//li[contains(.,"{public_stream.id}")]', timeout=10)
    stream = driver.switch_to.active_element
    stream.click()
    add_filter = driver.wait_for_xpath(f'//button[@type="submit"]', timeout=10)
    driver.execute_script("arguments[0].click();", add_filter)
    driver.wait_for_xpath(f'//span[contains(.,"{filter_name}")]', timeout=10)
    assert (
        len(driver.find_elements_by_xpath(f'//span[contains(.,"{filter_name}")]')) == 1
    )
