import datetime
import uuid

import pytest
from playwright.sync_api import expect

from skyportal.tests import api

from ....utils.naive_datetime import utcnow_naive


# Passes in isolation; only times out under full-suite contention, so retry.
@pytest.mark.flaky(reruns=2)
def test_candidate_date_filtering(
    page,
    user,
    public_candidate,
    public_filter,
    public_group,
    upload_data_token,
    ztf_camera,
):
    now_utc = utcnow_naive()
    now = datetime.datetime.now()

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
                "passed_at": str(now_utc),
            },
            token=upload_data_token,
        )
        assert status == 200

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

    page.goto(f"/become_user/{user.id}")
    page.goto("/candidates")
    page.locator(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group.id}"]'
    ).first.click()

    def _type_date(locator, when):
        s = when.strftime("%Y %m %d %I %M %p")
        locator.click()
        locator.fill("")
        for part in (s[5:7], s[8:10], s[0:4], s[11:13], s[14:16], s[17]):
            locator.press_sequentially(part)

    start_date_input = page.locator(
        '//label[text()="Start (Local Time)"]/../div/input'
    ).first
    _type_date(start_date_input, now - datetime.timedelta(minutes=2))

    end_date_input = page.locator(
        "//label[text()='End (Local Time)']/../div/input"
    ).first
    _type_date(end_date_input, now - datetime.timedelta(minutes=1))

    page.locator('//button[text()="Search"]').first.click()
    for i in range(5):
        expect(
            page.locator(f'//a[@data-testid="{candidate_id}_{i}"]').first
        ).to_be_hidden()

    expect(page.locator('//*[contains(., "Found 0 candidates")]').first).to_be_visible()

    _type_date(end_date_input, now + datetime.timedelta(minutes=1))

    page.locator('//button[text()="Search"]').first.click()

    expect(page.locator('//*[contains(., "Found 0 candidates")]').first).to_be_hidden()
    expect(page.locator('//*[contains(., "Found 5 candidates")]').first).to_be_visible()
