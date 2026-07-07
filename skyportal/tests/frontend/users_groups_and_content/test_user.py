from playwright.sync_api import expect


def test_user_info(page, super_admin_user):
    user = super_admin_user
    page.goto(f"/become_user/{user.id}")
    page.goto(f"/user/{user.id}")
    expect(page.locator(f'//div[contains(.,"{user.username}")]').first).to_be_visible()
    for acl in user.permissions:
        expect(page.locator(f'//ul/li[contains(.,"{acl}")]').first).to_be_visible()
