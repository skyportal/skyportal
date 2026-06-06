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

    # check for analysis service
    expect(
        page.locator(f'//*[@role="gridcell"][contains(.,"{display_name}")]').first
    ).to_be_visible(timeout=20000)

    # check for user who can only view
    page.goto(f"/become_user/{view_only_user.id}")
    page.goto("/services")
    expect(
        page.locator(f'//*[@role="gridcell"][contains(.,"{display_name}")]').first
    ).to_be_visible(timeout=20000)

    # confirm that no submission without permission
    expect(page.locator('//button[@name="new_analysis_service"]')).to_have_count(0)
