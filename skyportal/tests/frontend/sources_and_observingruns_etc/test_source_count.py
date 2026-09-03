import time
import uuid

from playwright.sync_api import expect

from skyportal.tests import api


def test_source_count_widget(page, user, public_group, upload_data_token):
    obj_id_base = str(uuid.uuid4())
    for i in range(2):
        status, data = api(
            "POST",
            "sources",
            data={
                "id": f"{obj_id_base}_{i}",
                "ra": 234.22,
                "dec": -22.33,
                "redshift": 3,
                "transient": False,
                "ra_dis": 2.3,
                "group_ids": [public_group.id],
            },
            token=upload_data_token,
        )
        assert status == 200
        assert data["data"]["id"] == f"{obj_id_base}_{i}"

    page.goto(f"/become_user/{user.id}")
    page.goto("/")

    source_counter = page.locator('//*[@id="sourceCountsWidget"]').first
    expect(source_counter).to_be_visible()
    time.sleep(2)  # wait for the counter to finish. Not a vanilla hardcode!
    source_count_text = source_counter.inner_text()

    # expecting something like: "3\nNew Sources\nLast 7 days"
    assert int(source_count_text.split()[0]) >= 2
