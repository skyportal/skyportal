def test_user_info(driver, super_admin_user):
    user = super_admin_user
    driver.get(f'/become_user/{user.id}')
    driver.get(f'/user/{user.id}')
    driver.wait_for_xpath(f'//div[contains(.,"{user.username}")]')
    pg_src = driver.page_source
    for acl in user.permissions:
        assert acl in pg_src
