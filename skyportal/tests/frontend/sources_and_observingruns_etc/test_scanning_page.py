import datetime
import time
import uuid

import pytest
from selenium.webdriver import ActionChains
from tdtax import __version__, taxonomy

from skyportal.tests import api


@pytest.mark.flaky(reruns=2)
def test_candidate_group_filtering(
    driver,
    user,
    public_candidate,
    public_filter,
    public_group,
    upload_data_token,
    super_admin_token,
):
    candidate_id = str(uuid.uuid4())
    for i in range(5):
        status, data = api(
            "POST",
            "candidates",
            data={
                "id": f"{candidate_id}_{i}",
                "ra": 234.22,
                "dec": -22.33,
                "redshift": 3,
                "altdata": {"simbad": {"class": "RRLyr"}},
                "transient": False,
                "ra_dis": 2.3,
                "passed_at": str(datetime.datetime.utcnow()),
                "filter_ids": [public_filter.id],
            },
            token=upload_data_token,
        )
        assert status == 200

    status, data = api(
        "POST",
        "groups",
        data={"name": str(uuid.uuid4()), "group_admins": [user.id]},
        token=super_admin_token,
    )
    new_group_id = data["data"]["id"]
    assert status == 200

    driver.get(f"/become_user/{user.id}")
    driver.get("/candidates")
    group_checkbox = driver.wait_for_xpath(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]'
    )
    driver.scroll_to_element_and_click(group_checkbox)
    submit_button = driver.wait_for_xpath('//button[text()="Search"]')
    driver.scroll_to_element_and_click(submit_button)

    driver.wait_for_xpath(
        '//*[contains(., "Found 6 candidates.")]'
    )  # the 5 candidates we added and the public candidate

    driver.scroll_to_element_and_click(group_checkbox)
    driver.click_xpath(
        f'//*[@data-testid="filteringFormGroupCheckbox-{new_group_id}"]',
        wait_clickable=False,
    )
    driver.scroll_to_element_and_click(submit_button)

    driver.wait_for_xpath('//*[contains(., "Found 0 candidates.")]')


@pytest.mark.flaky(reruns=2)
def test_candidate_saved_status_filtering(
    driver,
    user,
    public_candidate,
    public_filter,
    public_group,
    upload_data_token,
    manage_groups_token,
):
    # This test just tests basic unsaved/saved filtering to test integration of
    # the front-end form. More detailed testing of all options are covered in
    # the API tests.
    candidate_id = str(uuid.uuid4())
    for i in range(5):
        status, data = api(
            "POST",
            "sources",
            data={
                "id": f"{candidate_id}_{i}",
                "ra": 234.22,
                "dec": -22.33,
                "redshift": 3,
                "altdata": {"simbad": {"class": "RRLyr"}},
                "transient": False,
                "ra_dis": 2.3,
                "group_ids": [public_group.id],
            },
            token=upload_data_token,
        )
        assert status == 200
        status, data = api(
            "POST",
            "candidates",
            data={
                "id": f"{candidate_id}_{i}",
                "ra": 234.22,
                "dec": -22.33,
                "redshift": 3,
                "altdata": {"simbad": {"class": "RRLyr"}},
                "transient": False,
                "ra_dis": 2.3,
                "filter_ids": [public_filter.id],
                "passed_at": str(datetime.datetime.utcnow()),
            },
            token=upload_data_token,
        )
        assert status == 200

    driver.get(f"/become_user/{user.id}")
    driver.get("/candidates")
    driver.click_xpath(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]',
        wait_clickable=False,
    )
    # Set to candidates not saved to any accessibe groups
    driver.click_xpath("//*[@data-testid='savedStatusSelect']")
    driver.click_xpath(
        "//li[@data-value='notSavedToAnyAccessible']", scroll_parent=True
    )
    driver.click_xpath('//button[text()="Search"]')

    driver.wait_for_xpath(
        '//*[contains(., "Found 1 candidates.")]'
    )  # the public candidate

    # Set to candidates is saved to any accessibe groups and submit again
    driver.click_xpath("//*[@data-testid='savedStatusSelect']")
    driver.click_xpath("//li[@data-value='savedToAnyAccessible']", scroll_parent=True)
    driver.click_xpath('//button[text()="Search"]')

    driver.wait_for_xpath(
        '//*[contains(., "Found 5 candidates.")]'
    )  # the 5 candidates we added


