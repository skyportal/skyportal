# Comment to avert black & flake8 disagreement


def filter_for_value(driver, value, last=False):
    if last:
        xpath = '(//*[@data-testid="Search-iconButton"])[last()]'
    else:
        xpath = '//*[@data-testid="Search-iconButton"]'
    driver.click_xpath(xpath)
    search_input_xpath = "//input[@aria-label='Search']"
    search_input = driver.wait_for_xpath(search_input_xpath)
    driver.click_xpath(search_input_xpath)
    search_input.send_keys(value)


def test_group_admission_request_and_acceptance(
    driver, user, super_admin_user, public_group, public_group2
):
    driver.get(f"/become_user/{user.id}")
    driver.get("/groups")
    driver.wait_for_xpath('//h6[text()="My Groups"]')
    filter_for_value(driver, public_group2.name)
    driver.click_xpath(f'//*[@data-testid="requestAdmissionButton{public_group2.id}"]')
    driver.wait_for_xpath(
        f'//*[@data-testid="deleteAdmissionRequestButton{public_group2.id}"]'
    )
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get(f"/group/{public_group2.id}")
    filter_for_value(driver, user.username, last=True)
    driver.wait_for_xpath('//div[text()="pending"]')
    driver.click_xpath(f'//*[@data-testid="acceptRequestButton{user.id}"]')
    driver.wait_for_xpath('//div[text()="accepted"]')
    driver.wait_for_xpath(f'//a[text()="{user.username}"]')


def test_group_admission_request_insufficient_stream_access(
    driver,
    user_no_groups_no_streams,
    public_group,
):
    driver.get(f"/become_user/{user_no_groups_no_streams.id}")
    driver.get("/groups")
    driver.wait_for_xpath('//h6[text()="My Groups"]')
    filter_for_value(driver, public_group.name)
    driver.click_xpath(f'//*[@data-testid="requestAdmissionButton{public_group.id}"]')
    driver.wait_for_xpath(
        f'//*[text()="User {user_no_groups_no_streams.id} does not have sufficient stream access to be added to group {public_group.id}."]'
    )
