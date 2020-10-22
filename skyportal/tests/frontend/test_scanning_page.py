import uuid
import pytest
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains

from skyportal.tests import api


def test_candidates_page_render(driver, user, public_candidate):
    driver.get(f"/become_user/{user.id}")
    driver.get("/candidates")
    driver.wait_for_xpath(f'//a[text()="{public_candidate.id}"]')


@pytest.mark.flaky(reruns=2)
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
        data={"name": str(uuid.uuid4()), "group_admins": [user.id]},
        token=manage_groups_token,
    )
    assert status == 200

    driver.get(f"/become_user/{user.id}")
    driver.get("/candidates")
    for i in range(5):
        driver.wait_for_xpath(f'//a[text()="{candidate_id}_{i}"]')
    group_checkbox = driver.wait_for_xpath(f'//input[starts-with(@name,"groupIDs[0]")]')
    driver.scroll_to_element_and_click(group_checkbox)
    submit_button = driver.wait_for_xpath('//span[text()="Search"]')
    driver.scroll_to_element_and_click(submit_button)
    for i in range(5):
        driver.wait_for_xpath_to_disappear(f'//a[text()="{candidate_id}_{i}"]')
    driver.scroll_to_element_and_click(group_checkbox)
    driver.scroll_to_element_and_click(submit_button)
    for i in range(5):
        driver.wait_for_xpath(f'//a[text()="{candidate_id}_{i}"]')


@pytest.mark.flaky(reruns=2)
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
    submit_button = driver.wait_for_xpath('//span[text()="Search"]')
    driver.scroll_to_element_and_click(submit_button)
    for i in range(5):
        driver.wait_for_xpath_to_disappear(f'//a[text()="{candidate_id}_{i}"]')
    driver.scroll_to_element_and_click(unsaved_only_checkbox)
    driver.scroll_to_element_and_click(submit_button)
    for i in range(5):
        driver.wait_for_xpath(f'//a[text()="{candidate_id}_{i}"]')


@pytest.mark.flaky(reruns=2)
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
    start_date_input.send_keys("200012120000")
    end_date_input = driver.wait_for_xpath("//input[@name='endDate']")
    end_date_input.clear()
    end_date_input.send_keys("200112120000")
    submit_button = driver.wait_for_xpath_to_be_clickable('//span[text()="Search"]')
    driver.scroll_to_element_and_click(submit_button)
    for i in range(5):
        driver.wait_for_xpath_to_disappear(f'//a[text()="{candidate_id}_{i}"]', 10)
    end_date_input.clear()
    end_date_input.send_keys("209012120000")
    submit_button = driver.wait_for_xpath_to_be_clickable('//span[text()="Search"]')
    driver.scroll_to_element_and_click(submit_button)
    for i in range(5):
        driver.wait_for_xpath(f'//a[text()="{candidate_id}_{i}"]', 10)


@pytest.mark.flaky(reruns=2)
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
    try:
        driver.wait_for_xpath_to_disappear(
            f'//button[@name="initialSaveCandidateButton{public_candidate.id}"]'
        )
        driver.wait_for_xpath('//span[text()="Previously Saved"]')
    except TimeoutException:
        driver.refresh()
        driver.wait_for_xpath_to_disappear(
            f'//button[@name="initialSaveCandidateButton{public_candidate.id}"]'
        )
        driver.wait_for_xpath('//span[text()="Previously Saved"]')


@pytest.mark.flaky(reruns=2)
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

    assert driver.wait_for_xpath("//input[@name='group_ids[0]']").is_selected()
    second_save_button = driver.wait_for_xpath(
        f'//button[@name="finalSaveCandidateButton{public_candidate.id}"]'
    )
    second_save_button.click()
    try:
        driver.wait_for_xpath_to_disappear(
            f'//button[@name="initialSaveCandidateButton{public_candidate.id}"]'
        )
        driver.wait_for_xpath('//span[text()="Previously Saved"]')
    except TimeoutException:
        driver.refresh()
        driver.wait_for_xpath_to_disappear(
            f'//button[@name="initialSaveCandidateButton{public_candidate.id}"]'
        )
        driver.wait_for_xpath('//span[text()="Previously Saved"]')


