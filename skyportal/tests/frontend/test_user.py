def test_user_info(driver, super_admin_user):
    user = super_admin_user
    driver.get(f'/become_user/{user.id}')
    driver.get(f'/user/{user.id}')
    driver.wait_for_xpath(f'//div[contains(.,"{user.username}")]')
    for acl in user.permissions:
        permission = f'//ul/li[contains(.,"{acl}")]'
        driver.wait_for_xpath(permission)
