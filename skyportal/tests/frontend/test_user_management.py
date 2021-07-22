import pytest


def filter_for_user(driver, username):
    # Helper function to filter for a specific user on the page
    driver.click_xpath("//button[@data-testid='Filter Table-iconButton']")
    username_input_xpath = "//input[@id='root_username']"
    username_input = driver.wait_for_xpath(username_input_xpath)
    driver.click_xpath(username_input_xpath)
    username_input.send_keys(username)
    driver.click_xpath(
        "//div[contains(@class, 'MUIDataTableFilter-root')]//span[text()='Submit']"
    )


def test_delete_user_role(driver, super_admin_user, user):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/user_management')
    filter_for_user(driver, user.username)
    driver.click_xpath(
        f"//*[@data-testid='deleteUserRoleButton_{user.id}_Full user']//*[contains(@class, 'MuiChip-deleteIcon')]"
    )
    driver.wait_for_xpath("//div[text()='User role successfully removed.']")
    driver.wait_for_xpath_to_disappear(
        f"//*[@data-testid='deleteUserRoleButton_{user.id}_Full user']//*[contains(@class, 'MuiChip-deleteIcon')]"
    )


def test_grant_and_delete_user_acl(driver, super_admin_user, user):
    acl = "Post taxonomy"
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/user_management')
    filter_for_user(driver, user.username)
    driver.click_xpath(f'//*[@data-testid="addUserACLsButton{user.id}"]')
    driver.click_xpath('//*[@data-testid="addUserACLsSelect"]')
    driver.click_xpath(f'//li[text()="{acl}"]')
    driver.click_xpath('//*[text()="Submit"]')
    driver.wait_for_xpath('//*[text()="User successfully granted specified ACL(s)."]')
    driver.click_xpath(
        f"//*[@data-testid='deleteUserACLButton_{user.id}_{acl}']//*[contains(@class, 'MuiChip-deleteIcon')]"
    )
    driver.wait_for_xpath("//div[text()='User ACL successfully removed.']")
    driver.wait_for_xpath_to_disappear(
        f"//*[@data-testid='deleteUserACLButton_{user.id}_{acl}']//*[contains(@class, 'MuiChip-deleteIcon')]"
    )


def test_add_user_role(driver, super_admin_user, user):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/user_management')
    filter_for_user(driver, user.username)
    driver.click_xpath(f'//*[@data-testid="addUserRolesButton{user.id}"]')
    driver.click_xpath('//*[@data-testid="addUserRolesSelect"]')
    driver.click_xpath('//li[text()="Group admin"]')
    driver.click_xpath('//*[text()="Submit"]')
    driver.wait_for_xpath('//*[text()="User successfully granted specified role(s)."]')
    driver.wait_for_xpath(
        f"//*[@data-testid='deleteUserRoleButton_{user.id}_Group admin']//*[contains(@class, 'MuiChip-deleteIcon')]"
    )


def test_delete_group_user(driver, super_admin_user, user, public_group):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/user_management')
    filter_for_user(driver, user.username)
    driver.wait_for_xpath(
        f"//*[@data-testid='deleteGroupUserButton_{user.id}_{public_group.id}']"
    )
    driver.click_xpath(
        f"//*[@data-testid='deleteGroupUserButton_{user.id}_{public_group.id}']//*[contains(@class, 'MuiChip-deleteIcon')]"
    )
    driver.wait_for_xpath(
        "//div[text()='User successfully removed from specified group.']"
    )


@pytest.mark.flaky(reruns=2)
def test_delete_stream_user(driver, super_admin_user, user, stream_with_users):
    stream = stream_with_users
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/user_management')
    filter_for_user(driver, user.username)
    driver.wait_for_xpath(
        f"//*[@data-testid='deleteStreamUserButton_{user.id}_{stream.id}']"
    )
    driver.click_xpath(
        f"//*[@data-testid='deleteStreamUserButton_{user.id}_{stream.id}']//*[contains(@class, 'MuiChip-deleteIcon')]"
    )
    driver.wait_for_xpath("//div[text()='Stream access successfully revoked.']")


def test_add_user_to_group(driver, user, super_admin_user, public_group, public_group2):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/user_management')
    filter_for_user(driver, user.username)
    driver.wait_for_xpath(
        f"//*[@data-testid='deleteGroupUserButton_{user.id}_{public_group.id}']"
    )
    driver.click_xpath(f'//*[@data-testid="addUserGroupsButton{user.id}"]')
    driver.click_xpath('//*[@data-testid="addUserToGroupsSelect"]')
    driver.click_xpath(f'//li[text()="{public_group2.name}"]', scroll_parent=True)
    driver.click_xpath('//button[@data-testid="submitAddFromGroupsButton"]')
    driver.wait_for_xpath(
        '//*[text()="User successfully added to specified group(s)."]'
    )
    driver.wait_for_xpath(
        f"//*[@data-testid='deleteGroupUserButton_{user.id}_{public_group2.id}']"
    )


def test_add_user_to_stream(
    driver, user, super_admin_user, public_group, public_stream, public_stream2
):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/user_management')
    filter_for_user(driver, user.username)
    driver.wait_for_xpath(
        f"//*[@data-testid='deleteGroupUserButton_{user.id}_{public_group.id}']"
    )
    driver.click_xpath(f'//*[@data-testid="addUserStreamsButton{user.id}"]')
    driver.click_xpath('//*[@data-testid="addUserToStreamsSelect"]')
    driver.click_xpath(f'//li[text()="{public_stream2.name}"]', scroll_parent=True)
    driver.click_xpath('//*[text()="Submit"]')
    driver.wait_for_xpath(
        '//*[text()="User successfully added to specified stream(s)."]'
    )
    driver.wait_for_xpath(
        f"//*[@data-testid='deleteStreamUserButton_{user.id}_{public_stream2.id}']"
    )


def test_user_expiration(
    driver,
    user,
    super_admin_user,
):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/user_management')
    filter_for_user(driver, user.username)

    # Set expiration date to today
    driver.click_xpath(f"//*[@data-testid='editUserExpirationDate{user.id}']")
    driver.click_xpath("//*[@data-testid='expirationDatePicker']")
    driver.click_xpath("//span[text()='OK']")
    driver.click_xpath("//button[@data-testid='submitExpirationDateButton']")

    driver.wait_for_xpath("//*[text()='User expiration date successfully updated.']")

    # Check that user deactivated
    driver.get(f'/become_user/{user.id}')
    driver.get("/")
    driver.wait_for_xpath("//*[contains(text(), 'User account expired')]")
