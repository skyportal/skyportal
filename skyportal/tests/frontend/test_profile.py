import pytest
import uuid
from skyportal.tests import api


def test_token_acls_options_rendering1(driver, user):
    driver.get(f"/become_user/{user.id}")
    driver.get("/profile")
    driver.wait_for_xpath('//*[@data-testid="acls[0]"]')
    driver.wait_for_xpath('//*[@data-testid="acls[1]"]')
    driver.wait_for_xpath('//*[@data-testid="acls[2]"]')
    driver.wait_for_xpath('//*[@data-testid="acls[3]"]')
    driver.wait_for_xpath_to_disappear('//*[@data-testid="acls[4]"]')


def test_token_acls_options_rendering2(driver, super_admin_user):
    driver.get(f"/become_user/{super_admin_user.id}")
    driver.get("/profile")
    for i in range(5):
        driver.wait_for_xpath(f'//*[@data-testid="acls[{i}]"]')


@pytest.mark.xfail(strict=False)
def test_add_and_see_realname_in_user_profile(driver, user):
    driver.get(f"/become_user/{user.id}")
    driver.get("/profile")
    first_name_entry = driver.wait_for_xpath('//input[@name="firstName"]')
    first_name = str(uuid.uuid4())
    first_name_entry.send_keys(first_name)
    last_name_entry = driver.wait_for_xpath('//input[@name="lastName"]')
    last_name = str(uuid.uuid4())
    last_name_entry.send_keys(last_name)

    driver.scroll_to_element_and_click(
        driver.find_element_by_xpath('//*[@id="updateProfileButton"]')
    )

    # now that we added the name, let's see if it's displayed correctly
    name_display = driver.wait_for_xpath(
        '//*[@id="userRealname"][contains(@style, "visibility: visible")]'
    ).text
    assert name_display == f"{first_name} {last_name}"


def test_add_data_to_user_profile(driver, user):
    driver.get(f"/become_user/{user.id}")
    driver.get("/profile")
    first_name_entry = driver.wait_for_xpath('//input[@name="firstName"]')
    driver.scroll_to_element_and_click(first_name_entry)
    first_name = str(uuid.uuid4())
    first_name_entry.send_keys(first_name)
    last_name_entry = driver.wait_for_xpath('//input[@name="lastName"]')
    driver.scroll_to_element_and_click(last_name_entry)
    last_name = str(uuid.uuid4())
    last_name_entry.send_keys(last_name)

    email_entry = driver.wait_for_xpath('//input[@name="email"]')
    driver.scroll_to_element_and_click(email_entry)
    email = f"{str(uuid.uuid4())[:5]}@hotmail.com"
    email_entry.clear()
    email_entry.send_keys(email)

    phone_entry = driver.wait_for_xpath('//input[@name="phone"]')
    phone = "+12128675309"
    driver.scroll_to_element_and_click(phone_entry)
    phone_entry.send_keys(phone)

    driver.scroll_to_element_and_click(
        driver.find_element_by_xpath('//*[@id="updateProfileButton"]')
    )


def test_insufficient_name_entry_in_profile(driver, user):
    driver.get(f"/become_user/{user.id}")
    driver.get("/profile")
    first_name_entry = driver.wait_for_xpath('//input[@name="firstName"]')
    driver.scroll_to_element_and_click(first_name_entry)
    first_name_entry.clear()
    last_name_entry = driver.wait_for_xpath('//input[@name="lastName"]')
    last_name = str(uuid.uuid4())
    driver.scroll_to_element_and_click(last_name_entry)
    last_name_entry.send_keys(last_name)

    driver.click_xpath('//*[@id="updateProfileButton"]')

    helper = driver.wait_for_xpath('//p[@id="firstName_id-helper-text"]')
    assert helper.text == "Required"


