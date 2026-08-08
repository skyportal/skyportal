"""End-to-end tests for the GCN crossmatch loop.

These drive ``run_cycle`` against a real Broker row and a real GcnEvent with a
real localization, stubbing only the provider's outbound calls so the test is
deterministic and needs no network. What is exercised is everything between:
event selection, geometry, the epoch window, containment, the save call, the
annotation, and the per-(event, broker) state bookkeeping.
"""

import asyncio
import uuid
from datetime import timedelta

import numpy as np
import sqlalchemy as sa

from baselayer.app import models
from skyportal.broker_apis import GENERICBROKER
from skyportal.models import Annotation, GcnEventCrossmatchState, Localization, Obj
from skyportal.tests import api
from skyportal.utils.gcn_crossmatch import ANNOTATION_ORIGIN, run_cycle
from skyportal.utils.naive_datetime import utcnow_naive

RA, DEC, ERROR = 210.0, 15.0, 0.2


def _post_event(token, group_ids):
    """A cone event recent enough to be inside the crossmatch window."""
    dateobs = (utcnow_naive() - timedelta(hours=6)).replace(microsecond=0)
    payload = {
        "dateobs": dateobs.isoformat(),
        "trigger_id": f"XM{uuid.uuid4().hex[:10]}",
        "skymap": {"ra": RA, "dec": DEC, "error": ERROR},
        "tags": ["TEST"],
        "group_ids": list(group_ids),
    }
    status, data = api("POST", "gcn_event", data=payload, token=token)
    assert status == 200, data
    return dateobs, payload["trigger_id"]


def _stub_provider(monkeypatch, alerts, saved):
    """Make GENERICBROKER return `alerts` and record every save_as_source call."""

    def query_alerts(broker, session, **kwargs):
        # record what the service asked for so the test can assert on it
        saved.setdefault("query_kwargs", []).append(kwargs)
        return alerts

    async def save_as_source(broker, alert_id, session, user, group_ids, **kwargs):
        saved.setdefault("saved", []).append((alert_id, tuple(sorted(group_ids))))
        # create the Obj the annotation will hang off, mimicking a real save
        obj = await session.scalar(sa.select(Obj).where(Obj.id == alert_id))
        if obj is None:
            session.add(Obj(id=alert_id, ra=RA, dec=DEC))
            await session.commit()
        return {"id": alert_id}

    monkeypatch.setattr(GENERICBROKER, "query_alerts", staticmethod(query_alerts))
    monkeypatch.setattr(GENERICBROKER, "save_as_source", staticmethod(save_as_source))
    monkeypatch.setattr(
        GENERICBROKER,
        "implements",
        classmethod(lambda cls: {"query_alerts": True, "save_as_source": True}),
    )


def _alert(object_id, ra, dec, jd):
    return {"objectId": object_id, "candidate": {"ra": ra, "dec": dec, "jd": jd}}


def test_crossmatch_saves_only_contained_in_window_alerts(
    super_admin_token, public_group2, broker, monkeypatch
):
    """Only alerts inside the localization *and* inside the epoch window are saved."""
    dateobs, _ = _post_event(super_admin_token, [public_group2.id])
    from astropy.time import Time

    event_jd = float(Time(dateobs).jd)

    alerts = [
        _alert("XM_inside", RA, DEC, event_jd + 0.5),  # in cone, in window
        _alert("XM_outside_cone", RA + 5.0, DEC, event_jd + 0.5),  # far away
        _alert("XM_before_window", RA, DEC, event_jd - 30.0),  # too early
        _alert("XM_after_window", RA, DEC, event_jd + 500.0),  # too late
        _alert("XM_no_jd", RA, DEC, None),  # cannot be placed in time
    ]
    recorded = {}
    _stub_provider(monkeypatch, alerts, recorded)

    matched = asyncio.run(run_cycle({}))
    assert matched >= 1, recorded

    saved_ids = {obj_id for obj_id, _ in recorded.get("saved", [])}
    assert "XM_inside" in saved_ids, saved_ids
    for rejected in (
        "XM_outside_cone",
        "XM_before_window",
        "XM_after_window",
        "XM_no_jd",
    ):
        assert rejected not in saved_ids, f"{rejected} should not have been saved"


def test_crossmatch_passes_event_groups_and_epoch_window(
    super_admin_token, public_group2, broker, monkeypatch
):
    """Saves inherit the event's groups, and the broker is given the epoch window.

    The group assertion is the security-relevant one: a restricted event's
    matches must not be saved into wider groups than the event itself.
    """
    dateobs, _ = _post_event(super_admin_token, [public_group2.id])
    from astropy.time import Time

    event_jd = float(Time(dateobs).jd)

    recorded = {}
    _stub_provider(
        monkeypatch, [_alert("XM_groups", RA, DEC, event_jd + 0.1)], recorded
    )

    asyncio.run(run_cycle({}))

    saved = recorded.get("saved", [])
    assert saved, recorded
    assert all(groups == (public_group2.id,) for _, groups in saved), saved

    kwargs = recorded.get("query_kwargs", [])
    assert kwargs, recorded
    assert all("jd_start" in k and "jd_end" in k for k in kwargs), kwargs
    # the window must bracket the event, not run open-ended
    for k in kwargs:
        assert k["jd_start"] < event_jd < k["jd_end"], (k, event_jd)


