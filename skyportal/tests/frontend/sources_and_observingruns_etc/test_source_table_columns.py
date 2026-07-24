import uuid

import pytest
from playwright.sync_api import expect

from skyportal.handlers.api.internal.altdata_info import cache as altdata_info_cache
from skyportal.handlers.api.internal.annotations_info import (
    cache as annotations_info_cache,
)
from skyportal.tests import api


def _reveal_column(page, search_text):
    """Open the DataGrid columns panel and toggle on the matching hidden column."""
    page.locator("[data-testid='datagrid-columns-button']").first.click()
    panel = page.locator(".MuiDataGrid-panel")
    panel.locator("input[type='search']").first.fill(search_text)
    # After filtering, the matching column's toggle is the only checkbox shown.
    panel.locator("input[type='checkbox']").last.check()
    page.keyboard.press("Escape")


@pytest.mark.flaky(reruns=2)
def test_source_table_annotation_and_altdata_columns(
    page,
    super_admin_user,
    super_admin_token,
    public_group,
    annotation_token,
):
    prefix = f"coltest{uuid.uuid4().hex[:8]}"
    obj_id1 = f"{prefix}_a"
    obj_id2 = f"{prefix}_b"
    origin = f"o{uuid.uuid4().hex[:8]}"
    ann_key = "tE"
    alt_key = f"ak{uuid.uuid4().hex[:8]}"
    # Distinctive values so the assertions can't match unrelated cells.
    ann_values = {obj_id1: 987654, obj_id2: 876543}
    alt_values = {obj_id1: 111333, obj_id2: 222444}

    for oid in (obj_id1, obj_id2):
        status, data = api(
            "POST",
            "sources",
            data={
                "id": oid,
                "ra": 210.0,
                "dec": -22.33,
                "group_ids": [public_group.id],
                "altdata": {alt_key: alt_values[oid]},
            },
            token=super_admin_token,
        )
        assert status == 200, data
        status, data = api(
            "POST",
            f"sources/{oid}/annotations",
            data={"origin": origin, "data": {ann_key: ann_values[oid]}},
            token=annotation_token,
        )
        assert status == 200, data

    # Clear the info caches so the new origin/key and altdata key are offered.
    del altdata_info_cache["altdata_info"]
    del annotations_info_cache[f"annotations_info_{super_admin_user.id}"]

    page.goto(f"/become_user/{super_admin_user.id}")
    assert "localhost" in page.url
    page.goto("/sources")

    # Filter to our two sources by shared id prefix.
    page.locator("//button[@data-testid='Filter Table-iconButton']").first.click()
    page.locator("//input[@name='sourceID']").first.fill(prefix)
    page.locator("//button[text()='Submit']").first.click()
    expect(
        page.locator(f"//a[contains(@href, '/source/{obj_id2}')]").first
    ).to_be_visible()

    # Annotation column: hidden by default, then revealed and showing its value.
    expect(
        page.locator(f"//*[text()[contains(., '{ann_values[obj_id1]}')]]")
    ).to_have_count(0)
    _reveal_column(page, origin)
    expect(
        page.locator(f"//*[text()[contains(., '{ann_values[obj_id1]}')]]").first
    ).to_be_visible()

    # Altdata column: same flow.
    _reveal_column(page, alt_key)
    expect(
        page.locator(f"//*[text()[contains(., '{alt_values[obj_id1]}')]]").first
    ).to_be_visible()
