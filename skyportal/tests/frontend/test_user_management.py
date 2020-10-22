import pytest


def test_delete_group_user(driver, super_admin_user, user, public_group):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/user_management')
    driver.wait_for_xpath(
        f"//div[@id='deleteGroupUserButton_{user.id}_{public_group.id}']"
    )
    driver.click_xpath(
        f"//div[@id='deleteGroupUserButton_{user.id}_{public_group.id}']//*[contains(@class, 'MuiChip-deleteIcon')]"
    )
    driver.wait_for_xpath(
        f"//div[text()='User successfully removed from specified group.']"
    )


@pytest.mark.flaky(reruns=2)
def test_delete_stream_user(driver, super_admin_user, user, stream_with_users):
    stream = stream_with_users
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/user_management')
    driver.wait_for_xpath(f"//div[@id='deleteStreamUserButton_{user.id}_{stream.id}']")
    driver.click_xpath(
        f"//div[@id='deleteStreamUserButton_{user.id}_{stream.id}']//*[contains(@class, 'MuiChip-deleteIcon')]"
    )
    driver.wait_for_xpath(f"//div[text()='Stream access successfully revoked.']")


def test_add_user_to_group(driver, user, super_admin_user, public_group, public_group2):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/user_management')
    driver.wait_for_xpath(
        f"//div[@id='deleteGroupUserButton_{user.id}_{public_group.id}']"
    )
    driver.click_xpath(f'//*[@data-testid="addUserGroupsButton{user.id}"]')
    driver.click_xpath('//*[@id="addUserToGroupsSelect"]')
    driver.click_xpath(f'//li[text()="{public_group2.name}"]')
    driver.click_xpath('//*[text()="Submit"]')
    driver.wait_for_xpath(
        '//*[text()="User successfully added to specified group(s)."]'
    )
    driver.wait_for_xpath(
        f"//div[@id='deleteGroupUserButton_{user.id}_{public_group2.id}']"
    )
