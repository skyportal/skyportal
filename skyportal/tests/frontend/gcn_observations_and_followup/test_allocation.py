import uuid

import pytest
from playwright.sync_api import expect

from skyportal.tests import api


def one_request_comment_process(
    page, request_comment_xpath, actual_comment, comment_to_put
):
    """Test that one comment, updated on one request, is displayed correctly."""
    # Open the comment editor for this request
    page.locator(request_comment_xpath + "//span").first.click()
    # The pop-up textarea should hold the current comment
    popup_textarea = page.locator(
        '//div[@data-testid="updateCommentTextfield"]//textarea'
    ).first
    expect(popup_textarea).to_have_value(actual_comment)
    # Enter the new comment text (fill replaces, covering clear + send_keys)
    popup_textarea.fill(comment_to_put)
    page.locator('//button[@data-testid="updateCommentSubmitButton"]').first.click()

    expect(
        page.locator('//div[@data-testid="updateCommentTextfield"]').first
    ).to_be_hidden()

    expect(page.locator(request_comment_xpath).first).to_have_text(comment_to_put)


@pytest.mark.flaky(reruns=2)
def test_allocation_comment_display(
    page, super_admin_user, public_group, public_source, super_admin_token, sedm
):
    # Create an allocation
    request_data = {
        "group_id": public_group.id,
        "instrument_id": sedm.id,
        "pi": "Shri Kulkarni",
        "hours_allocated": 200,
        "validity_ranges": [
            {
                "start_date": "2021-02-27T00:00:00.000Z",
                "end_date": "3021-07-20T00:00:00.000Z",
            }
        ],
        "proposal_id": "COO-2020A-P01",
    }
    status, data = api("POST", "allocation", data=request_data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    allocation_id = data["data"]["id"]

    request_data = {
        "allocation_id": allocation_id,
        "obj_id": public_source.id,
        "payload": {
            "priority": 5,
            "start_date": "3010-09-01",
            "end_date": "3012-09-01",
            "observation_type": "IFU",
            "exposure_time": 300,
            "maximum_airmass": 2,
            "maximum_fwhm": 1.2,
        },
    }
    status, data = api(
        "POST", "followup_request", data=request_data, token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"

    request_data = {
        "allocation_id": allocation_id,
        "obj_id": public_source.id,
        "payload": {
            "priority": 5,
            "start_date": "3010-09-01",
            "end_date": "3012-09-01",
            "observation_type": "IFU",
            "exposure_time": 200,
            "maximum_airmass": 1,
            "maximum_fwhm": 1.3,
        },
    }
    status, data = api(
        "POST", "followup_request", data=request_data, token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/allocation/{allocation_id}")

    request1_comment_xpath = (
        '//div[@data-rowindex="0"]//span[@aria-label="Update comment"]/..'
    )
    request2_comment_xpath = (
        '//div[@data-rowindex="1"]//span[@aria-label="Update comment"]/..'
    )
    expect(page.locator(request1_comment_xpath).first).to_have_text("")
    expect(page.locator(request2_comment_xpath).first).to_have_text("")

    one_request_comment_process(page, request1_comment_xpath, "", "comment number 1")
    one_request_comment_process(page, request2_comment_xpath, "", "comment number 2")
    one_request_comment_process(page, request1_comment_xpath, "comment number 1", "")

    page.goto(f"/allocation/{allocation_id}")
    expect(page.locator(request1_comment_xpath).first).to_have_text("")
    expect(page.locator(request2_comment_xpath).first).to_have_text("comment number 2")


@pytest.mark.flaky(reruns=3)
def test_super_user_post_allocation(
    public_group, super_admin_token, super_admin_user, page
):
    telescope_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "telescope",
        data={
            "name": telescope_name,
            "nickname": telescope_name,
            "lat": 0.0,
            "lon": 0.0,
            "elevation": 0.0,
            "diameter": 10.0,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    telescope_id = data["data"]["id"]

    instrument_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "instrument",
        data={
            "name": instrument_name,
            "type": "imager",
            "band": "NIR",
            "filters": ["f110w"],
            "telescope_id": telescope_id,
            "api_classname": "ZTFAPI",
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    instrument_id = data["data"]["id"]

    instrument_name2 = str(uuid.uuid4())
    status, data = api(
        "POST",
        "instrument",
        data={
            "name": instrument_name2,
            "type": "imager",
            "band": "NIR",
            "filters": ["f110w"],
            "telescope_id": telescope_id,
            "api_classname": "ZTFAPI",
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    request_data = {
        "group_id": public_group.id,
        "instrument_id": instrument_id,
        "pi": "Shri Kulkarni",
        "hours_allocated": 200,
        "validity_ranges": [
            {
                "start_date": "2021-02-27T00:00:00.000Z",
                "end_date": "3021-07-20T00:00:00.000Z",
            }
        ],
        "proposal_id": "COO-2020A-P01",
    }

    status, data = api("POST", "allocation", data=request_data, token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    id = data["data"]["id"]

    status, data = api("GET", f"allocation/{id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/allocations")

    # The allocation grid is a (virtualized) show-all DataGrid; filter to the
    # instrument so its row is rendered before asserting.
    search = page.locator(".MuiDataGrid-root").get_by_placeholder("Search…").first
    search.fill(instrument_name)
    expect(
        page.locator(f'//*[contains(text(),"{instrument_name}")]').first
    ).to_be_visible()

    # Create a second allocation via the New Allocation dialog form.
    page.locator('//*[@name="new_allocation"]').first.click()
    dialog = page.locator('//div[@role="dialog"]')
    dialog.locator('//*[@id="root_group_id"]').first.click()
    page.locator('//li[contains(text(), "Sitewide Group")]').first.click()
    dialog.locator('//*[@id="root_pi"]').first.fill("Shri")
    dialog.locator('//*[@id="root_hours_allocated"]').first.fill("100")
    dialog.locator('//*[@id="root_instrument_id"]').first.click()
    page.locator(f'//li[contains(text(), "{instrument_name2}")]').first.click()

    dialog.locator('//button[@type="submit"]').first.click()
    expect(page.locator('//div[@role="dialog"]')).to_have_count(0)

    # ``fill`` replaces the field contents; filtering to the new instrument.
    search.fill(instrument_name2)
    expect(
        page.locator(f'//*[contains(text(),"{instrument_name2}")]').first
    ).to_be_visible()
