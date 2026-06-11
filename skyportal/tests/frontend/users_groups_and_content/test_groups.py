import uuid

import pytest
from playwright.sync_api import expect

from baselayer.app.env import load_env
from skyportal.tests import api

_, cfg = load_env()


def test_public_groups_list(page, user, public_group):
    page.goto(f"/become_user/{user.id}")
    page.goto("/groups")
    expect(page.locator('//h6[text()="My Groups"]').first).to_be_visible()
    expect(
        page.locator(f'//a[contains(.,"{public_group.name}")]').first
    ).to_be_visible()


def test_super_admin_groups_list(page, super_admin_user, public_group):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/groups")
    expect(page.locator('//h6[text()="All Groups"]').first).to_be_visible()
    expect(
        page.locator(f'//a[contains(.,"{public_group.name}")]').first
    ).to_be_visible()


def test_add_new_group(page, super_admin_user, user, super_admin_token):
    test_proj_name = str(uuid.uuid4())
    group_description = str(uuid.uuid4())
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/")
    page.reload()
    page.goto("/groups")
    expect(page.locator('//h3[text()="Create New Group"]').first).to_be_visible()
    page.locator('//input[@name="name"]').first.fill(test_proj_name)
    page.locator('//input[@name="description"]').first.fill(group_description)
    page.locator('//div[@id="groupAdminsSelect"]').first.click()
    page.locator(f'//li[contains(text(),"{user.username}")]').first.click()
    # close the (multiple) admins select so its menu overlay stops covering the
    # Create Group button
    page.keyboard.press("Escape")
    page.locator('//button[contains(.,"Create Group")]').first.click()
    expect(page.locator(f'//a[contains(.,"{test_proj_name}")]').first).to_be_visible()
    # check for group description
    status, data = api("GET", "groups", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    user_groups = data["data"]["user_groups"]
    for group in user_groups:
        if group["description"] == group_description:
            id = group["id"]
            break
    page.goto(f"/group/{id}")
    expect(page.locator('//h6[@data-testid="description"]').first).to_be_visible()
    expect(
        page.locator(f'//*[text()[contains(., "{group_description}")]]').first
    ).to_be_visible()


@pytest.mark.parametrize(
    "checkbox, admin_chip_count, admin, can_save",
    [
        ("adminCheckbox", 1, True, True),
        (None, 0, False, True),
        ("canSaveCheckbox", 0, False, False),
    ],
)
def test_add_new_group_user(
    page,
    super_admin_user,
    super_admin_token,
    user_no_groups,
    public_group,
    checkbox,
    admin_chip_count,
    admin,
    can_save,
):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/groups")
    expect(page.locator('//h6[text()="All Groups"]').first).to_be_visible()
    page.locator(f'//*[@data-testid="All Groups-{public_group.name}"]').first.click()
    page.locator('//div[@data-testid="newGroupUserTextInput"]').first.click()
    page.locator(f'//li[text()="{user_no_groups.username}"]').first.click()
    if checkbox is not None:
        page.locator(f'//*[@data-testid="{checkbox}"]').first.click()
    page.locator('//button[contains(.,"Add user")]').first.click()
    expect(
        page.locator(f'//a[contains(.,"{user_no_groups.username}")]').first
    ).to_be_visible()
    expect(page.locator(f'//div[@id="{user_no_groups.id}-admin-chip"]')).to_have_count(
        admin_chip_count
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
    assert group_user["admin"] == admin
    assert group_user["can_save"] == can_save


def test_invite_all_users_from_other_group(
    page, super_admin_user, public_group, public_group2, user, user_group2
):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/groups")
    expect(page.locator('//h6[text()="All Groups"]').first).to_be_visible()
    expect(
        page.locator(f'//a[contains(.,"{user_group2.username}")]').first
    ).to_be_hidden()
    page.locator(f'//*[@data-testid="All Groups-{public_group.name}"]').first.click()
    page.locator('//*[@data-testid="addUsersFromGroupsTextField"]').first.click()
    page.locator(f'//li[text()="{public_group2.name}"]').first.click()
    page.locator('//*[text()="Add users"]').first.click()
    expect(
        page.locator(
            "//*[text()='Successfully added users from specified group(s)']"
        ).first
    ).to_be_visible()
    expect(page.locator(f'//*[text()="{user_group2.username}"]').first).to_be_visible()


def test_delete_group_user(page, super_admin_user, user, public_group):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/groups")
    expect(page.locator('//h6[text()="All Groups"]').first).to_be_visible()
    page.locator(f'//*[@data-testid="All Groups-{public_group.name}"]').first.click()

    expect(page.locator(f'//a[contains(.,"{user.username}")]').first).to_be_visible()
    page.locator(f'//button[@data-testid="delete-{user.username}"]').first.click()
    page.locator(
        f'//button[@data-testid="confirm-delete-{user.username}"]'
    ).first.click()
    expect(page.locator(f'//a[contains(.,"{user.username}")]').first).to_be_hidden()


def test_delete_group(page, super_admin_user, user, public_group):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/groups")
    expect(page.locator('//h6[text()="All Groups"]').first).to_be_visible()
    page.locator(f'//*[@data-testid="All Groups-{public_group.name}"]').first.click()
    page.locator('//button[contains(.,"Delete Group")]').first.click()
    page.locator('//button[contains(.,"Confirm")]').first.click()
    expect(page.locator(f'//a[contains(.,"{public_group.name}")]').first).to_be_hidden()


def test_add_stream_add_delete_filter_group(
    page, super_admin_user, super_admin_token, public_group, public_stream2
):
    status, data = api(
        "POST",
        f"streams/{public_stream2.id}/users",
        data={"user_id": super_admin_user.id},
        token=super_admin_token,
    )
    assert status == 200

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/groups")
    page.locator('//h6[text()="All Groups"]').first.click()
    page.locator(f'//*[@data-testid="All Groups-{public_group.name}"]').first.click()

    # Add stream
    page.locator('//button[contains(.,"Add stream")]').first.click()
    page.locator(
        '//div[@aria-labelledby="alert-stream-select-required-label"]'
    ).first.click()
    page.locator(f'//li[contains(.,"{public_stream2.name}")]').first.click()
    page.locator('//button[@data-testid="add-stream-dialog-submit"]').first.click()

    # add filter
    filter_name = str(uuid.uuid4())
    page.locator('//button[contains(.,"Add filter")]').first.click()
    page.locator('//input[@name="filter_name"]/..').first.click()
    page.locator('//input[@name="filter_name"]').first.fill(filter_name)

    page.locator(
        '//*[@aria-labelledby="alert-stream-select-required-label"]'
    ).first.click()
    page.locator(f'//li[@data-value="{public_stream2.id}"]').first.click()
    page.locator('//button[@data-testid="add-filter-dialog-submit"]').first.click()
    expect(page.locator(f'//span[contains(.,"{filter_name}")]')).to_have_count(1)

    # delete filter
    page.locator(f'//a[contains(.,"{filter_name}")]').first.click()
    expect(page.locator(f'//a[contains(.,"{filter_name}")]').first).to_be_hidden()


def test_cannot_add_stream_group_users_cant_access(
    page, super_admin_user, user, public_group, public_stream2
):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/groups")
    page.locator('//h6[text()="All Groups"]').first.click()
    page.locator(f'//*[@data-testid="All Groups-{public_group.name}"]').first.click()

    # Cannot add stream that group members don't have access to
    page.locator('//button[contains(.,"Add stream")]').first.click()
    page.locator(
        '//*[@aria-labelledby="alert-stream-select-required-label"]'
    ).first.click()
    page.locator(f'//li[contains(.,"{public_stream2.name}")]').first.click()
    page.locator('//button[@data-testid="add-stream-dialog-submit"]').first.click()
    expect(
        page.locator('//*[contains(.,"Not all users have stream access with")]').first
    ).to_be_visible()
