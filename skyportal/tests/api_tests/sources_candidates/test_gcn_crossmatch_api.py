"""Tests for the crossmatch progress / requeue endpoint."""

import uuid
from datetime import timedelta

import numpy as np
import pytest
from skyportal_py import SkyPortalError
from skyportal_py.gcn_events import GcnEventPost

from skyportal.tests import client
from skyportal.utils.naive_datetime import utcnow_naive


def _post_event(token, group_ids):
    dateobs = (utcnow_naive() - timedelta(hours=3)).replace(microsecond=0)
    ra, dec = float(np.random.uniform(0, 360)), float(np.random.uniform(-20, 20))
    client(token).post_gcn_event(
        GcnEventPost(
            dateobs=dateobs.isoformat(),
            trigger_id=f"XM{uuid.uuid4().hex[:10]}",
            skymap={"ra": ra, "dec": dec, "error": 0.2},
            group_ids=list(group_ids),
        )
    )
    return dateobs.strftime("%Y-%m-%d %H:%M:%S")


def test_crossmatch_progress_readable_by_group_member(
    super_admin_token, public_group2, view_only_token_group2
):
    dateobs = _post_event(super_admin_token, [public_group2.id])
    states = client(view_only_token_group2).fetch_gcn_event_crossmatch(dateobs)
    assert isinstance(states, list)


def test_crossmatch_progress_hidden_from_non_members(
    super_admin_token, public_group2, view_only_token
):
    """A restricted event's crossmatch progress must not leak its existence."""
    dateobs = _post_event(super_admin_token, [public_group2.id])
    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).fetch_gcn_event_crossmatch(dateobs)
    assert err.value.status_code in (400, 403, 404)


def test_requeue_requires_manage_gcns(
    super_admin_token, public_group2, view_only_token_group2
):
    dateobs = _post_event(super_admin_token, [public_group2.id])
    with pytest.raises(SkyPortalError) as err:
        client(view_only_token_group2).post_gcn_event_crossmatch(dateobs)
    assert err.value.status_code in (400, 401, 403)

    result = client(super_admin_token).post_gcn_event_crossmatch(dateobs)
    assert result.filters_requeued is not None


def test_requeue_unknown_event_errors(super_admin_token):
    with pytest.raises(SkyPortalError) as err:
        client(super_admin_token).post_gcn_event_crossmatch("2001-01-01 00:00:00")
    assert err.value.status_code == 400
