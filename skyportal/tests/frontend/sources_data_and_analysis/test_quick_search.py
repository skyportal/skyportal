from playwright.sync_api import expect


def test_quick_search(
    page,
    super_admin_user,
    public_source,
    public_group,
):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/")

    page.locator("#quick-search-bar").first.fill(public_source.id)
    page.locator("#quick-search-bar-listbox").first.click()
    # Should be redirected to source page; check for elements that should render
    expect(page.locator(f'//h6[text()="{public_source.id}"]').first).to_be_visible()
    expect(page.locator(f'//span[text()="{public_group.name}"]').first).to_be_visible()

    page.locator("#quick-search-bar").first.fill("invalid_source_id")
    expect(page.locator('//*[text()="No matching Sources."]').first).to_be_visible()