@pytest.mark.flaky(reruns=2)
def test_save_candidate_quick_save(
    driver, group_admin_user, public_group, public_candidate
):
    driver.get(f"/become_user/{group_admin_user.id}")
    driver.get("/candidates")
    driver.click_xpath(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]',
        wait_clickable=False,
    )
    driver.click_xpath('//button[text()="Search"]', wait_clickable=False)
    driver.wait_for_xpath(f'//a[@data-testid="{public_candidate.id}"]')
    save_button = driver.wait_for_xpath(
        f'//button[@name="initialSaveCandidateButton{public_candidate.id}"]'
    )
    driver.scroll_to_element_and_click(save_button)
    driver.get("/candidates")
    driver.click_xpath(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]',
        wait_clickable=False,
    )
    driver.click_xpath('//button[text()="Search"]', wait_clickable=False)
    driver.wait_for_xpath(f'//a[@data-testid="{public_candidate.id}"]')
    driver.wait_for_xpath('//span[text()="Previously Saved"]')


@pytest.mark.flaky(reruns=2)
def test_save_candidate_select_groups(
    driver, group_admin_user, public_group, public_candidate
):
    driver.get(f"/become_user/{group_admin_user.id}")
    driver.get("/candidates")
    driver.click_xpath(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]',
        wait_clickable=False,
    )
    driver.click_xpath('//button[text()="Search"]')
    driver.wait_for_xpath(f'//a[@data-testid="{public_candidate.id}"]')
    carat = driver.wait_for_xpath(
        f'//button[@name="saveCandidateButtonDropDownArrow{public_candidate.id}"]'
    )
    driver.scroll_to_element_and_click(carat)
    driver.execute_script(
        "arguments[0].click();",
        driver.wait_for_xpath_to_be_clickable(
            f'//*[@name="buttonMenuOption{public_candidate.id}_Select groups & save"]'
        ),
    )
    save_button = driver.wait_for_xpath_to_be_clickable(
        f'//button[@name="initialSaveCandidateButton{public_candidate.id}"]'
    )
    driver.scroll_to_element_and_click(save_button)

    second_save_button = driver.wait_for_xpath(
        f'//button[@name="finalSaveCandidateButton{public_candidate.id}"]'
    )
    second_save_button.click()
    driver.get("/candidates")
    driver.click_xpath(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]',
        wait_clickable=False,
    )
    driver.click_xpath('//button[text()="Search"]')
    driver.wait_for_xpath('//span[text()="Previously Saved"]')


@pytest.mark.flaky(reruns=2)
def test_save_candidate_no_groups_error_message(
    driver, group_admin_user, public_group, public_candidate
):
    driver.get(f"/become_user/{group_admin_user.id}")
    driver.get("/candidates")
    driver.click_xpath(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]',
        wait_clickable=False,
    )
    driver.click_xpath('//button[text()="Search"]')
    driver.wait_for_xpath(f'//a[@data-testid="{public_candidate.id}"]')
    carat = driver.wait_for_xpath_to_be_clickable(
        f'//button[@name="saveCandidateButtonDropDownArrow{public_candidate.id}"]'
    )
    driver.scroll_to_element_and_click(carat)
    driver.execute_script(
        "arguments[0].click();",
        driver.wait_for_xpath_to_be_clickable(
            f'//*[@name="buttonMenuOption{public_candidate.id}_Select groups & save"]'
        ),
    )
    save_button = driver.wait_for_xpath_to_be_clickable(
        f'//button[@name="initialSaveCandidateButton{public_candidate.id}"]'
    )
    driver.scroll_to_element_and_click(save_button)

    group_checkbox = driver.wait_for_xpath(
        f"//*[@data-testid='saveCandGroupCheckbox-{public_group.id}']"
    )
    group_checkbox.click()
    second_save_button = driver.wait_for_xpath_to_be_clickable(
        f'//button[@name="finalSaveCandidateButton{public_candidate.id}"]'
    )
    second_save_button.click()
    driver.wait_for_xpath('//div[contains(.,"Select at least one group")]')