@pytest.mark.flaky(reruns=2)
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

    group_checkbox = driver.wait_for_xpath("//input[@name='group_ids[0]']")
    assert group_checkbox.is_selected()
    group_checkbox.click()
    assert not group_checkbox.is_selected()
    second_save_button = driver.wait_for_xpath_to_be_clickable(
        f'//button[@name="finalSaveCandidateButton{public_candidate.id}"]'
    )
    second_save_button.click()
    driver.wait_for_xpath('//div[contains(.,"Select at least one group")]')


@pytest.mark.flaky(reruns=2)
def test_submit_annotations_sorting(
    driver,
    view_only_user,
    public_group,
    public_candidate,
    public_candidate2,
    annotation_token,
):
    origin = str(uuid.uuid4())
    status, data = api(
        "POST",
        "annotation",
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
        "annotation",
        data={
            "obj_id": public_candidate2.id,
            "origin": origin,
            "data": {"numeric_field": 2},
        },
        token=annotation_token,
    )
    assert status == 200

    driver.get(f"/become_user/{view_only_user.id}")
    driver.get("/candidates")
    driver.wait_for_xpath(f'//a[text()="{public_candidate.id}"]')

    driver.click_xpath(f"//p[text()='numeric_field: 1.0000']")
    # Check to see that selected annotation appears in info column
    driver.wait_for_xpath(
        f'//td[contains(@data-testid, "MuiDataTableBodyCell")][.//span[text()=1.0000]]'
    )

    # Check to see that sorting button has become enabled, and click
    driver.wait_for_xpath_to_be_clickable(
        "//button[@data-testid='sortOnAnnotationButton']"
    )
    driver.click_xpath("//button[@data-testid='sortOnAnnotationButton']")

    # Check that results come back as expected
    # Col 1, Row 0 should be the first candidate's info (MuiDataTableBodyCell-1-0)
    driver.wait_for_xpath(
        f'//td[contains(@data-testid, "MuiDataTableBodyCell-1-0")][.//span[text()="1.0000"]]'
    )
    # Col 1, Row 1 should be the second candidate's info (MuiDataTableBodyCell-1-1)
    driver.wait_for_xpath(
        f'//td[contains(@data-testid, "MuiDataTableBodyCell-1-1")][.//span[text()="2.0000"]]'
    )


@pytest.mark.flaky(reruns=2)
def test_submit_annotations_filtering(
    driver,
    view_only_user,
    public_group,
    public_candidate,
    public_candidate2,
    annotation_token,
):
    origin = str(uuid.uuid4())
    status, data = api(
        "POST",
        "annotation",
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
        "annotation",
        data={
            "obj_id": public_candidate2.id,
            "origin": origin,
            "data": {"numeric_field": 2},
        },
        token=annotation_token,
    )
    assert status == 200

    driver.get(f"/become_user/{view_only_user.id}")
    driver.get("/candidates")
    driver.wait_for_xpath(f'//a[text()="{public_candidate.id}"]')

    driver.click_xpath("//button[@data-testid='Filter Table-iconButton']")
    # Filter by numeric_field < 1.5
    driver.click_xpath("//div[@id='root_origin']")
    driver.click_xpath(f'//li[@data-value="{origin}"]')
    key_select = driver.wait_for_xpath("//div[@id='root_key']")
    ActionChains(driver).move_to_element(key_select).pause(0.1).click().perform()
    driver.click_xpath("//li[@data-value='numeric_field']")
    min_box = driver.wait_for_xpath("//input[@id='root_min']")
    min_text = "0"
    min_box.send_keys(min_text)
    max_box = driver.wait_for_xpath("//input[@id='root_max']")
    max_text = "1.5"
    max_box.send_keys(max_text)
    driver.click_xpath("//span[text()='Submit']")

    # Check that results come back as expected
    # The first candidate should exist
    driver.wait_for_xpath(f'//a[text()="{public_candidate.id}"]')
    # The second candidate should not exist
    driver.wait_for_xpath_to_disappear(f'//a[text()="{public_candidate2.id}"]')
