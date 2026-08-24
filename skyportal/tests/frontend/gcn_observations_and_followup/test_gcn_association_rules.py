"""Managing association cuts from the GCN events page.

These are science choices -- how close in time a neutrino and a gravitational
wave must be to count as one event -- so they are per user, and the service does
not look for associations at all until somebody sets one.
"""

import pytest
from playwright.sync_api import expect

from skyportal.tests import api


@pytest.mark.flaky(reruns=3)
def test_association_rules_tab(page, super_admin_user, super_admin_token):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/gcn_events")

    page.get_by_role("tab", name="Association rules").click()
    expect(page.get_by_test_id("gcn-association-rules")).to_be_visible()

    page.get_by_label("Within (days)").fill("0.0001")
    page.get_by_role("button", name="Add").click()

    # 0.0001 d shown in the unit that reads: 8.64 s
    expect(page.get_by_text("9 s", exact=False)).to_be_visible()

    status, data = api("GET", "gcn_association_rules", token=super_admin_token)
    assert status == 200, data
    added = [
        rule
        for rule in data["data"]
        if rule["detector_type_1"] == "gravitational-wave"
        and rule["detector_type_2"] == "neutrino"
    ]
    assert added, data["data"]
    assert added[0]["days"] == 0.0001

    # and it can be taken away again
    page.get_by_label(f"delete rule {added[0]['id']}").click()
    status, data = api("GET", "gcn_association_rules", token=super_admin_token)
    assert status == 200, data
    assert not [r for r in data["data"] if r["id"] == added[0]["id"]]