# @pytest.mark.flaky(reruns=2)
def test_submit_annotations_sorting(
    driver,
    view_only_user,
    public_group,
    public_candidate,
    public_candidate2,
    annotation_token,
):
    origin = str(uuid.uuid4())[:5]
    status, data = api(
        "POST",
        f"sources/{public_candidate.id}/annotations",
        data={
            "obj_id": public_candidate.id,
            "origin": origin,
            "data": {"numeric_field": 1},
        },
        token=annotation_token,
    )
    assert status == 200
    status, data = api(
        "POST",
        f"sources/{public_candidate2.id}/annotations",
        data={
            "obj_id": public_candidate2.id,
            "origin": origin,
            "data": {"numeric_field": 2},
        },
        token=annotation_token,
    )
    assert status == 200

    # origins are cached, so we wait for the cache to invalidate (5 seconds in test config)
    time.sleep(3)

    driver.get(f"/become_user/{view_only_user.id}")
    driver.get("/candidates")
    driver.click_xpath(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]',
        wait_clickable=False,
    )

    driver.click_xpath('//input[@id="annotationSortingOriginSelect"]')
    driver.click_xpath(f'//li[text()="{origin}"]')
    driver.click_xpath('//input[@id="annotationSortingKeySelect"]')
    driver.click_xpath('//li[text()="numeric_field"]')
    driver.click_xpath('//input[@id="annotationSortingOrderSelect"]')
    driver.click_xpath('//li[text()="Ascending"]')

    driver.click_xpath('//button[text()="Search"]')
    driver.wait_for_xpath(f'//a[@data-testid="{public_candidate.id}"]')

    # Check that results come back as expected
    # candidate-1 should have the lowest value
    driver.wait_for_xpath(
        '//*[contains(@data-testid, "candidate-1")][.//*[contains(.,"1.0000")]]'
    )
    driver.wait_for_xpath(
        '//*[contains(@data-testid, "candidate-2")][.//*[contains(.,"2.0000")]]'
    )

    # Check to see that sorting button has become enabled, and click
    driver.wait_for_xpath_to_be_clickable(
        "//button[@data-testid='sortOnAnnotationButton']"
    )
    driver.click_xpath("//button[@data-testid='sortOnAnnotationButton']")

    # the order should now be reversed
    driver.wait_for_xpath(
        '//*[contains(@data-testid, "candidate-1")][.//*[contains(.,"2.0000")]]'
    )
    driver.wait_for_xpath(
        '//*[contains(@data-testid, "candidate-2")][.//*[contains(.,"1.0000")]]'
    )


def test_candidate_classifications_filtering(
    driver,
    user,
    public_candidate,
    public_filter,
    public_group,
    upload_data_token,
    taxonomy_token,
    classification_token,
):
    # Post an object with a classification
    candidate_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": candidate_id,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token,
    )
    assert status == 200

    status, data = api(
        "POST",
        "sources",
        data={"id": candidate_id},
        token=upload_data_token,
    )
    assert status == 200
    status, data = api(
        "POST",
        "taxonomy",
        data={
            "name": "test taxonomy" + str(uuid.uuid4()),
            "hierarchy": taxonomy,
            "group_ids": [public_group.id],
            "provenance": f"tdtax_{__version__}",
            "version": __version__,
            "isLatest": True,
        },
        token=taxonomy_token,
    )
    assert status == 200
    taxonomy_id = data["data"]["taxonomy_id"]

    status, data = api(
        "POST",
        "classification",
        data={
            "obj_id": candidate_id,
            "classification": "Algol",
            "taxonomy_id": taxonomy_id,
            "probability": 1.0,
            "group_ids": [public_group.id],
        },
        token=classification_token,
    )
    assert status == 200

    driver.get(f"/become_user/{user.id}")
    driver.get("/candidates")
    driver.click_xpath(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]',
        wait_clickable=False,
    )
    driver.click_xpath("//div[@id='classifications-select']")
    driver.click_xpath("//li[@data-value='Algol']", scroll_parent=True)

    # Click somewhere outside to remove focus from classification select
    header = driver.wait_for_xpath("//header")
    ActionChains(driver).move_to_element(header).click().perform()

    driver.click_xpath('//button[text()="Search"]')
    # Should see the posted classification
    driver.wait_for_xpath(f'//a[@data-testid="{candidate_id}"]')

    # Now search for a different classification
    driver.click_xpath("//div[@id='classifications-select']")
    # Clear old classification selection
    driver.click_xpath("//li[@data-value='Algol']", scroll_parent=True)
    driver.click_xpath("//li[@data-value='AGN']", scroll_parent=True)
    # Click somewhere outside to remove focus from classification select
    header = driver.wait_for_xpath("//header")
    ActionChains(driver).move_to_element(header).click().perform()
    driver.click_xpath('//button[text()="Search"]')
    # Should no longer see the classification
    driver.wait_for_xpath_to_disappear(f'//a[@data-testid="{candidate_id}"]')


