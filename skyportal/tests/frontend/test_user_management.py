def test_delete_group_user(driver, super_admin_user, user, public_group):
    driver.get(f'/become_user/{super_admin_user.id}')
    driver.get('/user_management')
    group_user_div = driver.wait_for_xpath(
        f"//div[@id='deleteGroupUserButton_{user.id}_{public_group.id}']"
    )
    del_svg = group_user_div.find_element_by_xpath(
        "//*[contains(@class, 'MuiChip-deleteIcon')]"
    )
    del_svg.click()
    driver.wait_for_xpath(
        f"//div[text()='User successfully removed from specified group.']"
    )
