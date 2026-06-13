from playwright.sync_api import expect


def test_db_stats_page_render(
    page, super_admin_user, public_group, public_source, public_candidate
):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/db_stats")
    expect(page.locator('//*[text()="Number of candidates"]').first).to_be_visible()
