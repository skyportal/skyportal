import uuid
import pytest
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from baselayer.app.env import load_env


_, cfg = load_env()


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
    driver.click_xpath('//div[@id="groupAdminsSelect"]')
    driver.click_xpath(f'//li[contains(text(),"{user.username}")]', scroll_parent=True)
    driver.click_xpath('//button[contains(.,"Create Group")]', wait_clickable=False)
    driver.wait_for_xpath(f'//a[contains(.,"{test_proj_name}")]')


@pytest.mark.flaky(reruns=2)
def test_add_new_group_explicit_self_admin(driver, super_admin_user, user):
    test_proj_name = str(uuid.uuid4())
    driver.get(f'/become_user/{super_admin_user.id}')  # TODO decorator/context manager?
    driver.get('/')
    driver.refresh()
    driver.get('/groups')
    driver.wait_for_xpath('//input[@name="name"]').send_keys(test_proj_name)
    driver.click_xpath('//div[@id="groupAdminsSelect"]')
    driver.click_xpath(f'//li[contains(text(),"{user.username}")]', scroll_parent=True)
    driver.click_xpath('//button[contains(.,"Create Group")]', wait_clickable=False)
    driver.wait_for_xpath(f'//a[contains(.,"{test_proj_name}")]')


@pytest.mark.flaky(reruns=2)
def test_add_new_group_user_admin(
    driver, super_admin_user, user_no_groups, public_group
):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h6[text()="All Groups"]')
    el = driver.wait_for_xpath(f'//a[contains(.,"{public_group.name}")]')
    driver.execute_script("arguments[0].click();", el)
    el_input = driver.wait_for_xpath('//input[@id="newUserEmail"]', timeout=10)
    el_input.clear()
    ActionChains(driver).move_to_element(el_input).click().send_keys(
        user_no_groups.username
    ).pause(5).send_keys(Keys.ENTER).perform()
    driver.click_xpath('//input[@type="checkbox"]')
    driver.click_xpath('//button[contains(.,"Add user")]')
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
    driver.wait_for_xpath('//h6[text()="All Groups"]')
    el = driver.wait_for_xpath(f'//a[contains(.,"{public_group.name}")]')
    driver.execute_script("arguments[0].click();", el)
    el_input = driver.wait_for_xpath('//input[@id="newUserEmail"]', timeout=10)
    el_input.clear()
    ActionChains(driver).move_to_element(el_input).click().send_keys(
        user_no_groups.username
    ).pause(5).send_keys(Keys.ENTER).perform()
    driver.click_xpath('//button[contains(.,"Add user")]')
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
    driver.wait_for_xpath('//h6[text()="All Groups"]')
    el = driver.wait_for_xpath(f'//a[contains(.,"{public_group.name}")]')
    driver.execute_script("arguments[0].click();", el)
    el_input = driver.wait_for_xpath('//input[@id="newUserEmail"]', timeout=10)
    el_input.clear()
    ActionChains(driver).move_to_element(el_input).click().send_keys(
        new_username
    ).pause(5).send_keys(Keys.ENTER).perform()
    driver.click_xpath('//button[contains(.,"Add user")]')
    if cfg["invitations.enabled"]:  # If invites are disabled, we won't see these
        driver.click_xpath('//span[text()="Confirm"]')
        driver.wait_for_xpath('//*[contains(., "Invitation successfully sent to")]')
    else:
        # If invitations are disabled, the user will be added and will appear
        driver.wait_for_xpath(f'//a[contains(.,"{new_username}")]')


@pytest.mark.flaky(reruns=2)
def test_invite_all_users_from_other_group(
    driver, super_admin_user, public_group, public_group2, user, user_group2
):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h6[text()="All Groups"]')
    el = driver.wait_for_xpath(f'//a[contains(.,"{public_group.name}")]')
    driver.wait_for_xpath_to_disappear(f'//a[contains(.,"{user_group2.username}")]')
    driver.execute_script("arguments[0].click();", el)
    driver.click_xpath('//*[@id="addUsersFromGroupsSelect"]')
    driver.click_xpath(f'//li[text()="{public_group2.name}"]', scroll_parent=True)
    driver.click_xpath('//*[text()="Add users"]')
    driver.wait_for_xpath(
        "//*[text()='Successfully added users from specified group(s)']"
    )
    driver.wait_for_xpath(f'//*[text()="{user_group2.username}"]')


@pytest.mark.flaky(reruns=2)
def test_delete_group_user(driver, super_admin_user, user, public_group):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h6[text()="All Groups"]')
    el = driver.wait_for_xpath(f'//a[contains(.,"{public_group.name}")]')
    driver.execute_script("arguments[0].click();", el)
    username_link = driver.wait_for_xpath(f'//a[contains(.,"{user.username}")]')
    delete_button = username_link.find_elements_by_xpath("../../*//button")
    delete_button[-1].click()
    driver.wait_for_xpath_to_disappear(f'//a[contains(.,"{user.username}")]')


@pytest.mark.flaky(reruns=2)
@pytest.mark.xfail(strict=False)
def test_delete_group(driver, super_admin_user, user, public_group):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h6[text()="All Groups"]')
    el = driver.wait_for_xpath(f'//a[contains(.,"{public_group.name}")]')
    driver.execute_script("arguments[0].click();", el)
    driver.scroll_to_element_and_click(
        driver.wait_for_xpath(f'//button[contains(.,"Delete Group")]')
    )
    driver.wait_for_xpath(f'//button[contains(.,"Confirm")]').click()
    driver.wait_for_xpath_to_disappear(f'//a[contains(.,"{public_group.name}")]')


@pytest.mark.flaky(reruns=2)
@pytest.mark.xfail(strict=False)
def test_add_stream_add_delete_filter_group(
    driver, super_admin_user, user, public_group, public_stream
):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h6[text()="All Groups"]')
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

    # delete filter
    delete_button = driver.wait_for_xpath(f'//a[contains(.,"{filter_name}")]')
    delete_button = delete_button.find_elements_by_xpath("../*/button")
    delete_button[0].click()
    driver.wait_for_xpath_to_disappear(f'//a[contains(.,"{filter_name}")]')
