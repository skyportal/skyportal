import uuid

import pytest


@pytest.mark.flaky(reruns=2)
def test_add_token(driver, user):
    token_name = str(uuid.uuid4())
    driver.get(f"/become_user/{user.id}")
    driver.get("/profile")
    driver.wait_for_xpath('//*[@data-testid="acls[0]"]').click()
    driver.wait_for_xpath('//*[@data-testid="acls[1]"]').click()
    driver.wait_for_xpath('//input[@name="name"]').send_keys(token_name)
    driver.wait_for_xpath('//button[contains(.,"Generate Token")]').click()
    driver.wait_for_xpath(f'//td[contains(.,"{token_name}")]')


@pytest.mark.flaky(reruns=2)
def test_cannot_create_more_than_one_token(driver, user, view_only_token):
    token_name = str(uuid.uuid4())
    driver.get(f"/become_user/{user.id}")
    driver.get("/profile")
    driver.wait_for_xpath('//*[@data-testid="acls[0]"]').click()
    driver.wait_for_xpath('//*[@data-testid="acls[1]"]').click()
    driver.wait_for_xpath('//input[@name="name"]').send_keys(token_name)
    driver.wait_for_xpath('//button[contains(.,"Generate Token")]').click()
    driver.wait_for_xpath(
        '//*[text()="You have reached the maximum number of tokens allowed for your account type."]'
    )


@pytest.mark.flaky(reruns=2)
def test_delete_token(driver, user, view_only_token):
    driver.get(f"/become_user/{user.id}")
    driver.get("/profile")
    driver.wait_for_xpath(f'//input[@value="{view_only_token}"]')
    driver.click_xpath('//button[contains(text(),"Delete")]')
    driver.wait_for_xpath_to_disappear(f'//input[@value="{view_only_token}"]')


@pytest.mark.flaky(reruns=2)
def test_add_duplicate_token_error_message(driver, super_admin_user):
    token_name = str(uuid.uuid4())
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get("/profile")
    driver.wait_for_xpath('//*[@data-testid="acls[0]"]').click()
    driver.wait_for_xpath('//*[@data-testid="acls[1]"]').click()
    driver.wait_for_xpath('//input[@name="name"]').send_keys(token_name)
    driver.wait_for_xpath('//button[contains(.,"Generate Token")]').click()
    driver.wait_for_xpath(f'//td[contains(.,"{token_name}")]')

    driver.wait_for_xpath('//input[@name="name"]').send_keys(token_name)
    driver.wait_for_xpath('//button[contains(.,"Generate Token")]').click()
    driver.wait_for_xpath('//div[contains(.,"Duplicate token name")]')


@pytest.mark.flaky(reruns=2)
def test_sys_admin_can_create_multiple_tokens(driver, super_admin_user):
    token_name = str(uuid.uuid4())
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get("/profile")
    driver.wait_for_xpath('//*[@data-testid="acls[0]"]').click()
    driver.wait_for_xpath('//*[@data-testid="acls[1]"]').click()
    driver.wait_for_xpath('//input[@name="name"]').send_keys(token_name)
    driver.wait_for_xpath('//button[contains(.,"Generate Token")]').click()
    driver.wait_for_xpath(f'//td[contains(.,"{token_name}")]')

    token2_name = str(uuid.uuid4())
    driver.wait_for_xpath('//*[@data-testid="acls[0]"]').click()
    driver.wait_for_xpath('//input[@name="name"]').send_keys(token2_name)
    driver.wait_for_xpath('//button[contains(.,"Generate Token")]').click()
    driver.wait_for_xpath(f'//td[contains(.,"{token2_name}")]')
