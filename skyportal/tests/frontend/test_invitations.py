import uuid


def test_bulk_invite_users(driver, super_admin_user, public_group, public_stream):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/user_management')

    user1_email = str(uuid.uuid4().hex)[:8] + "@skyportal.com"
    user2_email = str(uuid.uuid4().hex)[:8] + "@skyportal.com"

    csv = f"""{user1_email},{public_stream.id},{public_group.id},false
{user2_email},{public_stream.id},{public_group.id},false
    """

    textarea = driver.wait_for_xpath("//textarea[@name='bulkInviteCSVInput']")
    driver.scroll_to_element_and_click(textarea)
    textarea.send_keys(csv)

    driver.click_xpath("//*[@data-testid='bulkAddUsersButton']")

    # Check that the users show up in pending invitations
    driver.wait_for_xpath(
        f"//*[@data-testid='pendingInvitations']//*[text()='{user1_email}']"
    )
    driver.wait_for_xpath(
        f"//*[@data-testid='pendingInvitations']//*[text()='{user2_email}']"
    )


def test_invite_single_user(driver, super_admin_user, public_group, public_stream):
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/group/{public_group.id}")

    user_email = str(uuid.uuid4().hex)[:8] + "@skyportal.com"

    textarea = driver.wait_for_xpath("//*[@data-testid='newUserEmail']//input")
    driver.scroll_to_element_and_click(textarea)
    textarea.send_keys(user_email)

    driver.click_xpath("//*[@data-testid='inviteNewUserButton']")
    driver.click_xpath("//*[@data-testid='confirmNewUserButton']")

    driver.wait_for_xpath(f"//*[text()='Invitation successfully sent to {user_email}']")


def test_delete_invitation(driver, super_admin_user, public_group, public_stream):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/user_management')

    user_email = str(uuid.uuid4().hex)[:8] + "@skyportal.com"

    csv = f"{user_email},{public_stream.id},{public_group.id},false"

    textarea = driver.wait_for_xpath("//textarea[@name='bulkInviteCSVInput']")
    driver.scroll_to_element_and_click(textarea)
    textarea.send_keys(csv)

    driver.click_xpath("//*[@data-testid='bulkAddUsersButton']")

    # Check that the users show up in pending invitations
    driver.wait_for_xpath(
        f"//*[@data-testid='pendingInvitations']//*[text()='{user_email}']"
    )

    # Try deleting
    driver.click_xpath(f"//*[@data-testid='deleteInvitation_{user_email}']")
    driver.wait_for_xpath_to_disappear(
        f"//*[@data-testid='pendingInvitations']//*[text()='{user_email}']"
    )


def test_add_invitation_stream(
    driver, super_admin_user, public_group, public_stream, public_stream2
):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/user_management')

    user_email = str(uuid.uuid4().hex)[:8] + "@skyportal.com"

    csv = f"{user_email},{public_stream.id},{public_group.id},false"

    textarea = driver.wait_for_xpath("//textarea[@name='bulkInviteCSVInput']")
    driver.scroll_to_element_and_click(textarea)
    textarea.send_keys(csv)

    driver.click_xpath("//*[@data-testid='bulkAddUsersButton']")

    # Check that the users show up in pending invitations
    driver.wait_for_xpath(
        f"//*[@data-testid='pendingInvitations']//*[text()='{user_email}']"
    )

    # Try adding a stream
    driver.click_xpath(f"//*[@data-testid='addInvitationStreamsButton{user_email}']")
    driver.click_xpath("//*[@data-testid='addInvitationStreamsSelect']")
    driver.click_xpath(f"//*[text()='{public_stream2.name}']")
    driver.click_xpath("//*[@data-testid='submitAddInvitationStreamsButton']")
    driver.wait_for_xpath(
        f"//*[@data-testid='pendingInvitations']//*[text()='{public_stream2.name}']"
    )


def test_edit_invitation_role(
    driver, super_admin_user, public_group, public_stream, public_stream2
):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/user_management')

    user_email = str(uuid.uuid4().hex)[:8] + "@skyportal.com"

    csv = f"{user_email},{public_stream.id},{public_group.id},false"

    textarea = driver.wait_for_xpath("//textarea[@name='bulkInviteCSVInput']")
    driver.scroll_to_element_and_click(textarea)
    textarea.send_keys(csv)

    driver.click_xpath("//*[@data-testid='bulkAddUsersButton']")

    # Check that the users show up in pending invitations
    driver.wait_for_xpath(
        f"//*[@data-testid='pendingInvitations']//*[text()='{user_email}']"
    )
    driver.wait_for_xpath(
        "//*[@data-testid='pendingInvitations']//*[text()='Full user']"
    )

    # Edit role
    driver.click_xpath(f"//*[@data-testid='editInvitationRoleButton{user_email}']")
    driver.click_xpath("//*[@data-testid='invitationRoleSelect']")
    driver.click_xpath("//*[text()='View only']")
    driver.click_xpath("//*[@data-testid='submitEditRoleButton']")
    driver.wait_for_xpath(
        "//*[@data-testid='pendingInvitations']//*[text()='View only']"
    )
