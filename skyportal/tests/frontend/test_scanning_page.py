import uuid
import time

from skyportal.tests import api


def test_candidates_page_render(driver, user, public_candidate):
    driver.get(f"/become_user/{user.id}")
    driver.get("/candidates")
    driver.wait_for_xpath(f'//a[text()="{public_candidate.id}"]')


def test_candidate_group_filtering(
    driver,
    user,
    public_candidate,
    public_filter,
    public_group,
    upload_data_token,
    manage_groups_token,
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
                "filter_ids": [public_filter.id],
            },
            token=upload_data_token,
        )
        assert status == 200
        assert data["data"]["id"] == f"{candidate_id}_{i}"

    status, data = api(
        "POST",
        "groups",
        data={"name": str(uuid.uuid4()), "group_admins": [user.username]},
        token=manage_groups_token,
    )
    assert status == 200

    driver.get(f"/become_user/{user.id}")
    driver.get("/candidates")
    for i in range(5):
        driver.wait_for_xpath(f'//a[text()="{candidate_id}_{i}"]')
    group_checkbox = driver.wait_for_xpath(f'//input[starts-with(@name,"groupIDs[0]")]')
    driver.scroll_to_element_and_click(group_checkbox)
    submit_button = driver.wait_for_xpath('//span[text()="Submit"]')
    driver.scroll_to_element_and_click(submit_button)
    for i in range(5):
        driver.wait_for_xpath_to_disappear(f'//a[text()="{candidate_id}_{i}"]')
    driver.scroll_to_element_and_click(group_checkbox)
    driver.scroll_to_element_and_click(submit_button)
    for i in range(5):
        driver.wait_for_xpath(f'//a[text()="{candidate_id}_{i}"]')


def test_candidate_unsaved_only_filtering(
    driver,
    user,
    public_candidate,
    public_filter,
    public_group,
    upload_data_token,
    manage_groups_token,
):
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
            },
            token=upload_data_token,
        )
        assert status == 200
        assert data["data"]["id"] == f"{candidate_id}_{i}"

    driver.get(f"/become_user/{user.id}")
    driver.get("/candidates")
    for i in range(5):
        driver.wait_for_xpath(f'//a[text()="{candidate_id}_{i}"]')
    unsaved_only_checkbox = driver.wait_for_xpath('//input[@name="unsavedOnly"]')
    driver.scroll_to_element_and_click(unsaved_only_checkbox)
    submit_button = driver.wait_for_xpath('//span[text()="Submit"]')
    driver.scroll_to_element_and_click(submit_button)
    for i in range(5):
        driver.wait_for_xpath_to_disappear(f'//a[text()="{candidate_id}_{i}"]')
    driver.scroll_to_element_and_click(unsaved_only_checkbox)
    driver.scroll_to_element_and_click(submit_button)
    for i in range(5):
        driver.wait_for_xpath(f'//a[text()="{candidate_id}_{i}"]')


def test_candidate_date_filtering(
    driver,
    user,
    public_candidate,
    public_filter,
    public_group,
    upload_data_token,
    ztf_camera,
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
                "filter_ids": [public_filter.id],
            },
            token=upload_data_token,
        )
        assert status == 200
        assert data["data"]["id"] == f"{candidate_id}_{i}"

        status, data = api(
            "POST",
            "photometry",
            data={
                "obj_id": f"{candidate_id}_{i}",
                "mjd": 58000.0,
                "instrument_id": ztf_camera.id,
                "flux": 12.24,
                "fluxerr": 0.031,
                "zp": 25.0,
                "magsys": "ab",
                "filter": "ztfr",
                "group_ids": [public_group.id],
            },
            token=upload_data_token,
        )
        assert status == 200

    driver.get(f"/become_user/{user.id}")
    driver.get("/candidates")
    for i in range(5):
        driver.wait_for_xpath(f'//a[text()="{candidate_id}_{i}"]')
    start_date_input = driver.wait_for_xpath("//input[@name='startDate']")
    start_date_input.clear()
    start_date_input.send_keys("20001212")
    end_date_input = driver.wait_for_xpath("//input[@name='endDate']")
    end_date_input.clear()
    end_date_input.send_keys("20011212")
    time.sleep(0.1)
    submit_button = driver.wait_for_xpath('//span[text()="Submit"]')
    driver.scroll_to_element_and_click(submit_button)
    for i in range(5):
        driver.wait_for_xpath_to_disappear(f'//a[text()="{candidate_id}_{i}"]', 10)
    end_date_input.clear()
    end_date_input.send_keys("20901212")
    time.sleep(0.1)
    driver.scroll_to_element_and_click(submit_button)
    for i in range(5):
        driver.wait_for_xpath(f'//a[text()="{candidate_id}_{i}"]', 10)


