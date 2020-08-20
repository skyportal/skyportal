from selenium.common.exceptions import TimeoutException


def test_share_data(
    driver,
    super_admin_user,
    super_admin_token,
    public_source,
    public_group,
    public_group2,
):
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/source/{public_source.id}")
    driver.click_xpath('//*[text()="Share data"]')
    driver.wait_for_xpath(f"//div[text()='{public_group.name}']", 15)
    driver.click_xpath('//*[@id="MUIDataTableSelectCell-0"]')
    driver.click_xpath('//*[@id="dataSharingFormGroupsSelect"]')
    driver.click_xpath(f'//li[text()="{public_group2.name}"]')
    driver.click_xpath('//*[text()="Submit"]')
    driver.wait_for_xpath('//*[text()="Data successfully shared"]', 15)
    groups_str = ", ".join([public_group.name, public_group2.name])
    try:
        driver.wait_for_xpath(f"//div[text()='{groups_str}']")
    except TimeoutException:
        groups_str = ", ".join([public_group2.name, public_group.name])
        driver.wait_for_xpath(f"//div[text()='{groups_str}']")
