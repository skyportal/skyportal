"""Managing association cuts from the GCN events page.

These are science choices -- how close in time a neutrino and a gravitational
wave must be to count as one event -- so they are per user, and the service does
not look for associations at all until somebody sets one.
"""

import uuid
from datetime import timedelta

import numpy as np
import pytest
from astropy.time import Time
from playwright.sync_api import expect

from skyportal.tests import api


@pytest.mark.flaky(reruns=3)
def test_association_rules_tab(page, super_admin_user, super_admin_token):
    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/gcn_events")

    page.get_by_role("tab", name="Association rules").click()
    expect(page.get_by_test_id("gcn-association-rules")).to_be_visible()

    # a rule belongs to a group, so one has to be chosen
    page.get_by_label("Group").click()
    page.get_by_role("option").first.click()

    page.get_by_label("Within (days)").fill("0.0001")
    page.get_by_role("button", name="Add").click()

    # wait for the row itself, not just any "9 s" on the page: the API is read
    # straight afterwards and the mutation has to have landed first
    expect(
        page.get_by_role("cell", name="gravitational-wave × neutrino")
    ).to_be_visible()
    # 0.0001 d shown in the unit that reads: 8.64 s
    expect(page.get_by_role("cell", name="9 s")).to_be_visible()

    status, data = api("GET", "gcn_association_rules", token=super_admin_token)
    assert status == 200, data
    added = [
        rule
        for rule in data["data"]
        if rule["detector_type_1"] == "gravitational-wave"
        and rule["detector_type_2"] == "neutrino"
        and rule["days"] == 0.0001
    ]
    assert added, data["data"]

    # and it can be taken away again
    page.get_by_label(f"delete rule {added[0]['id']}").click()
    status, data = api("GET", "gcn_association_rules", token=super_admin_token)
    assert status == 200, data
    assert not [r for r in data["data"] if r["id"] == added[0]["id"]]


@pytest.mark.flaky(reruns=3)
def test_association_rule_tags_from_the_page(page, super_admin_user, super_admin_token):
    """A rule can be narrowed to tagged events, e.g. BNS/NSBH gravitational waves."""
    # a tag has to exist for the picker to offer it
    dateobs = (
        Time.now() - timedelta(seconds=int(np.random.randint(10**4, 10**5)))
    ).datetime.replace(microsecond=0)
    # the picker offers a messenger's own tags, so the event needs a detector
    nickname = f"XL{uuid.uuid4().hex[:6]}"
    status, data = api(
        "POST",
        "mmadetector",
        data={
            "name": nickname,
            "nickname": nickname,
            "type": "gravitational-wave",
            "fixed_location": False,
        },
        token=super_admin_token,
    )
    assert status == 200, data

    status, data = api(
        "POST",
        "gcn_event",
        data={
            "dateobs": dateobs.isoformat(),
            "trigger_id": str(np.random.randint(10**8, 10**9)),
            "skymap": {"ra": 42.0, "dec": 12.0, "error": 1.0},
            "tags": [nickname, "BNS"],
        },
        token=super_admin_token,
    )
    assert status == 200, data

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/gcn_events")
    page.get_by_role("tab", name="Association rules").click()

    # the first column's tag picker; its options are that messenger's own tags
    page.get_by_test_id("association-tags-1").locator("[role=combobox]").click()
    page.get_by_role("option", name="BNS", exact=True).click()
    page.keyboard.press("Escape")

    page.get_by_label("Group").click()
    page.get_by_role("option").first.click()

    page.get_by_label("Within (days)").fill("0.5")
    page.get_by_role("button", name="Add").click()

    # the restriction is visible on the rule it belongs to
    expect(page.get_by_text("gravitational-wave (BNS)", exact=False)).to_be_visible()

    status, data = api("GET", "gcn_association_rules", token=super_admin_token)
    assert status == 200, data
    tagged = [rule for rule in data["data"] if rule["tags_1"] == ["BNS"]]
    assert tagged, data["data"]
    assert tagged[0]["detector_type_1"] == "gravitational-wave"