def test_candidate_redshift_filtering(
    driver,
    user,
    public_filter,
    public_group,
    upload_data_token,
):
    # Post candidates with different redshifts
    obj_id1 = str(uuid.uuid4())
    obj_id2 = str(uuid.uuid4())
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id1,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 0,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token,
    )
    assert status == 200
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id2,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 1,
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token,
    )
    assert status == 200

    driver.get(f"/become_user/{user.id}")
    driver.get("/candidates")
    driver.click_xpath(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]',
        wait_clickable=False,
    )
    min_box = driver.wait_for_xpath("//input[@id='minimum-redshift']")
    min_text = "0"
    min_box.send_keys(min_text)
    max_box = driver.wait_for_xpath("//input[@id='maximum-redshift']")
    max_text = "0.5"
    max_box.send_keys(max_text)
    driver.click_xpath('//button[text()="Search"]')
    # Should see the obj_id1 but not obj_id2
    driver.wait_for_xpath(f'//a[@data-testid="{obj_id1}"]')
    driver.wait_for_xpath_to_disappear(f'//a[@data-testid="{obj_id2}"]')


def test_candidate_rejection_filtering(
    driver,
    user,
    public_group,
    upload_data_token,
    public_filter,
):
    candidate_id = str(uuid.uuid4())

    status, data = api(
        "POST",
        "candidates",
        data={
            "id": candidate_id,
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "altdata": {"simbad": {"class": "RRLyr"}},
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(datetime.datetime.utcnow()),
        },
        token=upload_data_token,
    )
    assert status == 200

    driver.get(f"/become_user/{user.id}")
    driver.get("/candidates")
    driver.click_xpath(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]',
        wait_clickable=False,
    )

    driver.click_xpath('//button[text()="Search"]')

    # make sure candidate appears and click the icon to reject it
    driver.click_xpath(f'//*[@data-testid="rejected-visible_{candidate_id}"]')

    driver.click_xpath('//button[text()="Search"]')

    # now the candidate doesn't show up anymore
    driver.wait_for_xpath('//*[contains(., "Found 0 candidates.")]')

    # choose to show rejected now
    driver.click_xpath('//*[@data-testid="rejectedStatusSelect"]')

    driver.click_xpath('//button[text()="Search"]')

    # make sure candidate appears and that it has a "rejected" icon
    driver.wait_for_xpath(f'//*[@data-testid="rejected_invisible_{candidate_id}"]')


def test_add_scanning_profile(
    driver, user, public_group, public_source, annotation_token
):
    # Post an annotation to the test source, to test setting annotation sorting
    status, _ = api(
        "POST",
        f"sources/{public_source.id}/annotations",
        data={
            "obj_id": public_source.id,
            "origin": "kowalski",
            "data": {"offset_from_host_galaxy": 1.5},
            "group_ids": [public_group.id],
        },
        token=annotation_token,
    )
    assert status == 200

    # origins are cached, so we wait for the cache to invalidate (2 seconds in test config)
    time.sleep(2)

    driver.get(f"/become_user/{user.id}")
    driver.get("/candidates")
    driver.click_xpath('//button[@data-testid="manageScanningProfilesButton"]')

    # click on the + icon on the top right of the table to open the form
    driver.click_xpath('//button[@name="new_scanning_profile"]')

    # let the form initialize, load the groups, etc.
    time.sleep(1)

    # Fill out form
    name_input = driver.wait_for_xpath('//div[@data-testid="profile-name"]//input')
    name_input.clear()
    name_input.send_keys("profile1")

    time_range_input = driver.wait_for_xpath('//div[@data-testid="timeRange"]//input')
    time_range_input.clear()
    time_range_input.send_keys("48")

    driver.click_xpath('//div[@aria-labelledby="savedStatusSelectLabel"]')
    saved_status_option = "and is saved to at least one group I have access to"
    driver.click_xpath(f'//li[text()="{saved_status_option}"]')

    redshift_minimum_input = driver.wait_for_xpath(
        '//div[@data-testid="profile-minimum-redshift"]//input'
    )
    redshift_minimum_input.send_keys("0.0")
    redshift_maximum_input = driver.wait_for_xpath(
        '//div[@data-testid="profile-maximum-redshift"]//input'
    )
    redshift_maximum_input.send_keys("1.0")
    driver.click_xpath('//div[@data-testid="annotation-sorting-accordion"]')
    driver.click_xpath(
        '//div[@data-testid="profileAnnotationSortingOriginSelect"]', scroll_parent=True
    )
    driver.click_xpath('//li[text()="kowalski"]')
    driver.click_xpath('//div[@data-testid="profileAnnotationSortingKeySelect"]')
    driver.click_xpath('//li[text()="offset_from_host_galaxy"]')
    driver.click_xpath('//div[@data-testid="profileAnnotationSortingOrderSelect"]')
    driver.click_xpath('//li[text()="Descending"]')

    driver.click_xpath(
        f'//span[@data-testid="profileFilteringFormGroupCheckbox-{public_group.id}"]'
    )

    # Submit and check it shows up in table of profiles
    driver.click_xpath(
        '//button[@data-testid="saveScanningProfileButton"]', scroll_parent=True
    )
    driver.wait_for_xpath(f'//div[text()="{saved_status_option}"]')

    # Navigate back to scanning page and check that form is populated properly
    driver.click_xpath('//button[@data-testid="closeScanningProfilesButton"]')
    # driver.wait_for_xpath(f'//div[text()="{saved_status_option}"]')
    driver.wait_for_xpath('//input[@id="minimum-redshift"][@value="0.0"]')
    driver.wait_for_xpath('//input[@id="maximum-redshift"][@value="1.0"]')
    driver.wait_for_xpath(
        f'//span[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]'
    )
    # driver.wait_for_xpath('//div[text()="kowalski"]')
    driver.wait_for_xpath('//input[@value="offset_from_host_galaxy"]')
    driver.wait_for_xpath('//input[@value="Descending"]')


