import pytest

# Adding a comment here to make flake8 and black play nicely together (spacing below)


@pytest.mark.flaky(reruns=2)
def test_quick_search(
    driver,
    super_admin_user,
    public_source,
    public_group,
):
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get("/")
    driver.wait_for_xpath('//*[@id="quick-search-bar"]').send_keys(public_source.id)
    driver.click_xpath('//*[@id="quick-search-bar-listbox"]')
    # Should be redirected to source page; check for elements that should render
    driver.wait_for_xpath(f'//div[text()="{public_source.id}"]')
    driver.wait_for_xpath(f'//span[text()="{public_group.name}"]')

    driver.wait_for_xpath('//*[@id="quick-search-bar"]').send_keys("invalid_source_id")
    driver.wait_for_xpath('//*[text()="No matching Sources."]')