def test_save_candidate_quick_save(
    driver, group_admin_user, public_group, public_candidate
):
    driver.get(f"/become_user/{group_admin_user.id}")
    driver.get("/candidates")
    driver.wait_for_xpath(f'//a[text()="{public_candidate.id}"]')
    save_button = driver.wait_for_xpath(
        f'//button[@name="initialSaveCandidateButton{public_candidate.id}"]'
    )
    driver.scroll_to_element_and_click(save_button)
    driver.wait_for_xpath_to_disappear(
        f'//button[@name="initialSaveCandidateButton{public_candidate.id}"]'
    )
    driver.wait_for_xpath('//a[text()="Previously Saved"]')


def test_save_candidate_select_groups(
    driver, group_admin_user, public_group, public_candidate
):
    driver.get(f"/become_user/{group_admin_user.id}")
    driver.get("/candidates")
    driver.wait_for_xpath(f'//a[text()="{public_candidate.id}"]')
    carat = driver.wait_for_xpath(
        f'//button[@name="saveCandidateButtonDropDownArrow{public_candidate.id}"]'
    )
    driver.scroll_to_element_and_click(carat)
    driver.wait_for_xpath_to_be_clickable(
        f'//*[@name="buttonMenuOption{public_candidate.id}_Select groups & save"]'
    ).click()
    save_button = driver.wait_for_xpath_to_be_clickable(
        f'//button[@name="initialSaveCandidateButton{public_candidate.id}"]'
    )
    driver.scroll_to_element_and_click(save_button)

    assert driver.wait_for_xpath("//input[@name='group_ids[0]']").is_selected()
    second_save_button = driver.wait_for_xpath(
        f'//button[@name="finalSaveCandidateButton{public_candidate.id}"]'
    )
    second_save_button.click()
    driver.wait_for_xpath_to_disappear(
        f'//button[@name="initialSaveCandidateButton{public_candidate.id}"]'
    )
    driver.wait_for_xpath('//a[text()="Previously Saved"]')


def test_save_candidate_no_groups_error_message(
    driver, group_admin_user, public_group, public_candidate
):
    driver.get(f"/become_user/{group_admin_user.id}")
    driver.get("/candidates")
    driver.wait_for_xpath(f'//a[text()="{public_candidate.id}"]')
    carat = driver.wait_for_xpath_to_be_clickable(
        f'//button[@name="saveCandidateButtonDropDownArrow{public_candidate.id}"]'
    )
    driver.scroll_to_element_and_click(carat)
    driver.wait_for_xpath_to_be_clickable(
        f'//*[@name="buttonMenuOption{public_candidate.id}_Select groups & save"]'
    ).click()
    save_button = driver.wait_for_xpath_to_be_clickable(
        f'//button[@name="initialSaveCandidateButton{public_candidate.id}"]'
    )
    driver.scroll_to_element_and_click(save_button)

    group_checkbox = driver.wait_for_xpath("//input[@name='group_ids[0]']")
    assert group_checkbox.is_selected()
    group_checkbox.click()
    assert not group_checkbox.is_selected()
    second_save_button = driver.wait_for_xpath_to_be_clickable(
        f'//button[@name="finalSaveCandidateButton{public_candidate.id}"]'
    )
    second_save_button.click()
    driver.wait_for_xpath('//div[contains(.,"Select at least one group")]')
