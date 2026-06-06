import uuid

import pytest
from playwright.sync_api import expect


@pytest.mark.flaky(reruns=2)
def test_analysis_service_frontend(
    super_admin_token, super_admin_user, analysis_service_token, view_only_user, page
):
    page.goto(f"/become_user/{super_admin_user.id}")

    # go to the analysis services page
    page.goto("/services")

    # add dropdown analysis
    analysis_name = str(uuid.uuid4())
    display_name = str(uuid.uuid4())

    page.locator('//button[@name="new_analysis_service"]').first.click()

    page.locator('//*[@id="root_name"]').first.fill(analysis_name)
    page.locator('//*[@id="root_display_name"]').first.fill(display_name)
    page.locator('//*[@id="root_url"]').first.fill(
        f"http://localhost:5000/analysis/{analysis_name}"
    )

    # Playwright auto-scrolls and retries actionability, so a single click is
    # enough (no manual scrollIntoView / sleep-retry loop needed).
    page.locator('//button[@type="submit"]').first.click()

    # The services DataGrid paginates (10/page) and accumulates rows across the
    # suite, so filter to the new service via the grid quick-filter before
    # asserting (otherwise it lands on a later page and isn't rendered).
    def _expect_service_visible():
        # The services grid loads/re-renders asynchronously and discards the
        # quick-filter value if it's set mid-load, so re-apply the filter until
        # the matching row shows (rather than filtering once and hoping the grid
        # was ready).
        grid = page.locator(".MuiDataGrid-root")
        search = grid.get_by_placeholder("Search…").first
        cell = page.locator(
            f'//*[@role="gridcell"][contains(.,"{display_name}")]'
        ).first
        for _ in range(8):
            search.fill(display_name)
            try:
                expect(cell).to_be_visible(timeout=5000)
                return
            except AssertionError:
                page.wait_for_timeout(1000)
        expect(cell).to_be_visible(timeout=5000)

    _expect_service_visible()

    # check for user who can only view
    page.goto(f"/become_user/{view_only_user.id}")
    page.goto("/services")
    _expect_service_visible()

    # confirm that no submission without permission
    expect(page.locator('//button[@name="new_analysis_service"]')).to_have_count(0)
