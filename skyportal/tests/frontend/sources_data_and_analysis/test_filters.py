import json
import uuid

import pytest
from playwright.sync_api import expect

from skyportal.tests import api


@pytest.mark.flaky(reruns=2)
def test_add_filter(page, super_admin_user, public_group):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/groups")
    page.get_by_role("tab", name="All Groups").click()
    page.locator(f'//div[@data-id="{public_group.id}"]').first.click()
    page.get_by_role("tab", name="Streams and filters").click()

    filter_name = str(uuid.uuid4())
    page.get_by_role("button", name="add filter").first.click()
    page.locator('//input[@name="filter_name"]').first.fill(filter_name)
    page.locator('//button[@data-testid="add-filter-dialog-submit"]').first.click()
    expect(page.locator(f'//h6[contains(.,"{filter_name}")]').first).to_be_visible()


@pytest.mark.flaky(reruns=2)
def test_rename_filter(page, super_admin_user, public_group, public_filter):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/group/{public_group.id}")
    page.get_by_role("tab", name="Streams and filters").click()

    page.locator(f'//*[@data-testid="rename-filter-{public_filter.id}"]').first.click()
    new_name = str(uuid.uuid4())
    page.locator('//input[@data-testid="filter-name-input"]').first.fill(new_name)
    page.locator('//*[@data-testid="save-filter-name-button"]').first.click()
    expect(page.locator(f'//span[contains(.,"{new_name}")]')).to_have_count(1)


def _fake_boom(page, broker_id, filter_id, stream_name):
    """Serve the BOOM-backed endpoints from the browser, recording saved versions."""
    state = {"posted": None}
    base = f"**/api/brokers/{broker_id}"

    def respond(route, data):
        route.fulfill(json={"status": "success", "data": data})

    def filter_version(route):
        if route.request.method == "POST":
            state["posted"] = route.request.post_data_json
            return respond(route, {"id": filter_id, "fid": "v1"})
        posted = state["posted"]
        respond(
            route,
            {
                "id": filter_id,
                "name": "filter",
                "group_id": None,
                "active": False,
                "active_fid": "v1" if posted else None,
                "fv": [{"fid": "v1", "created_at": "2026-10-05T00:00:00"}]
                if posted
                else [],
                "filters": [{"fid": "v1", "version": posted["filters"]}]
                if posted
                else [],
                "altdata": {},
                "stream": {"name": stream_name},
            },
        )

    page.route(f"{base}/**", lambda route: respond(route, []))
    page.route(f"{base}/filter_modules*", lambda route: respond(route, {}))
    page.route(f"{base}/filters/{filter_id}", filter_version)
    return state


@pytest.mark.flaky(reruns=2)
def test_save_filter_written_in_mongodb(
    page, super_admin_user, super_admin_token, public_filter
):
    import sqlalchemy as sa

    from skyportal.models import Broker, DBSession, Filter

    status, data = api(
        "POST",
        "brokers",
        data={
            "name": str(uuid.uuid4()),
            "broker_classname": "BOOMBROKER",
            "altdata": {"host": "boom.test", "username": "x", "password": "y"},
        },
        token=super_admin_token,
    )
    assert status == 200
    broker_id = data["data"]["id"]
    try:
        DBSession().execute(
            sa.update(Broker).where(Broker.id == broker_id).values(active=True)
        )
        DBSession().execute(
            sa.update(Filter)
            .where(Filter.id == public_filter.id)
            .values(broker_id=broker_id)
        )
        DBSession().commit()

        state = _fake_boom(page, broker_id, public_filter.id, public_filter.stream.name)
        page.goto(f"/become_user/{super_admin_user.id}")
        page.goto(f"/filter/{public_filter.id}")

        pipeline = [{"$match": {"candidate.drb": {"$gt": 0.9}}}]
        page.get_by_role("button", name="MongoDB", exact=True).click()
        editor = page.locator("textarea:not([aria-hidden])")
        editor.fill("[{")
        expect(page.get_by_text("Invalid JSON")).to_be_visible()
        expect(page.get_by_test_id("tour-filter-save")).to_be_disabled()

        editor.fill(json.dumps(pipeline))
        page.get_by_test_id("tour-filter-save").click()
        page.get_by_role("dialog").get_by_role("button", name="Save").click()

        # The pipeline is sent as is, and kept as the version's editable content.
        expect(page.get_by_role("dialog")).to_have_count(0)
        assert state["posted"]["altdata"] == pipeline
        assert state["posted"]["filters"]["filters"] == pipeline

        # The saved version reopens in the MongoDB editor.
        expect(
            page.get_by_role("button", name="MongoDB", exact=True)
        ).to_have_attribute("aria-pressed", "true")
        expect(editor).to_have_value(json.dumps(pipeline, indent=2))
    finally:
        api("DELETE", f"brokers/{broker_id}", token=super_admin_token)
