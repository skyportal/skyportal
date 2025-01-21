import uuid

import pytest

from baselayer.app.env import load_env

_, cfg = load_env()


@pytest.mark.flaky(reruns=2)
@pytest.mark.xfail(strict=False)
def test_add_filter(driver, super_admin_user, user, public_group, public_stream):
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get("/groups")
    driver.wait_for_xpath('//h6[text()="All Groups"]')
    el = driver.wait_for_xpath(f'//a[contains(.,"{public_group.name}")]')
    driver.execute_script("arguments[0].click();", el)
    # add stream
    driver.wait_for_xpath('//button[contains(.,"Add stream")]').click()
    driver.wait_for_xpath('//input[@name="stream_id"]/..', timeout=10).click()
    driver.wait_for_xpath(f'//li[contains(.,"{public_stream.id}")]', timeout=10)
    stream = driver.switch_to.active_element
    stream.click()
    add_stream = driver.wait_for_xpath_to_be_clickable('//button[@type="submit"]')
    driver.execute_script("arguments[0].click();", add_stream)

    # add filter
    filter_name = str(uuid.uuid4())
    driver.wait_for_xpath_to_be_clickable(
        '//button[contains(.,"Add filter")]', timeout=10
    )
    flt = driver.switch_to.active_element
    flt.click()
    driver.click_xpath('//button[contains(.,"Add filter")]')
    driver.click_xpath('//input[@name="filter_name"]/..', timeout=10)
    driver.wait_for_xpath('//input[@name="filter_name"]').send_keys(filter_name)
    driver.click_xpath(
        '//input[@name="filter_stream_id"]/..', wait_clickable=False, timeout=10
    )
    driver.wait_for_xpath(f'//li[contains(.,"{public_stream.id}")]', timeout=10)
    stream = driver.switch_to.active_element
    stream.click()
    add_filter = driver.wait_for_xpath('//button[@type="submit"]', timeout=10)
    driver.execute_script("arguments[0].click();", add_filter)
    driver.wait_for_xpath(f'//span[contains(.,"{filter_name}")]', timeout=10)
    assert (
        len(driver.find_elements_by_xpath(f'//span[contains(.,"{filter_name}")]')) == 1
    )

    # go to filter page
    driver.click_xpath(f'//span[contains(.,"{filter_name}")]')
    driver.wait_for_xpath(f'//h6[contains(.,"{filter_name}")]', timeout=10)
    # driver.wait_for_xpath(f"//h6[text()='Filter:&nbsp;&nbsp;{filter_name}']")
