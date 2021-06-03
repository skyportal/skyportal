import uuid
import pytest
from baselayer.app.env import load_env
from skyportal.tests import api


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
    driver, super_admin_user, super_admin_token, user_no_groups, public_group
):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h6[text()="All Groups"]')
    driver.click_xpath(
        f'//div[@data-testid="All Groups-{public_group.name}"]', scroll_parent=True
    )
    driver.click_xpath('//div[@data-testid="newGroupUserTextInput"]')
    driver.click_xpath(f'//li[text()="{user_no_groups.username}"]', scroll_parent=True)
    # Default is unchecked; just need to click once to make group admin
    driver.click_xpath('//*[@data-testid="adminCheckbox"]')
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

    status, data = api(
        "GET",
        f"groups/{public_group.id}?includeGroupUsers=true",
        token=super_admin_token,
    )
    group_user = None
    for gu in data["data"]["users"]:
        if gu["id"] == user_no_groups.id:
            group_user = gu
    assert group_user is not None
    assert group_user["admin"]
    assert group_user["can_save"]


@pytest.mark.flaky(reruns=2)
def test_add_new_group_user_nonadmin(
    driver, super_admin_user, super_admin_token, user_no_groups, public_group
):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h6[text()="All Groups"]')
    driver.click_xpath(
        f'//div[@data-testid="All Groups-{public_group.name}"]', scroll_parent=True
    )
    driver.click_xpath('//div[@data-testid="newGroupUserTextInput"]')
    driver.click_xpath(f'//li[text()="{user_no_groups.username}"]', scroll_parent=True)
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

    status, data = api(
        "GET",
        f"groups/{public_group.id}?includeGroupUsers=true",
        token=super_admin_token,
    )
    group_user = None
    for gu in data["data"]["users"]:
        if gu["id"] == user_no_groups.id:
            group_user = gu
    assert group_user is not None
    assert not group_user["admin"]
    assert group_user["can_save"]


@pytest.mark.flaky(reruns=2)
def test_add_new_group_user_cant_save(
    driver, super_admin_user, super_admin_token, user_no_groups, public_group
):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h6[text()="All Groups"]')
    driver.click_xpath(
        f'//div[@data-testid="All Groups-{public_group.name}"]', scroll_parent=True
    )
    driver.click_xpath('//div[@data-testid="newGroupUserTextInput"]')
    driver.click_xpath(f'//li[text()="{user_no_groups.username}"]', scroll_parent=True)
    # Checkbox is checked by default
    driver.click_xpath('//*[@data-testid="canSaveCheckbox"]')
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

    status, data = api(
        "GET",
        f"groups/{public_group.id}?includeGroupUsers=true",
        token=super_admin_token,
    )
    group_user = None
    for gu in data["data"]["users"]:
        if gu["id"] == user_no_groups.id:
            group_user = gu
    assert group_user is not None
    assert not group_user["admin"]
    assert not group_user["can_save"]


@pytest.mark.flaky(reruns=2)
def test_invite_all_users_from_other_group(
    driver, super_admin_user, public_group, public_group2, user, user_group2
):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h6[text()="All Groups"]')
    driver.wait_for_xpath_to_disappear(f'//a[contains(.,"{user_group2.username}")]')
    driver.click_xpath(
        f'//div[@data-testid="All Groups-{public_group.name}"]', scroll_parent=True
    )
    driver.click_xpath('//*[@data-testid="addUsersFromGroupsTextField"]')
    driver.click_xpath(f'//li[text()="{public_group2.name}"]', scroll_parent=True)
    driver.click_xpath('//*[text()="Add users"]')
    driver.wait_for_xpath(
        "//*[text()='Successfully added users from specified group(s)']"
    )
    driver.wait_for_xpath(f'//*[text()="{user_group2.username}"]')


# @pytest.mark.flaky(reruns=2)
def test_delete_group_user(driver, super_admin_user, user, public_group):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h6[text()="All Groups"]')
    driver.click_xpath(
        f'//div[@data-testid="All Groups-{public_group.name}"]', scroll_parent=True
    )

    driver.wait_for_xpath(f'//a[contains(.,"{user.username}")]')
    driver.click_xpath(f'//button[@data-testid="delete-{user.username}"]')
    driver.wait_for_xpath_to_disappear(f'//a[contains(.,"{user.username}")]')


@pytest.mark.flaky(reruns=2)
# @pytest.mark.xfail(strict=False)
def test_delete_group(driver, super_admin_user, user, public_group):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h6[text()="All Groups"]')
    driver.click_xpath(
        f'//div[@data-testid="All Groups-{public_group.name}"]', scroll_parent=True
    )
    driver.scroll_to_element_and_click(
        driver.wait_for_xpath('//button[contains(.,"Delete Group")]')
    )
    driver.wait_for_xpath('//button[contains(.,"Confirm")]').click()
    driver.wait_for_xpath_to_disappear(f'//a[contains(.,"{public_group.name}")]')


@pytest.mark.flaky(reruns=2)
def test_add_stream_add_delete_filter_group(
    driver, super_admin_user, super_admin_token, public_group, public_stream2
):
    status, data = api(
        'POST',
        f'streams/{public_stream2.id}/users',
        data={
            'user_id': super_admin_user.id,
        },
        token=super_admin_token,
    )
    assert status == 200

    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/groups')
    driver.click_xpath('//h6[text()="All Groups"]', scroll_parent=True)
    driver.click_xpath(
        f'//div[@data-testid="All Groups-{public_group.name}"]', scroll_parent=True
    )

    # Add stream
    driver.click_xpath('//button[contains(.,"Add stream")]')
    driver.click_xpath('//input[@name="stream_id"]/..')

    driver.click_xpath(f'//li[contains(.,"{public_stream2.name}")]', scroll_parent=True)
    driver.click_xpath('//button[@data-testid="add-stream-dialog-submit"]')

    # add filter
    filter_name = str(uuid.uuid4())
    driver.click_xpath('//button[contains(.,"Add filter")]')
    driver.click_xpath('//input[@name="filter_name"]/..')
    driver.wait_for_xpath('//input[@name="filter_name"]').send_keys(filter_name)
    driver.click_xpath('//input[@name="filter_stream_id"]/..')
    driver.click_xpath(
        f'//div[@id="menu-filter_stream_id"]//li[contains(.,"{public_stream2.name}")]',
        scroll_parent=True,
    )
    driver.click_xpath('//button[@data-testid="add-filter-dialog-submit"]')
    driver.wait_for_xpath(f'//span[contains(.,"{filter_name}")]')
    assert (
        len(driver.find_elements_by_xpath(f'//span[contains(.,"{filter_name}")]')) == 1
    )

    # delete filter
    driver.click_xpath(f'//a[contains(.,"{filter_name}")]')
    driver.wait_for_xpath_to_disappear(f'//a[contains(.,"{filter_name}")]')


def test_cannot_add_stream_group_users_cant_access(
    driver, super_admin_user, user, public_group, public_stream2
):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/groups')
    driver.click_xpath('//h6[text()="All Groups"]', scroll_parent=True)
    driver.click_xpath(
        f'//div[@data-testid="All Groups-{public_group.name}"]', scroll_parent=True
    )

    # Cannot add stream that group members don't have access to
    driver.click_xpath('//button[contains(.,"Add stream")]')
    driver.click_xpath('//input[@name="stream_id"]/..')

    driver.click_xpath(f'//li[contains(.,"{public_stream2.name}")]', scroll_parent=True)
    driver.click_xpath('//button[@data-testid="add-stream-dialog-submit"]')
    driver.wait_for_xpath('//*[contains(.,"Insufficient permissions")]')
