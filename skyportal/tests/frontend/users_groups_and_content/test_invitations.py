import uuid

from playwright.sync_api import expect


def test_bulk_invite_users(page, super_admin_user, public_group, public_stream):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/user_management")

    user1_email = str(uuid.uuid4().hex)[:8] + "@skyportal.com"
    user2_email = str(uuid.uuid4().hex)[:8] + "@skyportal.com"

    csv = f"""{user1_email},{public_stream.id},{public_group.id},false
{user2_email},{public_stream.id},{public_group.id},false
    """

    page.locator("//textarea[@name='bulkInviteCSVInput']").first.fill(csv)
    page.locator("//*[@data-testid='bulkAddUsersButton']").first.click()

    # Check that the users show up in pending invitations
    expect(
        page.locator(
            f"//*[@data-testid='pendingInvitations']//*[text()='{user1_email}']"
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            f"//*[@data-testid='pendingInvitations']//*[text()='{user2_email}']"
        ).first
    ).to_be_visible()


def test_invite_single_user(page, super_admin_user, public_group, public_stream):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/group/{public_group.id}")

    user_email = str(uuid.uuid4().hex)[:8] + "@skyportal.com"

    page.locator("//*[@data-testid='newUserEmail']//input").first.fill(user_email)
    page.locator("//*[@data-testid='inviteNewUserButton']").first.click()
    page.locator("//*[@data-testid='confirmNewUserButton']").first.click()

    expect(
        page.locator(
            f"//*[text()='Invitation successfully sent to {user_email}']"
        ).first
    ).to_be_visible()


def test_delete_invitation(page, super_admin_user, public_group, public_stream):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/user_management")

    user_email = str(uuid.uuid4().hex)[:8] + "@skyportal.com"
    csv = f"{user_email},{public_stream.id},{public_group.id},false"

    page.locator("//textarea[@name='bulkInviteCSVInput']").first.fill(csv)
    page.locator("//*[@data-testid='bulkAddUsersButton']").first.click()

    expect(
        page.locator(
            f"//*[@data-testid='pendingInvitations']//*[text()='{user_email}']"
        ).first
    ).to_be_visible()

    page.locator(f"//*[@data-testid='deleteInvitation_{user_email}']").first.click()
    page.locator("//*[@data-testid='confirmDeletetionButton']").first.click()

    expect(
        page.locator(
            f"//*[@data-testid='pendingInvitations']//*[text()='{user_email}']"
        ).first
    ).to_be_hidden()


def test_add_invitation_stream(
    page, super_admin_user, public_group, public_stream, public_stream2
):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/user_management")

    user_email = str(uuid.uuid4().hex)[:8] + "@skyportal.com"
    csv = f"{user_email},{public_stream.id},{public_group.id},false"

    page.locator("//textarea[@name='bulkInviteCSVInput']").first.fill(csv)
    page.locator("//*[@data-testid='bulkAddUsersButton']").first.click()

    expect(
        page.locator(
            f"//*[@data-testid='pendingInvitations']//*[text()='{user_email}']"
        ).first
    ).to_be_visible()

    page.locator(
        f"//*[@data-testid='addInvitationStreamsButton{user_email}']"
    ).first.click()
    page.locator("//*[@data-testid='addInvitationStreamsSelect']").first.click()
    page.locator(f"//*[text()='{public_stream2.name}']").first.click()
    page.locator("//*[@data-testid='submitAddInvitationStreamsButton']").first.click()
    expect(
        page.locator(
            f"//*[@data-testid='pendingInvitations']//*[text()='{public_stream2.name}']"
        ).first
    ).to_be_visible()


def test_edit_invitation_role(
    page, super_admin_user, public_group, public_stream, public_stream2
):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/user_management")

    user_email = str(uuid.uuid4().hex)[:8] + "@skyportal.com"
    csv = f"{user_email},{public_stream.id},{public_group.id},false"

    page.locator("//textarea[@name='bulkInviteCSVInput']").first.fill(csv)
    page.locator("//*[@data-testid='bulkAddUsersButton']").first.click()

    expect(
        page.locator(
            f"//*[@data-testid='pendingInvitations']//*[text()='{user_email}']"
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            "//*[@data-testid='pendingInvitations']//*[text()='Full user']"
        ).first
    ).to_be_visible()

    page.locator(
        f"//*[@data-testid='editInvitationRoleButton{user_email}']"
    ).first.click()
    page.locator("//*[@data-testid='invitationRoleSelect']").first.click()
    # scope to the open dropdown option ("View only" also appears elsewhere on
    # the page, and the unscoped .first can land on a non-clickable match)
    page.locator('//li[@role="option"][normalize-space(.)="View only"]').first.click()
    page.locator("//*[@data-testid='submitEditRoleButton']").first.click()
    expect(
        page.locator(
            "//*[@data-testid='pendingInvitations']//*[text()='View only']"
        ).first
    ).to_be_visible()
