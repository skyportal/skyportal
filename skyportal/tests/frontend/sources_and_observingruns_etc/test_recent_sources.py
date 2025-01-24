import datetime
import uuid

import pytest
from selenium.common.exceptions import TimeoutException

from skyportal.tests import api


@pytest.mark.flaky(reruns=2)
def test_recent_sources(driver, user, public_group, upload_data_token):
    obj_id = str(uuid.uuid4())
    ra = 50.1
    redshift = 2.5
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": ra,
            "dec": 22.33,
            "redshift": redshift,
            "altdata": {"simbad": {"class": "RRLyr"}},
            "transient": False,
            "ra_dis": 2.3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id

    driver.get(f"/become_user/{user.id}")
    driver.get("/")

    # Wait for just added source to show up in added sources
    recent_source_dataid = "recentSourceItem"
    driver.wait_for_xpath(
        f'//div[starts-with(@data-testid, "{recent_source_dataid}")][.//span[text()="a few seconds ago"]][.//span[contains(text(), "{obj_id}")]]'
    )


@pytest.mark.flaky(reruns=2)
def test_hidden_recent_source(driver, user_no_groups, public_group, upload_data_token):
    obj_id = str(uuid.uuid4())
    ra = 50.1
    redshift = 2.5
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": ra,
            "dec": 22.33,
            "redshift": redshift,
            "altdata": {"simbad": {"class": "RRLyr"}},
            "transient": False,
            "ra_dis": 2.3,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id

    driver.get(f"/become_user/{user_no_groups.id}")
    driver.get("/")

    # Make sure just added source doesn't show up
    with pytest.raises(TimeoutException):
        recent_source_class = "makeStyles-recentSourceItemWithButton"
        driver.wait_for_xpath(
            f'//div[starts-with(@class, "{recent_source_class}")][.//span[text()="a few seconds ago"]][.//span[contains(text(), "{obj_id}")]]'
        )


def test_recently_saved_candidate(
    driver, user, public_group, public_filter, upload_data_token
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
            "passed_at": str(datetime.datetime.utcnow()),
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

    driver.get(f"/become_user/{user.id}")
    driver.get("/")
    driver.wait_for_xpath(
        f'//div[starts-with(@data-testid, "recentSourceItem")][.//span[text()="a few seconds ago"]][.//span[contains(text(), "{obj_id}")]]'
    )
