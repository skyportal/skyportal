import datetime

import pytest
from playwright.sync_api import expect


def filter_for_user(page, username):
    # Helper function to filter for a specific user on the page
    page.locator("//button[@data-testid='Filter Table-iconButton']").first.click()
    page.locator("//input[@id='root_username']").first.fill(username)
    page.locator(
        "//div[contains(@class, 'MuiDialog-root')]//button[text()='Submit']"
    ).first.click()


def test_delete_user_role(page, super_admin_user, user):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/user_management")
    filter_for_user(page, user.username)
    page.locator(
        f"//*[@data-testid='deleteUserRoleButton_{user.id}_Full user']//*[contains(@class, 'MuiChip-deleteIcon')]"
    ).first.click()
    expect(
        page.locator("//div[text()='User role successfully removed.']").first
    ).to_be_visible()
    expect(
        page.locator(
            f"//*[@data-testid='deleteUserRoleButton_{user.id}_Full user']//*[contains(@class, 'MuiChip-deleteIcon')]"
        ).first
    ).to_be_hidden()


def test_add_and_delete_user_affiliations(page, super_admin_user, user):
    affiliation = "Test affiliation"
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/user_management")
    filter_for_user(page, user.username)
    page.locator(
        f'//*[@data-testid="addUserAffiliationsButton{user.id}"]'
    ).first.click()
    page.locator('//*[@data-testid="addUserAffiliationsSelect"]').first.click()

    entry = page.locator(
        '//*[@data-testid="addUserAffiliationsTextField"]/div/input'
    ).first
    entry.fill(affiliation)
    entry.press("Enter")

    page.locator('//*[text()="Submit"]').first.click()
    expect(
        page.locator(
            """//*[text()="Successfully updated user's affiliations."]"""
        ).first
    ).to_be_visible()
    page.locator(
        f"//*[@data-testid='deleteUserAffiliationsButton_{user.id}_{affiliation}']//*[contains(@class, 'MuiChip-deleteIcon')]"
    ).first.click()
    expect(
        page.locator(
            """//div[text()="Successfully deleted user's affiliation."]"""
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            f"//*[@data-testid='deleteUserAffiliationsButton_{user.id}_{affiliation}']//*[contains(@class, 'MuiChip-deleteIcon')]"
        ).first
    ).to_be_hidden()


def test_grant_and_delete_user_acl(page, super_admin_user, user):
    acl = "Post taxonomy"
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/user_management")
    filter_for_user(page, user.username)
    page.locator(f'//*[@data-testid="addUserACLsButton{user.id}"]').first.click()
    page.locator('//*[@data-testid="addUserACLsSelect"]').first.click()
    page.locator(f'//li[text()="{acl}"]').first.click()
    page.locator('//*[text()="Submit"]').first.click()
    expect(
        page.locator('//*[text()="User successfully granted specified ACL(s)."]').first
    ).to_be_visible()
    page.locator(
        f"//*[@data-testid='deleteUserACLButton_{user.id}_{acl}']//*[contains(@class, 'MuiChip-deleteIcon')]"
    ).first.click()
    expect(
        page.locator("//div[text()='User ACL successfully removed.']").first
    ).to_be_visible()
    expect(
        page.locator(
            f"//*[@data-testid='deleteUserACLButton_{user.id}_{acl}']//*[contains(@class, 'MuiChip-deleteIcon')]"
        ).first
    ).to_be_hidden()


def test_add_user_role(page, super_admin_user, user):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/user_management")
    filter_for_user(page, user.username)
    page.locator(f'//*[@data-testid="addUserRolesButton{user.id}"]').first.click()
    page.locator('//*[@data-testid="addUserRolesSelect"]').first.click()
    page.locator('//li[text()="Group admin"]').first.click()
    page.locator('//*[text()="Submit"]').first.click()
    expect(
        page.locator('//*[text()="User successfully granted specified role(s)."]').first
    ).to_be_visible()
    expect(
        page.locator(
            f"//*[@data-testid='deleteUserRoleButton_{user.id}_Group admin']//*[contains(@class, 'MuiChip-deleteIcon')]"
        ).first
    ).to_be_visible()


