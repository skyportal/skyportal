# Comment to avert black & flake8 disagreement


def test_group_admission_request_and_acceptance(
    driver, user, super_admin_user_two_groups, public_group, public_group2
):
    driver.get(f'/become_user/{user.id}')
    driver.get('/groups')
    driver.wait_for_xpath('//h6[text()="My Groups"]')
    driver.click_xpath(f'//*[@data-testid="requestAdmissionButton{public_group2.id}"]')
    driver.wait_for_xpath(
        f'//*[@data-testid="deleteAdmissionRequestButton{public_group2.id}"]'
    )
    driver.get(f"/become_user/{super_admin_user_two_groups.id}")
    driver.get(f"/group/{public_group2.id}")
    driver.wait_for_xpath('//div[text()="pending"]')
    driver.click_xpath(f'//*[@data-testid="acceptRequestButton{user.id}"]')
    driver.wait_for_xpath('//div[text()="accepted"]')
    driver.wait_for_xpath(f'//a[text()="{user.username}"]')