def test_crossmatch_records_state_and_annotation(
    super_admin_token, public_group2, broker, monkeypatch
):
    """A match leaves per-broker state and an event-relative annotation behind."""
    dateobs, trigger_id = _post_event(super_admin_token, [public_group2.id])
    from astropy.time import Time

    event_jd = float(Time(dateobs).jd)
    alert_jd = event_jd + 0.25
    recorded = {}
    _stub_provider(monkeypatch, [_alert("XM_state", RA, DEC, alert_jd)], recorded)

    asyncio.run(run_cycle({}))

    with models.DBSession() as session:
        state = session.scalar(
            sa.select(GcnEventCrossmatchState)
            .join(
                Localization,
                Localization.dateobs == dateobs,
            )
            .where(GcnEventCrossmatchState.broker_id == broker.id)
            .order_by(GcnEventCrossmatchState.created_at.desc())
        )
        assert state is not None, "no crossmatch state row was written"
        assert state.status == "done", state.status
        assert state.last_queried is not None
        # the resume point advances to the newest alert seen, so the next pass
        # does not re-walk ground already covered
        assert state.last_alert_jd is not None
        assert abs(state.last_alert_jd - alert_jd) < 1e-6, state.last_alert_jd

        annotation = session.scalar(
            sa.select(Annotation).where(
                Annotation.obj_id == "XM_state",
                Annotation.origin == ANNOTATION_ORIGIN,
            )
        )
        assert annotation is not None, "no crossmatch annotation was written"
        entry = annotation.data.get(trigger_id)
        assert entry is not None, annotation.data
        assert abs(entry["delta_t"] - 0.25) < 1e-3, entry
        assert entry["distance_arcmin"] < 1.0, entry


def test_crossmatch_skips_events_outside_the_age_window(
    super_admin_token, public_group2, broker, monkeypatch
):
    """An event older than max_event_age is not queried at all."""
    old_dateobs = (
        utcnow_naive()
        - timedelta(days=400)
        - timedelta(seconds=int(np.random.randint(0, 10**5)))
    ).replace(microsecond=0)
    payload = {
        "dateobs": old_dateobs.isoformat(),
        "trigger_id": f"XM{uuid.uuid4().hex[:10]}",
        "skymap": {"ra": RA, "dec": DEC, "error": ERROR},
        "group_ids": [public_group2.id],
    }
    status, data = api("POST", "gcn_event", data=payload, token=super_admin_token)
    assert status == 200, data

    recorded = {}
    _stub_provider(monkeypatch, [_alert("XM_old", RA, DEC, 2460000.0)], recorded)

    asyncio.run(run_cycle({"max_event_age": 1.0}))

    assert "XM_old" not in {o for o, _ in recorded.get("saved", [])}


def _stub_filter_provider(monkeypatch, alerts, recorded):
    """A provider that supports test_filter, i.e. the broker-side filter path."""

    def test_filter(broker, session, **kwargs):
        recorded.setdefault("test_filter_kwargs", []).append(kwargs)
        return {"results": alerts}

    async def save_as_source(broker, alert_id, session, user, group_ids, **kwargs):
        recorded.setdefault("saved", []).append((alert_id, tuple(sorted(group_ids))))
        obj = await session.scalar(sa.select(Obj).where(Obj.id == alert_id))
        if obj is None:
            session.add(Obj(id=alert_id, ra=RA, dec=DEC))
            await session.commit()
        return {"id": alert_id}

    def query_alerts(broker, session, **kwargs):
        recorded.setdefault("query_alerts_called", []).append(kwargs)
        return []

    monkeypatch.setattr(GENERICBROKER, "test_filter", staticmethod(test_filter))
    monkeypatch.setattr(GENERICBROKER, "save_as_source", staticmethod(save_as_source))
    monkeypatch.setattr(GENERICBROKER, "query_alerts", staticmethod(query_alerts))
    monkeypatch.setattr(
        GENERICBROKER,
        "implements",
        classmethod(
            lambda cls: {
                "query_alerts": True,
                "save_as_source": True,
                "test_filter": True,
            }
        ),
    )


def test_crossmatch_runs_quality_cuts_as_a_broker_filter(
    super_admin_token, public_group2, broker, monkeypatch
):
    """When the broker supports filters, cuts run server-side as a pipeline.

    The cone becomes the leading spatial stage and the quality cuts follow, so
    artifacts and asteroids are rejected by the broker rather than transferred
    and discarded here. query_alerts must not be used in this case.
    """
    dateobs, _ = _post_event(super_admin_token, [public_group2.id])
    from astropy.time import Time

    event_jd = float(Time(dateobs).jd)

    recorded = {}
    _stub_filter_provider(
        monkeypatch, [_alert("XM_filtered", RA, DEC, event_jd + 0.2)], recorded
    )

    asyncio.run(run_cycle({}))

    calls = recorded.get("test_filter_kwargs", [])
    assert calls, recorded
    assert not recorded.get("query_alerts_called"), (
        "should not fall back to query_alerts"
    )

    kwargs = calls[0]
    pipeline = kwargs["pipeline"]

    # leading stage is the cone, expressed in BOOM's shifted-longitude GeoJSON
    cone = pipeline[0]["$match"]["coordinates.radec_geojson"]["$geoWithin"]
    centre, radius_rad = cone["$centerSphere"]
    assert abs(centre[0] - (RA - 180.0)) < 1e-9, centre
    assert abs(centre[1] - DEC) < 1e-9, centre
    assert radius_rad > 0

    # the quality cuts follow it
    assert len(pipeline) > 1, pipeline
    cuts = pipeline[1]["$match"]
    assert "candidate.drb" in cuts and "candidate.rb" in cuts, cuts

    # and the epoch window is handed to the broker, not applied only locally
    assert kwargs["start_jd"] < event_jd < kwargs["end_jd"], kwargs

    # results parsed out of the {"results": [...]} envelope and saved
    assert "XM_filtered" in {o for o, _ in recorded.get("saved", [])}, recorded
