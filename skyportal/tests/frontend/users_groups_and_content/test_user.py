from playwright.sync_api import expect


def test_user_info(page, super_admin_user):
    user = super_admin_user
    page.goto(f"/become_user/{user.id}")
    page.goto(f"/user/{user.id}")
    expect(page.locator('//*[@id="publicProfileRealname"]').first).to_be_visible()
    expect(page.get_by_text(f"@{user.username}").first).to_be_visible()
    expect(page.get_by_text("Member since").first).to_be_visible()
    for acl in user.permissions:
        expect(page.locator(f'//ul/li[contains(.,"{acl}")]')).to_have_count(0)
