from playwright.sync_api import expect

from skyportal.tests import api


def test_followup_request_frontend(
    public_group_sedm_allocation,
    public_source,
    upload_data_token,
    super_admin_user,
    sedm,
    page,
):
    request_data = {
        "allocation_id": public_group_sedm_allocation.id,
        "obj_id": public_source.id,
        "payload": {
            "priority": 5,
            "start_date": "3010-09-01",
            "end_date": "3012-09-01",
            "observation_type": "IFU",
        },
    }

    status, data = api(
        "POST", "followup_request", data=request_data, token=upload_data_token
    )
    assert status == 200
    assert data["status"] == "success"

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/followup_requests")

    table = page.locator('//*[@data-testid="followup-requests-table"]')
    expect(table.locator('//div[contains(., "IFU")]').first).to_be_visible()
    expect(table.locator('//div[contains(., "5")]').first).to_be_visible()
    expect(table.locator('//div[contains(., "submitted")]').first).to_be_visible()

    page.locator('//input[@name="sourceID"]').fill("not_the_source")

    expect(table.locator('//div[contains(., "IFU")]').first).to_be_hidden()
    expect(table.locator('//div[contains(., "submitted")]').first).to_be_hidden()