def test_delete_scanning_profile(driver, user, public_group):
    driver.get(f"/become_user/{user.id}")
    driver.get("/candidates")
    driver.click_xpath('//button[@data-testid="manageScanningProfilesButton"]')

    # click on the + icon on the top right of the table to open the form
    driver.click_xpath('//button[@name="new_scanning_profile"]')

    # let the form initialize, load the groups, etc.
    time.sleep(1)

    # Fill out form
    name_input = driver.wait_for_xpath('//div[@data-testid="profile-name"]//input')
    name_input.clear()
    name_input.send_keys("profile1")

    time_range_input = driver.wait_for_xpath('//div[@data-testid="timeRange"]//input')
    time_range_input.clear()
    time_range_input.send_keys("123")

    driver.click_xpath(
        f'//span[@data-testid="profileFilteringFormGroupCheckbox-{public_group.id}"]',
        scroll_parent=True,
    )

    # Submit and check it shows up in table of profiles
    driver.click_xpath('//button[@data-testid="saveScanningProfileButton"]')
    driver.wait_for_xpath('//div[text()="123hrs"]')

    # Delete and check that it disappears
    driver.click_xpath('//button[@id="delete_button_0"]')
    driver.wait_for_xpath_to_disappear('//div[text()="123hrs"]')


@pytest.mark.flaky(reruns=2)
def test_load_scanning_profile(
    driver, user, public_group, public_source, annotation_token
):
    driver.get(f"/become_user/{user.id}")
    driver.get("/candidates")

    # Add two scanning profiles with different max redshifts
    driver.click_xpath('//button[@data-testid="manageScanningProfilesButton"]')

    # click on the + icon on the top right of the table to open the form
    driver.click_xpath('//button[@name="new_scanning_profile"]')

    # let the form initialize, load the groups, etc.
    time.sleep(1)

    redshift_maximum_input = driver.wait_for_xpath(
        '//div[@data-testid="profile-maximum-redshift"]//input'
    )
    redshift_maximum_input.send_keys("0.5")
    name_input = driver.wait_for_xpath('//div[@data-testid="profile-name"]//input')
    name_input.clear()
    name_input.send_keys("profile1")
    driver.click_xpath(
        f'//span[@data-testid="profileFilteringFormGroupCheckbox-{public_group.id}"]',
        scroll_parent=True,
    )
    driver.click_xpath('//button[@data-testid="saveScanningProfileButton"]')
    driver.wait_for_xpath('//div[contains(text(), "0.5")]')

    # click on the + icon on the top right of the table to open the form
    driver.click_xpath('//button[@name="new_scanning_profile"]')

    redshift_maximum_input = driver.wait_for_xpath(
        '//div[@data-testid="profile-maximum-redshift"]//input'
    )
    redshift_maximum_input.send_keys("1.0")
    name_input = driver.wait_for_xpath('//div[@data-testid="profile-name"]//input')
    name_input.clear()
    name_input.send_keys("profile2")
    driver.click_xpath(
        f'//span[@data-testid="profileFilteringFormGroupCheckbox-{public_group.id}"]',
        scroll_parent=True,
    )
    driver.click_xpath('//button[@data-testid="saveScanningProfileButton"]')
    driver.wait_for_xpath('//div[contains(text(), "1.0")]')

    # unload
    driver.click_xpath('//span[@data-testid="loaded_0"]')
    # load
    driver.click_xpath('//span[@data-testid="loaded_0"]')

    # Navigate back to scanning page and check that form is populated properly
    driver.click_xpath('//button[@data-testid="closeScanningProfilesButton"]')
    driver.wait_for_xpath('//input[@id="maximum-redshift"][@value="0.5"]')