@pytest.mark.flaky(reruns=2)
def test_profile_dropdown(driver, user):
    test_add_data_to_user_profile(driver, user)

    # click on profile dropdown
    avatar_element = driver.wait_for_xpath("//span[contains(@data-testid, 'avatar')]")
    driver.scroll_to_element_and_click(avatar_element)

    # check dropdown contents
    driver.wait_for_xpath("//p[contains(@data-testid, 'firstLastName')]")
    driver.wait_for_xpath("//p[contains(@data-testid, 'username')]")
    driver.wait_for_xpath("//a[contains(@data-testid, 'signOutButton')]")


def test_add_scanning_profile(
    driver, user, public_group, public_source, annotation_token
):

    # Post an annotation to the test source, to test setting annotation sorting
    status, _ = api(
        'POST',
        'annotation',
        data={
            'obj_id': public_source.id,
            'origin': 'kowalski',
            'data': {'offset_from_host_galaxy': 1.5},
            'group_ids': [public_group.id],
        },
        token=annotation_token,
    )
    assert status == 200

    driver.get(f"/become_user/{user.id}")
    driver.get("/profile")
    driver.click_xpath('//button[@data-testid="addScanningProfileButton"]')

    # Fill out form
    time_range_input = driver.wait_for_xpath('//div[@data-testid="timeRange"]//input')
    time_range_input.clear()
    time_range_input.send_keys("48")

    driver.click_xpath('//div[@data-testid="savedStatusSelect"]')
    saved_status_option = "and is saved to at least one group I have access to"
    driver.click_xpath(f'//li[text()="{saved_status_option}"]')

    redshift_minimum_input = driver.wait_for_xpath(
        '//div[@data-testid="minimum-redshift"]//input'
    )
    redshift_minimum_input.send_keys("0.0")
    redshift_maximum_input = driver.wait_for_xpath(
        '//div[@data-testid="maximum-redshift"]//input'
    )
    redshift_maximum_input.send_keys("1.0")

    driver.click_xpath('//div[@data-testid="annotationSortingOriginSelect"]')
    driver.click_xpath('//li[text()="kowalski"]')
    driver.click_xpath('//div[@data-testid="annotationSortingKeySelect"]')
    driver.click_xpath('//li[text()="offset_from_host_galaxy"]')
    driver.click_xpath('//div[@data-testid="annotationSortingOrderSelect"]')
    driver.click_xpath('//li[text()="descending"]')

    driver.click_xpath(
        f'//span[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]'
    )

    # Submit and check it shows up in table of profiles
    driver.click_xpath('//button[@data-testid="saveScanningProfileButton"]')
    driver.wait_for_xpath(f'//div[text()="{saved_status_option}"]')

    # Navigate to scanning page and check that form is populated properly
    driver.get("/candidates")
    driver.wait_for_xpath(f'//div[text()="{saved_status_option}"]')
    driver.wait_for_xpath('//input[@id="minimum-redshift"][@value="0.0"]')
    driver.wait_for_xpath('//input[@id="maximum-redshift"][@value="1.0"]')
    driver.wait_for_xpath(
        f'//span[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]//input[@value]'
    )

    # TODO: Check that annotation sorting options have been set, once
    # the front-end to display that has been implemented


def test_delete_scanning_profile(driver, user, public_group):

    driver.get(f"/become_user/{user.id}")
    driver.get("/profile")
    driver.click_xpath('//button[@data-testid="addScanningProfileButton"]')

    # Fill out form
    time_range_input = driver.wait_for_xpath('//div[@data-testid="timeRange"]//input')
    time_range_input.clear()
    time_range_input.send_keys("123")

    driver.click_xpath(
        f'//span[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]'
    )

    # Submit and check it shows up in table of profiles
    driver.click_xpath('//button[@data-testid="saveScanningProfileButton"]')
    driver.wait_for_xpath('//div[text()="123hrs"]')
    # Delete and check that it disappears
    driver.click_xpath('//tr[.//div[text()="123hrs"]]//button[./span[text()="Delete"]]')
    driver.wait_for_xpath_to_disappear('//div[text()="123hrs"]')
