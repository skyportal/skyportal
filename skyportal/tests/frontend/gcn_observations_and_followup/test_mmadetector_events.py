import uuid
from datetime import timedelta

import numpy as np
import pytest
from astropy.time import Time
from playwright.sync_api import expect

from skyportal.tests import api


@pytest.mark.flaky(reruns=3)
def test_mmadetector_shows_its_gcn_events(page, super_admin_user, super_admin_token):
    """Clicking a detector lists the events it contributed to."""
    nickname = f"XD{uuid.uuid4().hex[:6]}"
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

    # the tag matching the nickname is what links the event to the detector
    dateobs = (
        Time.now() - timedelta(seconds=int(np.random.randint(10**5, 10**7)))
    ).datetime.replace(microsecond=0)
    status, data = api(
        "POST",
        "gcn_event",
        data={
            "dateobs": dateobs.isoformat(),
            "trigger_id": str(np.random.randint(10**8, 10**9)),
            "skymap": {"ra": 42.0, "dec": 12.0, "error": 0.1},
            "tags": [nickname],
        },
        token=super_admin_token,
    )
    assert status == 200, data

    page.goto(f"/become_user/{super_admin_user.id}")
    page.goto("/mmadetectors")

    page.get_by_label(f"show gcn events for {nickname}").click()

    expect(page.get_by_test_id("mmadetector-events-table")).to_be_visible()
    expect(
        page.locator(f'//*[text()="{dateobs.strftime("%Y-%m-%d %H:%M:%S")}"]').first
    ).to_be_visible()
