import uuid

import pytest
from playwright.sync_api import expect

from skyportal.tests import api

from ....utils.naive_datetime import utcnow_naive


@pytest.mark.flaky(reruns=2)
def test_recent_sources(page, user, public_group, upload_data_token):
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 50.1,
            "dec": 22.33,
            "redshift": 2.5,
            "altdata": {"simbad": {"class": "RRLyr"}},
            "transient": False,
            "ra_dis": 2.3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id

    page.goto(f"/become_user/{user.id}")
    page.goto("/")

    expect(
        page.locator(
            f'//div[starts-with(@data-testid, "recentSourceItem")][.//span[contains(text(), "few seconds")]][.//span[contains(text(), "{obj_id}")]]'
        ).first
    ).to_be_visible()


@pytest.mark.flaky(reruns=2)
def test_hidden_recent_source(page, user_no_groups, public_group, upload_data_token):
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 50.1,
            "dec": 22.33,
            "redshift": 2.5,
            "altdata": {"simbad": {"class": "RRLyr"}},
            "transient": False,
            "ra_dis": 2.3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id

    page.goto(f"/become_user/{user_no_groups.id}")
    page.goto("/")

    # Give the widget time to render, then confirm the source never shows up.
    page.wait_for_timeout(3000)
    expect(
        page.locator(
            f'//div[starts-with(@class, "makeStyles-recentSourceItemWithButton")][.//span[contains(text(), "few seconds")]][.//span[contains(text(), "{obj_id}")]]'
        )
    ).to_have_count(0)


def test_recently_saved_candidate(
    page, user, public_group, public_filter, upload_data_token
):
    obj_id = str(uuid.uuid4())

    status, data = api(
        "POST",
        "candidates",
        data={
            "id": obj_id,
            "ra": 50.1,
            "dec": 22.33,
            "redshift": 2.5,
            "altdata": {"simbad": {"class": "RRLyr"}},
            "transient": False,
            "ra_dis": 2.3,
            "filter_ids": [public_filter.id],
            "passed_at": str(utcnow_naive()),
        },
        token=upload_data_token,
    )
    assert status == 200

    status, data = api(
        "POST",
        "sources",
        data={"id": obj_id, "group_ids": [public_group.id]},
        token=upload_data_token,
    )
    assert status == 200

    page.goto(f"/become_user/{user.id}")
    page.goto("/")
    expect(
        page.locator(
            f'//div[starts-with(@data-testid, "recentSourceItem")][.//span[contains(text(), "few seconds")]][.//span[contains(text(), "{obj_id}")]]'
        ).first
    ).to_be_visible()
