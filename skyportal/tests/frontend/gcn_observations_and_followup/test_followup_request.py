import datetime

import pytest
from playwright.sync_api import expect

from skyportal.tests import api


# NOTE: porting this test against the rewritten followup-requests page uncovered
# a real backend bug (fixed in handlers/api/followup_request.py): the
# instrumentID/allocationID query args were compared to integer columns without
# casting, so the instrument-filtered list query 500'd ("operator does not exist:
# integer = character varying"). The page filters by instrument, so we explicitly
# select the SEDM instrument before submitting the filter.
@pytest.mark.flaky(reruns=2)
def test_followup_request_frontend(
    public_group_sedm_allocation,
    public_source,
    upload_data_token,
    super_admin_user,
    sedm,
    page,
):
    # The followup-requests list filters by a "requested date" window that
    # defaults to roughly [now-1d, now+1d], so post the request with a start
    # date inside that window (otherwise it never appears in the table).
    now = datetime.datetime.utcnow()
    request_data = {
        "allocation_id": public_group_sedm_allocation.id,
        "obj_id": public_source.id,
        "payload": {
            "priority": 5,
            "start_date": now.strftime("%Y-%m-%dT%H:%M:%S"),
            "end_date": (now + datetime.timedelta(days=2)).strftime(
                "%Y-%m-%dT%H:%M:%S"
            ),
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

    # Scope the filter form: the requests list (with per-row type="submit"
    # buttons) renders before it, so an unscoped submit would hit a row button.
    selection_form = page.locator(
        '//div[@data-testid="followup-request-selection-form"]'
    )
    # The form filters by instrument and defaults to the *first* instrument, so
    # explicitly pick SEDM (the allocation our request was posted to) -- otherwise
    # the list comes back filtered to some other instrument and is empty.
    instrument_select = selection_form.locator('//*[@id="root_instrumentID"]').first
    instrument_select.click()
    # option label is "<telescope> / <instrument>", so match on full text (".").
    # Wait for the option to render, click it, and wait for the menu to close so
    # the selection registers before we submit (otherwise the default instrument
    # is used and the SEDM request never appears).
    sedm_option = page.locator(
        f'//li[@role="option"][contains(., "{sedm.name}")]'
    ).first
    expect(sedm_option).to_be_visible()
    sedm_option.click()
    expect(page.locator('//ul[@role="listbox"]')).to_have_count(0)
    selection_form.locator('//button[@type="submit"]').first.click()

    page.locator(f"//*[@data-testid='{sedm.name}-requests-header']").first.click()
    expect(
        page.locator(
            f'//div[contains(@data-testid, "{sedm.name}_followupRequestsTable")]//div[contains(., "IFU")]'
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            f'//div[contains(@data-testid, "{sedm.name}_followupRequestsTable")]//div[contains(., "5")]'
        ).first
    ).to_be_visible()
    expect(
        page.locator(
            f'//div[contains(@data-testid, "{sedm.name}_followupRequestsTable")]//div[contains(., "submitted")]'
        ).first
    ).to_be_visible()

    selection_form.locator('//*[@id="root_sourceID"]').first.fill("not_the_source")
    selection_form.locator('//button[@type="submit"]').first.click()

    expect(
        page.locator(
            f'//div[contains(@data-testid, "{sedm.name}_followupRequestsTable")]//div[contains(., "IFU")]'
        ).first
    ).to_be_hidden()
    expect(
        page.locator(
            f'//div[contains(@data-testid, "{sedm.name}_followupRequestsTable")]//div[contains(., "submitted")]'
        ).first
    ).to_be_hidden()
