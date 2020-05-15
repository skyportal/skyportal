import uuid
import arrow

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
    for i in range(20):
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
    for i in range(20):
        driver.wait_for_xpath(f'//a[text()="{candidate_id}_{i}"]')
    group_checkbox = driver.wait_for_xpath(
        f'//input[starts-with(@name,"groupIDCheckBox_{public_group.id}")]'
    )
    group_checkbox.click()
    start_date_input = driver.wait_for_xpath("//input[@name='startDate']")
    start_date_input.clear()
    end_date_input = driver.wait_for_xpath("//input[@name='endDate']")
    end_date_input.clear()
    submit_button = driver.wait_for_xpath('//button[text()="Submit"]')
    submit_button.click()
    for i in range(20):
        driver.wait_for_xpath_to_disappear(f'//a[text()="{candidate_id}_{i}"]')
    group_checkbox.click()
    submit_button.click()
    for i in range(20):
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
    for i in range(20):
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

    status, data = api(
        "POST",
        "groups",
        data={"name": str(uuid.uuid4()), "group_admins": [user.username]},
        token=manage_groups_token,
    )
    assert status == 200

    driver.get(f"/become_user/{user.id}")
    driver.get("/candidates")
    for i in range(20):
        driver.wait_for_xpath(f'//a[text()="{candidate_id}_{i}"]')
    unsaved_only_checkbox = driver.wait_for_xpath('//input[@name="unsavedOnly"]')
    unsaved_only_checkbox.click()
    start_date_input = driver.wait_for_xpath("//input[@name='startDate']")
    start_date_input.clear()
    end_date_input = driver.wait_for_xpath("//input[@name='endDate']")
    end_date_input.clear()
    submit_button = driver.wait_for_xpath('//button[text()="Submit"]')
    submit_button.click()
    for i in range(20):
        driver.wait_for_xpath_to_disappear(f'//a[text()="{candidate_id}_{i}"]')
    unsaved_only_checkbox.click()
    submit_button.click()
    for i in range(20):
        driver.wait_for_xpath(f'//a[text()="{candidate_id}_{i}"]')


def test_candidate_date_filtering(
    driver, user, public_candidate, public_filter, public_group, upload_data_token
):
    candidate_id = str(uuid.uuid4())
    for i in range(20):
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
                "observed_at": arrow.utcnow().isoformat(),
                "time_format": "iso",
                "time_scale": "utc",
                "instrument_id": 1,
                "mag": 12.24,
                "e_mag": 0.031,
                "lim_mag": 14.1,
                "filter": "V",
            },
            token=upload_data_token,
        )
        assert status == 200

    driver.get(f"/become_user/{user.id}")
    driver.get("/candidates")
    for i in range(20):
        driver.wait_for_xpath(f'//a[text()="{candidate_id}_{i}"]')
    start_date_input = driver.wait_for_xpath("//input[@name='startDate']")
    start_date_input.clear()
    start_date_input.send_keys("2000-12-12T00:00:00")
    end_date_input = driver.wait_for_xpath("//input[@name='endDate']")
    end_date_input.clear()
    end_date_input.send_keys("2001-12-12T00:00:01")
    submit_button = driver.wait_for_xpath('//button[text()="Submit"]')
    submit_button.click()
    for i in range(20):
        driver.wait_for_xpath_to_disappear(f'//a[text()="{candidate_id}_{i}"]', 10)
    end_date_input.clear()
    end_date_input.send_keys("2090-12-12T00:00:00")
    submit_button.click()
    for i in range(20):
        driver.wait_for_xpath(f'//a[text()="{candidate_id}_{i}"]', 10)


def test_save_candidate(driver, group_admin_user, public_group, public_candidate):
    driver.get(f"/become_user/{group_admin_user.id}")
    driver.get("/candidates")
    driver.wait_for_xpath(f'//a[text()="{public_candidate.id}"]')
    first_save_button = driver.wait_for_xpath('//button[text()="Save as source"]')
    first_save_button.click()
    driver.wait_for_xpath(f"//input[@name='{public_group.id}']").click()
    second_save_button = driver.wait_for_xpath('//button[text()="Save"]')
    second_save_button.click()
    driver.wait_for_xpath_to_disappear('//button[text()="Save as source"]')
    driver.wait_for_xpath('//a[text()="Previously Saved"]')


def test_save_candidate_no_groups_error_message(
    driver, group_admin_user, public_group, public_candidate
):
    driver.get(f"/become_user/{group_admin_user.id}")
    driver.get("/candidates")
    driver.wait_for_xpath(f'//a[text()="{public_candidate.id}"]')
    first_save_button = driver.wait_for_xpath('//button[text()="Save as source"]')
    first_save_button.click()
    driver.wait_for_xpath(f"//input[@name='{public_group.id}']")
    second_save_button = driver.wait_for_xpath('//button[text()="Save"]')
    second_save_button.click()
    driver.wait_for_xpath('//div[contains(.,"Invalid group_ids field")]')
