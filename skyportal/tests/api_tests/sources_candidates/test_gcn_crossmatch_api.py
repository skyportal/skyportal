"""Tests for the crossmatch progress / requeue endpoint."""

import uuid
from datetime import timedelta

import numpy as np

from skyportal.tests import api
from skyportal.utils.naive_datetime import utcnow_naive


def _post_event(token, group_ids):
    dateobs = (utcnow_naive() - timedelta(hours=3)).replace(microsecond=0)
    ra, dec = float(np.random.uniform(0, 360)), float(np.random.uniform(-20, 20))
    payload = {
        "dateobs": dateobs.isoformat(),
        "trigger_id": f"XM{uuid.uuid4().hex[:10]}",
        "skymap": {"ra": ra, "dec": dec, "error": 0.2},
        "group_ids": list(group_ids),
    }
    status, data = api("POST", "gcn_event", data=payload, token=token)
    assert status == 200, data
    return dateobs.strftime("%Y-%m-%d %H:%M:%S")


def test_crossmatch_progress_readable_by_group_member(
    super_admin_token, public_group2, view_only_token_group2
):
    dateobs = _post_event(super_admin_token, [public_group2.id])
    status, data = api(
        "GET", f"gcn_event/{dateobs}/crossmatch", token=view_only_token_group2
    )
    assert status == 200, data
    assert isinstance(data["data"], list)


def test_crossmatch_progress_hidden_from_non_members(
    super_admin_token, public_group2, view_only_token
):
    """A restricted event's crossmatch progress must not leak its existence."""
    dateobs = _post_event(super_admin_token, [public_group2.id])
    status, data = api("GET", f"gcn_event/{dateobs}/crossmatch", token=view_only_token)
    assert status in (400, 403, 404), data


def test_requeue_requires_manage_gcns(
    super_admin_token, public_group2, view_only_token_group2
):
    dateobs = _post_event(super_admin_token, [public_group2.id])
    status, data = api(
        "POST", f"gcn_event/{dateobs}/crossmatch", token=view_only_token_group2
    )
    assert status in (400, 401, 403), data

    status, data = api(
        "POST", f"gcn_event/{dateobs}/crossmatch", token=super_admin_token
    )
    assert status == 200, data
    assert "brokers_requeued" in data["data"], data


def test_requeue_unknown_event_errors(super_admin_token):
    status, data = api(
        "POST", "gcn_event/2001-01-01 00:00:00/crossmatch", token=super_admin_token
    )
    assert status == 400, data
