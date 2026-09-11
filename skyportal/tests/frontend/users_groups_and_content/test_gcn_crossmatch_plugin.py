"""Turning a filter's GCN crossmatch on from the filter page.

Until this panel existed, `altdata.gcn_crossmatch` could only be set through the
API, so every crossmatch in production was configured by hand.
"""

import pytest
from playwright.sync_api import expect

from skyportal.tests import api


@pytest.mark.flaky(reruns=3)
def test_enable_gcn_crossmatch_from_the_filter_page(
    page, super_admin_user, super_admin_token, public_filter
):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto(f"/filter/{public_filter.id}")

    page.get_by_text("GCN crossmatch").click()

    toggle = page.get_by_label("enable gcn crossmatch")
    expect(toggle).not_to_be_checked()
    toggle.check()

    page.get_by_label("Only events tagged (comma separated)").fill("Einstein Probe")
    page.get_by_label("Days after").fill("7")
    page.get_by_role("button", name="Save").click()

    expect(page.get_by_text("Saved")).to_be_visible()

    # the panel writes through to the filter the service actually reads
    status, data = api("GET", f"filters/{public_filter.id}", token=super_admin_token)
    assert status == 200, data
    config = data["data"]["altdata"]["gcn_crossmatch"]
    assert config["enabled"] is True, config
    assert config["delta_t_after"] == 7, config
    assert config["filters"] == {"gcn_tags": ["Einstein Probe"]}, config