def test_user_without_save_access_cannot_save(
    driver, super_admin_token, public_group, public_candidate, user_group2
):
    status, data = api(
        "POST",
        f"groups/{public_group.id}/users",
        data={"userID": user_group2.id, "admin": False, "canSave": False},
        token=super_admin_token,
    )
    assert status == 200

    status, data = api(
        "GET",
        f"groups/{public_group.id}?includeGroupUsers=true",
        token=super_admin_token,
    )
    group_user = None
    for gu in data["data"]["users"]:
        if gu["id"] == user_group2.id:
            group_user = gu
    assert group_user is not None
    assert not group_user["can_save"]
    assert not group_user["admin"]

    driver.get(f"/become_user/{user_group2.id}")
    driver.get("/candidates")
    driver.click_xpath(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]',
        wait_clickable=False,
    )
    driver.click_xpath('//button[text()="Search"]', wait_clickable=False)
    driver.wait_for_xpath(f'//a[@data-testid="{public_candidate.id}"]')
    save_button = driver.wait_for_xpath(
        f'//button[@name="initialSaveCandidateButton{public_candidate.id}"]'
    )
    driver.scroll_to_element_and_click(save_button)


@pytest.mark.flaky(reruns=2)
def test_add_classification_on_scanning_page(
    driver, user, public_group, taxonomy_token, public_filter, upload_data_token
):
    from ..test_profile import test_add_classification_shortcut

    shortcut_name = test_add_classification_shortcut(
        driver, user, public_group, taxonomy_token
    )
    driver.get(f"/become_user/{user.id}")
    candidate_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "candidates",
        data={
            "id": f"{candidate_id}",
            "ra": 234.22,
            "dec": -22.33,
            "redshift": 3,
            "altdata": {"simbad": {"class": "RRLyr"}},
            "transient": False,
            "ra_dis": 2.3,
            "passed_at": str(datetime.datetime.utcnow()),
            "filter_ids": [public_filter.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    driver.get("/candidates")
    group_checkbox = driver.wait_for_xpath(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]'
    )
    driver.scroll_to_element_and_click(group_checkbox)
    submit_button = driver.wait_for_xpath('//button[text()="Search"]')
    driver.scroll_to_element_and_click(submit_button)
    save_button = driver.wait_for_xpath(
        f'//button[@data-testid="saveCandidateButton_{candidate_id}"]'
    )
    driver.scroll_to_element_and_click(save_button)

    driver.get("/candidates")
    group_checkbox = driver.wait_for_xpath(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]'
    )
    driver.scroll_to_element_and_click(group_checkbox)
    submit_button = driver.wait_for_xpath('//button[text()="Search"]')
    driver.scroll_to_element_and_click(submit_button)

    add_classifications_button = driver.wait_for_xpath(
        f'//button[@data-testid="addClassificationsButton_{candidate_id}"]'
    )
    driver.scroll_to_element_and_click(add_classifications_button)
    shortcut_button = driver.wait_for_xpath(
        f'//button[@data-testid="{shortcut_name}_inDialog"]'
    )
    driver.scroll_to_element_and_click(shortcut_button)
    shortcut_button = driver.wait_for_xpath(
        '//button[@data-testid="addClassificationsButtonInDialog"]'
    )
    driver.scroll_to_element_and_click(shortcut_button)

    driver.get(f"/source/{candidate_id}")
    driver.wait_for_xpath('//span[contains(text(), "AGN")]')
    driver.wait_for_xpath('//span[contains(text(), "AM CVn")]')
