"""Smoke tests for the BOOM-backed alerts pages.

These exercise the frontend changes from PR #578 (Migrate Frontend to
BOOM-based endpoints): the rewritten Alerts.jsx search/list page and
the new Alert.jsx detail view. We only assert minimal landmarks — that
the page mounts and shows the survey selector / alert details — so the
tests remain robust to small UI tweaks while still catching regressions
like a route disappearing or a duck/reducer wiring change.

Driven with Playwright (the session-scoped `page` fixture from
skyportal/tests/test_util.py). `expect(...).to_be_visible()` auto-waits and
`locator.click()` auto-scrolls + retries actionability, which handles MUI
dialog backdrops and the detail page's async re-renders without the explicit
stale-element retry loops the old Selenium version needed.
"""

import time

import pytest
from playwright.sync_api import expect

from skyportal.tests import api


def test_alerts_page_loads(page):
    """The /alerts route mounts and renders the survey selector."""
    page.goto("/alerts")
    # AlertsSearchButton routes here; the page should render a survey
    # selector (ZTF / LSST). We look for either label via a broad xpath.
    expect(
        page.locator(
            "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            "'abcdefghijklmnopqrstuvwxyz'),'ztf') or "
            "contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            "'abcdefghijklmnopqrstuvwxyz'),'lsst')]"
        )
        .locator("visible=true")
        .first
    ).to_be_visible()


def test_alerts_page_search_by_object_id(page):
    """The /alerts page accepts an objectId query param and renders without
    a hard crash. We don't require results because BOOM may have no data
    matching arbitrary OIDs at this stage; the assertion is just that the
    page mounted (websocket connected, body present)."""
    page.goto("/alerts?survey=ZTF&objectId=ZTF99zzzzzz")
    expect(page.locator("//body").first).to_be_visible()


@pytest.mark.requires_boom_data
def test_alert_detail_page_loads(page, boom_seed_oid):
    """The Alert.jsx detail page renders for an object that BOOM has data
    for. The component reads its objectId from route.id (Alert.jsx:472);
    we assert the heading or another landmark containing the OID."""
    page.goto(f"/alerts/ZTF/{boom_seed_oid}")
    expect(
        page.locator(f"//*[contains(text(),'{boom_seed_oid}')]")
        .locator("visible=true")
        .first
    ).to_be_visible()


@pytest.mark.requires_boom_data
def test_alerts_search_results_for_seed_oid(page, boom_seed_oid):
    """Run the alerts search with the seed objectId and confirm at least
    one row references it."""
    page.goto(f"/alerts?survey=ZTF&objectId={boom_seed_oid}")
    expect(
        page.locator(f"//*[contains(text(),'{boom_seed_oid}')]")
        .locator("visible=true")
        .first
    ).to_be_visible()


@pytest.mark.requires_boom_data
def test_open_alert_from_table(page, boom_seed_oid):
    """The main navigation flow: open the alerts search page, click the
    alert's objectId link in the results table, and verify the Alert.jsx
    detail page rendered with the SaveAlertButton present. The row link has
    target='_blank', so it opens a new page in the browser context.
    """
    page.goto(f"/alerts?survey=ZTF&objectId={boom_seed_oid}")
    # Row link uses data-testid={objectId} (Alerts.jsx:502). Wait for it to be
    # visible before clicking so the search results have finished rendering.
    row_link = page.locator(f"//*[@data-testid='{boom_seed_oid}']").first
    expect(row_link).to_be_visible(timeout=30000)
    with page.context.expect_page() as new_page_info:
        row_link.click()
    new_page = new_page_info.value
    try:
        # SaveAlertButton has data-testid=saveAlertButton_{alert.id} where
        # alert.id is the objectId.
        expect(
            new_page.locator(
                f"//*[@data-testid='saveAlertButton_{boom_seed_oid}']"
            ).first
        ).to_be_visible(timeout=30000)
    finally:
        new_page.close()


@pytest.mark.requires_boom_data
def test_save_alert_as_source(page, boom_seed_oid, public_group, super_admin_token):
    """Drive the Save-as-Source workflow end-to-end: open the alert
    detail page, click the SaveAlertButton, check a group in the dialog,
    and submit. We verify the *outcome* via the API — confirm a Source
    was created — rather than waiting for a UI notification, because
    the success toast can dismiss before it's caught. `public_group`
    ensures there is at least one selectable group in the dialog.
    """
    page.goto(f"/alerts/ZTF/{boom_seed_oid}")
    # Let the detail page settle before interacting; it re-renders several
    # times as photometry/cutouts load asynchronously. Waiting for the OID
    # landmark lets the initial data-load churn finish (Playwright re-resolves
    # the locator on each action, so no manual stale-element retry is needed).
    expect(
        page.locator(f"//*[contains(text(),'{boom_seed_oid}')]")
        .locator("visible=true")
        .first
    ).to_be_visible(timeout=30000)
    # The detail page re-renders several times as photometry/cutouts load, so a
    # click that lands mid-render can be dropped before the dialog opens. Wait
    # for the button to settle, then retry the click until the dialog appears.
    save_button = page.locator(
        f"//*[@data-testid='saveAlertButton_{boom_seed_oid}']"
    ).first
    expect(save_button).to_be_visible(timeout=30000)
    # Dialog title (SaveAlertButton.jsx:206).
    dialog_title = page.locator(
        "//*[contains(text(),'Select one or more groups')]"
    ).first
    for _ in range(5):
        save_button.click()
        try:
            expect(dialog_title).to_be_visible(timeout=5000)
            break
        except AssertionError:
            continue
    else:
        # Surface a clear failure if the dialog never opened.
        expect(dialog_title).to_be_visible(timeout=5000)
    # Click the group's label text rather than the raw checkbox input: the
    # MUI <input> is visibility:hidden (only the SVG icon shows), so a direct
    # click misses the hit area / fires an event React Hook Form ignores.
    # Clicking the label text triggers the native label→input pairing that
    # RHF's Controller picks up. public_group.name is unique on the page.
    page.locator(f"//*[contains(text(),'{public_group.name}')]").first.click()
    # Submit button has name=finalSaveAlertButton{alert.id}.
    page.locator(f"//button[@name='finalSaveAlertButton{boom_seed_oid}']").first.click()

    # Poll the API for the Source. The full chain we're verifying is:
    # dialog submit → boom_alert.saveAlertAsSource duck → backend
    # POST /api/boom/surveys/ZTF/objects/{oid} (BoomObjectHandler.post)
    # → Obj + Source created.
    deadline = time.time() + 30
    last_status = None
    while time.time() < deadline:
        last_status, data = api(
            "GET", f"sources/{boom_seed_oid}", token=super_admin_token
        )
        if last_status == 200 and data.get("status") == "success":
            assert data["data"]["id"] == boom_seed_oid
            return
        time.sleep(1)
    pytest.fail(
        f"Source {boom_seed_oid} never appeared after submit "
        f"(last GET /sources status={last_status})"
    )
