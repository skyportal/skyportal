"""Tests for the crossmatch progress / requeue endpoint."""

import uuid
from datetime import datetime, timedelta

import numpy as np
import pytest
import sqlalchemy as sa

from skyportal.model_util import create_token, delete_token
from skyportal.models import DBSession, GcnEvent, GcnEventCrossmatchState, Localization
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
    assert status in (400, 403), data

    status, data = api(
        "POST", f"gcn_event/{dateobs}/crossmatch", token=super_admin_token
    )
    assert status == 200, data
    assert "filters_requeued" in data["data"], data


def test_requeue_unknown_event_errors(super_admin_token):
    status, data = api(
        "POST", "gcn_event/2001-01-01 00:00:00/crossmatch", token=super_admin_token
    )
    assert status == 400, data


@pytest.fixture()
def manage_gcns_token(group_admin_user):
    """Can requeue, and reads public_group's filters but not public_group2's."""
    token_id = create_token(
        ACLs=["Manage GCNs"], user_id=group_admin_user.id, name=str(uuid.uuid4())
    )
    yield token_id
    delete_token(token_id)


def _add_done_states(dateobs, filter_ids):
    """One state per filter, as a fully searched window leaves it."""
    dateobs = datetime.fromisoformat(dateobs)
    with DBSession() as session:
        event_id = session.scalar(
            sa.select(GcnEvent.id).where(GcnEvent.dateobs == dateobs)
        )
        localization_id = session.scalar(
            sa.select(Localization.id).where(Localization.dateobs == dateobs)
        )
        states = [
            GcnEventCrossmatchState(
                gcnevent_id=event_id,
                filter_id=filter_id,
                localization_id=localization_id,
                status="done",
                last_queried=utcnow_naive(),
                last_alert_jd=2461000.5,
                archival_done=True,
                n_matches=2,
            )
            for filter_id in filter_ids
        ]
        session.add_all(states)
        session.commit()
        return [state.id for state in states]


def test_requeue_unknown_or_unreadable_filter_errors(
    super_admin_token, manage_gcns_token, public_group, public_filter2
):
    """Both answer alike, so a requeue cannot probe for hidden filters."""
    dateobs = _post_event(super_admin_token, [public_group.id])
    for filter_id in (999999999, public_filter2.id):
        status, data = api(
            "POST",
            f"gcn_event/{dateobs}/crossmatch",
            data={"filter_id": filter_id},
            token=manage_gcns_token,
        )
        assert status == 400, data
        assert f"No filter with ID {filter_id}" in data["message"], data


def test_requeue_one_filter_leaves_the_others(
    super_admin_token, manage_gcns_token, public_group, public_filter, public_filter2
):
    filter_id, other_filter_id = public_filter.id, public_filter2.id
    dateobs = _post_event(super_admin_token, [public_group.id])
    requeued_id, untouched_id = _add_done_states(dateobs, [filter_id, other_filter_id])

    status, data = api(
        "POST",
        f"gcn_event/{dateobs}/crossmatch",
        data={"filter_id": filter_id},
        token=manage_gcns_token,
    )
    assert status == 200, data
    assert data["data"]["filters_requeued"] == 1, data

    with DBSession() as session:
        requeued = session.get(GcnEventCrossmatchState, requeued_id)
        assert requeued.status == "pending"
        assert requeued.archival_done is False
        assert requeued.last_queried is None
        assert requeued.last_alert_jd is None
        assert requeued.n_matches == 0
        untouched = session.get(GcnEventCrossmatchState, untouched_id)
        assert untouched.status == "done"
        assert untouched.archival_done is True
        assert untouched.n_matches == 2