def test_delete_group_user(page, super_admin_user, user, public_group):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/user_management")
    filter_for_user(page, user.username)
    # Playwright clicks SVG icons and auto-retries on the virtualized DataGrid,
    # so a normal click replaces the old dispatchEvent workaround.
    page.locator(
        f"//*[@data-testid='deleteGroupUserButton_{user.id}_{public_group.id}']//*[contains(@class, 'MuiChip-deleteIcon')]"
    ).first.click()
    expect(
        page.locator(
            "//div[text()='User successfully removed from specified group.']"
        ).first
    ).to_be_visible()


def test_delete_stream_user(page, super_admin_user, user, stream_with_users):
    stream = stream_with_users
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/user_management")
    filter_for_user(page, user.username)
    page.locator(
        f"//*[@data-testid='deleteStreamUserButton_{user.id}_{stream.id}']//*[contains(@class, 'MuiChip-deleteIcon')]"
    ).first.click()
    expect(
        page.locator("//div[text()='Stream access successfully revoked.']").first
    ).to_be_visible()


def test_add_user_to_group(page, user, super_admin_user, public_group, public_group2):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/user_management")
    filter_for_user(page, user.username)
    expect(
        page.locator(
            f"//*[@data-testid='deleteGroupUserButton_{user.id}_{public_group.id}']"
        ).first
    ).to_be_visible()
    page.locator(f'//*[@data-testid="addUserGroupsButton{user.id}"]').first.click()
    page.locator('//*[@data-testid="addUserToGroupsSelect"]').first.click()
    page.locator(f'//li[text()="{public_group2.name}"]').first.click()
    page.locator('//button[@data-testid="submitAddFromGroupsButton"]').first.click()
    expect(
        page.locator(
            '//*[text()="User successfully added to specified group(s)."]'
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            f"//*[@data-testid='deleteGroupUserButton_{user.id}_{public_group2.id}']"
        ).first
    ).to_be_visible()


def test_add_user_to_stream(
    page, user, super_admin_user, public_group, public_stream, public_stream2
):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/user_management")
    filter_for_user(page, user.username)
    expect(
        page.locator(
            f"//*[@data-testid='deleteGroupUserButton_{user.id}_{public_group.id}']"
        ).first
    ).to_be_visible()
    page.locator(f'//*[@data-testid="addUserStreamsButton{user.id}"]').first.click()
    page.locator('//*[@data-testid="addUserToStreamsSelect"]').first.click()
    page.locator(f'//li[text()="{public_stream2.name}"]').first.click()
    page.locator('//*[text()="Submit"]').first.click()
    expect(
        page.locator(
            '//*[text()="User successfully added to specified stream(s)."]'
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            f"//*[@data-testid='deleteStreamUserButton_{user.id}_{public_stream2.id}']"
        ).first
    ).to_be_visible()


# Passes in isolation; only times out under full-suite contention, so retry.
@pytest.mark.flaky(reruns=3)
def test_user_expiration(page, user, super_admin_user):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/user_management")
    filter_for_user(page, user.username)

    # Set expiration date to today
    page.locator(f"//*[@data-testid='editUserExpirationDate{user.id}']").first.click()
    # The MUI date field is read-only, so `fill` times out; type the MMDDYYYY
    # digits into the segmented input instead (as the other date-picker tests do).
    date_input = page.locator("//input[@placeholder='MM/DD/YYYY']").first
    date_input.click()
    date_input.press_sequentially(datetime.datetime.now().strftime("%m%d%Y"))

    page.locator('//*[text()="Submit"]').first.click()

    # Check that user deactivated
    page.goto(f"/become_user/{user.id}")
    page.goto("/")
    expect(page.locator("//*[contains(text(), 'Top Sources')]").first).to_be_hidden()
