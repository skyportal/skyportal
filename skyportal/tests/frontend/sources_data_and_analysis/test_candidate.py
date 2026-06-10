import datetime
import uuid

from playwright.sync_api import expect

from skyportal.tests import api

from ....utils.naive_datetime import utcnow_naive


def test_candidate_date_filtering(
    page,
    user,
    public_filter2,
    public_group2,
    upload_data_token,
    super_admin_token,
    ztf_camera,
):
    now_utc = utcnow_naive()
    now = datetime.datetime.now()

    status, data = api(
        "POST",
        f"groups/{public_group2.id}/users",
        data={"userID": user.id, "admin": False},
        token=super_admin_token,
    )
    assert status == 200

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
                "filter_ids": [public_filter2.id],
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
                "group_ids": [public_group2.id],
            },
            token=upload_data_token,
        )
        assert status == 200

    page.goto(f"/become_user/{user.id}")
    page.goto("/candidates")
    page.locator(
        f'//*[@data-testid="filteringFormGroupCheckbox-{public_group2.id}"]'
    ).first.click()
    start_date_input = page.locator(
        '//label[text()="Start (Local Time)"]/../div/input'
    ).first
    end_date_input = page.locator(
        "//label[text()='End (Local Time)']/../div/input"
    ).first

    minus_2 = now - datetime.timedelta(minutes=2)
    minus_1 = now - datetime.timedelta(minutes=1)
    plus_1 = now + datetime.timedelta(minutes=1)

    # Scan between [now - 2 minutes] and [now - 1 minute]
    start_date_input.click(position={"x": 8, "y": 10})
    start_date_input.press_sequentially(minus_2.strftime("%m%d%Y%I%M%p"))
    end_date_input.click(position={"x": 8, "y": 10})
    end_date_input.press_sequentially(minus_1.strftime("%m%d%Y%I%M%p"))
    page.locator('//button[text()="Search"]').first.click()
    expect(page.locator('//*[contains(., "Found 0 candidates")]').first).to_be_visible()

    # Scan between [now] and [now + 1 minute]
    start_date_input.click(position={"x": 8, "y": 10})
    start_date_input.press_sequentially(now.strftime("%m%d%Y%I%M%p"))
    end_date_input.click(position={"x": 8, "y": 10})
    end_date_input.press_sequentially(plus_1.strftime("%m%d%Y%I%M%p"))
    page.locator('//button[text()="Search"]').first.click()
    expect(page.locator('//*[contains(., "Found 0 candidates")]').first).to_be_hidden()
    expect(page.locator('//*[contains(., "Found 5 candidates")]').first).to_be_visible()
