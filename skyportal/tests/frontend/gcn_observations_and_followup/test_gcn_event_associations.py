"""Ruling on associated events from a GCN event page.

Mirrors the source page: the verdict buttons select, SAVE commits, so one click
is never a permanent ruling.
"""

import uuid
from datetime import timedelta

import numpy as np
import pytest
from astropy.time import Time
from playwright.sync_api import expect

from skyportal.tests import api


def _post_event(token, dateobs, ra, dec, tag):
    status, data = api(
        "POST",
        "gcn_event",
        data={
            "dateobs": dateobs.isoformat(),
            "trigger_id": str(np.random.randint(10**8, 10**9)),
            "skymap": {"ra": ra, "dec": dec, "error": 1.0},
            "tags": [tag],
        },
        token=token,
    )
    assert status == 200, data


@pytest.mark.flaky(reruns=3)
def test_vet_an_associated_event(page, super_admin_user, super_admin_token):
    from baselayer.app import models
    from skyportal.models import GcnEventAssociation

    # read before any DBSession use expires the fixture's instance
    user_id = super_admin_user.id

    nickname = f"XG{uuid.uuid4().hex[:6]}"
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

    # the service only looks for pairs somebody has a rule for
    status, data = api(
        "POST",
        "gcn_association_rules",
        data={
            "detector_type_1": "gravitational-wave",
            "detector_type_2": "gravitational-wave",
            "days": 1.0,
            "min_consistency": 0.5,
        },
        token=super_admin_token,
    )
    assert status == 200, data

    ra, dec = float(np.random.uniform(0, 360)), float(np.random.uniform(-20, 20))
    base = (
        Time.now() - timedelta(seconds=int(np.random.randint(10**4, 10**5)))
    ).datetime.replace(microsecond=0)
    partner = base + timedelta(hours=1)
    _post_event(super_admin_token, base, ra, dec, nickname)
    _post_event(super_admin_token, partner, ra, dec, nickname)

    # the pass itself is covered by the service tests; this is about the page,
    # and Playwright's sync API already owns the event loop
    with models.DBSession() as session:
        session.add(
            GcnEventAssociation(
                dateobs_1=base,
                dateobs_2=partner,
                overlap=42.0,
                consistency=0.974,
                dt_days=1 / 24,
                confirmer_id=1,
            )
        )
        session.commit()

    page.goto(f"/become_user/{user_id}")
    page.goto(f"/gcn_events/{base.isoformat()}")

    # nothing is confirmed yet, so the summary above the tabs stays empty
    expect(page.get_by_text("Associated events:")).not_to_be_visible()

    page.get_by_role("tab", name="Associated Events").click()
    expect(page.get_by_test_id("gcn-event-associations")).to_be_visible()
    # the readable statistic, not the six-figure overlap behind it
    expect(page.get_by_text("0.974")).to_be_visible()
    expect(page.get_by_text(partner.strftime("%Y-%m-%d %H:%M:%S"))).to_be_visible()

    # selecting alone must not commit
    page.get_by_role("button", name="REJECT").first.click()
    status, data = api(
        "GET", f"gcn_event/{base.isoformat()}/associations", token=super_admin_token
    )
    assert status == 200, data
    assert data["data"][0]["status"] == "pending", "the click committed a verdict"

    # confirm it first: the summary lists only what somebody has ruled on
    page.get_by_role("button", name="CONFIRM").first.click()
    page.get_by_role("button", name="SAVE").first.click()
    expect(page.get_by_text("Associated events:")).to_be_visible()

    page.get_by_role("tab", name="Associated Events").click()
    page.get_by_role("button", name="REJECT").first.click()
    page.get_by_role("button", name="SAVE").first.click()

    expect(page.get_by_text("No associated events.")).to_be_visible()

    # the tabs after the inserted one still address their own panels
    page.get_by_role("tab", name="Observations").click()
    expect(page.get_by_test_id("gcn-event-associations")).not_to_be_visible()
    page.get_by_role("tab", name="Sources").click()
    expect(page.get_by_test_id("gcn-event-associations")).not_to_be_visible()
    status, data = api(
        "GET",
        f"gcn_event/{base.isoformat()}/associations",
        params={"includeRejected": True},
        token=super_admin_token,
    )
    assert status == 200, data
    assert data["data"][0]["status"] == "rejected", data["data"]
