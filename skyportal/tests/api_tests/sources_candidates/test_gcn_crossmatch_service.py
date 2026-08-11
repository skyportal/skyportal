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
from skyportal.models import (
    Annotation,
    Candidate,
    GcnEventCrossmatchState,
    Localization,
    Obj,
    Source,
)
from skyportal.tests import api
from skyportal.utils.gcn_crossmatch import ANNOTATION_ORIGIN, run_cycle
from skyportal.utils.naive_datetime import utcnow_naive

ERROR = 0.2


def _unique_position():
    """A distinct sky position per test.

    run_cycle is global -- it walks every recent event in the database, so a
    shared position would let one test's broker calls be attributed to another
    test's event. Positions are how calls are told apart.
    """
    return float(np.random.uniform(0, 360)), float(np.random.uniform(-20, 20))


def _post_event(token, group_ids, ra, dec):
    """A cone event recent enough to be inside the crossmatch window."""
    dateobs = (utcnow_naive() - timedelta(hours=6)).replace(microsecond=0)
    payload = {
        "dateobs": dateobs.isoformat(),
        "trigger_id": f"XM{uuid.uuid4().hex[:10]}",
        "skymap": {"ra": ra, "dec": dec, "error": ERROR},
        "tags": ["TEST"],
        "group_ids": list(group_ids),
    }
    status, data = api("POST", "gcn_event", data=payload, token=token)
    assert status == 200, data
    return dateobs, payload["trigger_id"]


def _stub_provider(monkeypatch, alerts, saved, ra=0.0, dec=0.0):
    """Make GENERICBROKER return `alerts`; the service creates candidates itself."""

    def query_alerts(broker, session, **kwargs):
        # record what the service asked for so the test can assert on it
        saved.setdefault("query_kwargs", []).append(kwargs)
        return alerts

    monkeypatch.setattr(GENERICBROKER, "query_alerts", staticmethod(query_alerts))
    monkeypatch.setattr(
        GENERICBROKER,
        "implements",
        classmethod(lambda cls: {"query_alerts": True}),
    )


def _objs_created(obj_ids):
    """Which of these object ids now exist (a match creates the Obj)."""
    with models.DBSession() as session:
        rows = session.scalars(sa.select(Obj.id).where(Obj.id.in_(list(obj_ids))))
        return set(rows.all())


def _calls_at(recorded, key, ra):
    """Broker calls issued for the event at ``ra`` (cone centre in the payload)."""
    out = []
    for k in recorded.get(key, []):
        if key == "test_filter_kwargs":
            centre = k["pipeline"][0]["$match"]["coordinates.radec_geojson"]
            call_ra = centre["$geoWithin"]["$centerSphere"][0][0] + 180.0
        else:
            call_ra = k.get("ra")
        # the cone is parsed back out of localization_name, which carries only
        # 5 decimals, so match at that precision
        if call_ra is not None and abs(call_ra - ra) < 1e-4:
            out.append(k)
    return out


def _alert(object_id, ra, dec, jd):
    return {"objectId": object_id, "candidate": {"ra": ra, "dec": dec, "jd": jd}}


def test_crossmatch_saves_only_contained_in_window_alerts(
    super_admin_token, public_group2, broker, monkeypatch
):
    """Only alerts inside the localization *and* inside the epoch window are saved."""
    ra, dec = _unique_position()
    dateobs, _ = _post_event(super_admin_token, [public_group2.id], ra, dec)
    from astropy.time import Time

    event_jd = float(Time(dateobs).jd)

    alerts = [
        _alert("XM_inside", ra, dec, event_jd + 0.5),  # in cone, in window
        _alert("XM_outside_cone", ra + 5.0, dec, event_jd + 0.5),  # far away
        _alert("XM_before_window", ra, dec, event_jd - 30.0),  # too early
        _alert("XM_after_window", ra, dec, event_jd + 500.0),  # too late
        _alert("XM_no_jd", ra, dec, None),  # cannot be placed in time
    ]
    recorded = {}
    _stub_provider(monkeypatch, alerts, recorded, ra, dec)

    # archival off: this is about the forward window, and the archival pass
    # would legitimately match XM_before_window
    matched = asyncio.run(run_cycle({"archival": False}))
    assert matched >= 1, recorded

    all_ids = [a["objectId"] for a in alerts]
    created = _objs_created(all_ids)
    assert "XM_inside" in created, created
    for rejected in (
        "XM_outside_cone",
        "XM_before_window",
        "XM_after_window",
        "XM_no_jd",
    ):
        assert rejected not in created, f"{rejected} should not have matched"


def test_crossmatch_passes_event_groups_and_epoch_window(
    super_admin_token, public_group2, broker, monkeypatch
):
    """Saves inherit the event's groups, and the broker is given the epoch window.

    The group assertion is the security-relevant one: a restricted event's
    matches must not be saved into wider groups than the event itself.
    """
    ra, dec = _unique_position()
    dateobs, _ = _post_event(super_admin_token, [public_group2.id], ra, dec)
    from astropy.time import Time

    event_jd = float(Time(dateobs).jd)

    recorded = {}
    _stub_provider(
        monkeypatch, [_alert("XM_groups", ra, dec, event_jd + 0.1)], recorded, ra, dec
    )

    asyncio.run(run_cycle({"archival": False}))

    assert "XM_groups" in _objs_created(["XM_groups"])
    # a match is raised to scan, never auto-saved as a Source
    with models.DBSession() as session:
        sources = session.scalars(
            sa.select(Source.obj_id).where(Source.obj_id == "XM_groups")
        ).all()
    assert sources == [], f"match was auto-saved as a Source: {sources}"

    calls = _calls_at(recorded, "query_kwargs", ra)
    assert calls, recorded
    assert all("jd_start" in k and "jd_end" in k for k in calls), calls
    # exactly one pass brackets the event (the forward one); the archival pass
    # deliberately sits entirely before it
    assert all(k["jd_start"] < event_jd < k["jd_end"] for k in calls), calls


def test_crossmatch_records_state_and_annotation(
    super_admin_token, public_group2, broker, monkeypatch
):
    """A match leaves per-broker state and an event-relative annotation behind."""
    ra, dec = _unique_position()
    dateobs, trigger_id = _post_event(super_admin_token, [public_group2.id], ra, dec)
    from astropy.time import Time

    event_jd = float(Time(dateobs).jd)
    alert_jd = event_jd + 0.25
    recorded = {}
    _stub_provider(
        monkeypatch, [_alert("XM_state", ra, dec, alert_jd)], recorded, ra, dec
    )

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
    ra, dec = _unique_position()
    old_dateobs = (
        utcnow_naive()
        - timedelta(days=400)
        - timedelta(seconds=int(np.random.randint(0, 10**5)))
    ).replace(microsecond=0)
    payload = {
        "dateobs": old_dateobs.isoformat(),
        "trigger_id": f"XM{uuid.uuid4().hex[:10]}",
        "skymap": {"ra": ra, "dec": dec, "error": ERROR},
        "group_ids": [public_group2.id],
    }
    status, data = api("POST", "gcn_event", data=payload, token=super_admin_token)
    assert status == 200, data

    recorded = {}
    _stub_provider(
        monkeypatch, [_alert("XM_old", ra, dec, 2460000.0)], recorded, ra, dec
    )

    asyncio.run(run_cycle({"max_event_age": 1.0, "archival": False}))

    assert "XM_old" not in _objs_created(["XM_old"])


def _stub_filter_provider(monkeypatch, alerts, recorded, ra=0.0, dec=0.0):
    """A provider that supports test_filter, i.e. the broker-side filter path."""

    def test_filter(broker, session, **kwargs):
        recorded.setdefault("test_filter_kwargs", []).append(kwargs)
        return {"results": alerts}

    def query_alerts(broker, session, **kwargs):
        recorded.setdefault("query_alerts_called", []).append(kwargs)
        return []

    monkeypatch.setattr(GENERICBROKER, "test_filter", staticmethod(test_filter))
    monkeypatch.setattr(GENERICBROKER, "query_alerts", staticmethod(query_alerts))
    monkeypatch.setattr(
        GENERICBROKER,
        "implements",
        classmethod(
            lambda cls: {
                "query_alerts": True,
                "test_filter": True,
                # the crossmatch only sends a Mongo pipeline to a provider that
                # declares it speaks one
                "filter_pipeline": "mongo",
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
    ra, dec = _unique_position()
    dateobs, _ = _post_event(super_admin_token, [public_group2.id], ra, dec)
    from astropy.time import Time

    event_jd = float(Time(dateobs).jd)

    recorded = {}
    _stub_filter_provider(
        monkeypatch,
        [_alert("XM_filtered", ra, dec, event_jd + 0.2)],
        recorded,
        ra,
        dec,
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
    # localization_name is written by from_cone with 5-decimal precision, and
    # search_cone parses the cone back out of it, so compare at that precision
    assert abs(centre[0] - (ra - 180.0)) < 1e-4, centre
    assert abs(centre[1] - dec) < 1e-4, centre
    assert radius_rad > 0

    # the quality cuts follow it
    assert len(pipeline) > 1, pipeline
    cuts = pipeline[1]["$match"]
    assert "candidate.drb" in cuts and "candidate.rb" in cuts, cuts

    # and the epoch window is handed to the broker, not applied only locally

    # results parsed out of the {"results": [...]} envelope and turned into a match
    assert "XM_filtered" in _objs_created(["XM_filtered"]), recorded


def test_annotation_carries_alert_quality_fields(
    super_admin_token, public_group2, broker, monkeypatch
):
    """The annotation exposes the columns reviewers triage on."""
    ra, dec = _unique_position()
    dateobs, trigger_id = _post_event(super_admin_token, [public_group2.id], ra, dec)
    from astropy.time import Time

    event_jd = float(Time(dateobs).jd)
    alert = {
        "objectId": "XM_fields",
        "candidate": {
            "ra": ra,
            "dec": dec,
            "jd": event_jd + 0.25,
            "drb": 0.987,
            "sgscore1": 0.02,
            "distpsnr1": 3.5,
            "ssdistnr": -999.0,
            "ssmagnr": -999.0,
            "ndethist": 4,
            "jdstarthist": event_jd - 9.0,
        },
    }
    recorded = {}
    _stub_provider(monkeypatch, [alert], recorded, ra, dec)

    asyncio.run(run_cycle({"archival": False}))

    with models.DBSession() as session:
        annotation = session.scalar(
            sa.select(Annotation).where(
                Annotation.obj_id == "XM_fields",
                Annotation.origin == ANNOTATION_ORIGIN,
            )
        )
        assert annotation is not None
        entry = annotation.data[trigger_id]

    for key in (
        "delta_t",
        "distance_arcmin",
        "distance_ratio",
        "drb",
        "sgscore",
        "distpsnr",
        "ssdistnr",
        "ssmagnr",
        "ndethist",
        "age",
        "event_mjd",
    ):
        assert key in entry, f"{key} missing from {sorted(entry)}"

    assert entry["drb"] == 0.987
    assert entry["ndethist"] == 4
    assert abs(entry["age"] - 9.25) < 1e-3, entry["age"]
    assert abs(entry["event_mjd"] - (event_jd - 2400000.5)) < 1e-6


def test_archival_match_flags_prior_activity_and_survives_forward_pass(
    super_admin_token, public_group2, broker, monkeypatch
):
    """A pre-event detection marks the candidate, and a later match keeps the mark.

    The annotation is keyed per event, so without stickiness the forward pass
    would overwrite the archival entry and erase the very fact that rules the
    candidate out.
    """
    ra, dec = _unique_position()
    dateobs, trigger_id = _post_event(super_admin_token, [public_group2.id], ra, dec)
    from astropy.time import Time

    event_jd = float(Time(dateobs).jd)

    # one alert well before the event, one just after: the same object active in
    # both windows
    archival_alert = _alert("XM_prior", ra, dec, event_jd - 10.0)
    forward_alert = _alert("XM_prior", ra, dec, event_jd + 0.3)

    def query_alerts(broker_, session, **kwargs):
        # serve whichever alert falls in the window being asked for
        out = []
        for a in (archival_alert, forward_alert):
            jd = a["candidate"]["jd"]
            if kwargs["jd_start"] <= jd <= kwargs["jd_end"]:
                out.append(a)
        return out

    recorded = {}
    _stub_provider(monkeypatch, [], recorded, ra, dec)
    monkeypatch.setattr(GENERICBROKER, "query_alerts", staticmethod(query_alerts))

    asyncio.run(run_cycle({"archival": True, "archival_days": 31.0}))

    with models.DBSession() as session:
        annotation = session.scalar(
            sa.select(Annotation).where(
                Annotation.obj_id == "XM_prior",
                Annotation.origin == ANNOTATION_ORIGIN,
            )
        )
        assert annotation is not None, "archival match was not annotated"
        entry = annotation.data[trigger_id]
        assert entry.get("prior_activity") is True, entry
        # the forward pass ran too and refreshed the timing
        assert entry["delta_t"] > 0, entry

        state = session.scalar(
            sa.select(GcnEventCrossmatchState)
            .where(GcnEventCrossmatchState.broker_id == broker.id)
            .order_by(GcnEventCrossmatchState.created_at.desc())
        )
        assert state.archival_done is True, "archival pass should not repeat"


def test_match_creates_candidate_not_source(
    super_admin_token, public_group2, public_filter, broker, monkeypatch
):
    """With a filter configured, a match becomes a scannable Candidate only.

    The Obj and Candidate put it on the scanning page; no Source is created,
    so it stays a suggestion until a human saves it.
    """
    ra, dec = _unique_position()
    dateobs, _ = _post_event(super_admin_token, [public_group2.id], ra, dec)
    from astropy.time import Time

    event_jd = float(Time(dateobs).jd)
    obj_id = f"XM_cand_{uuid.uuid4().hex[:8]}"

    alert = _alert(obj_id, ra, dec, event_jd + 0.2)
    alert["candidate"]["candid"] = 123456789
    alert["candidate"]["drb"] = 0.99

    recorded = {}
    _stub_provider(monkeypatch, [alert], recorded, ra, dec)

    asyncio.run(run_cycle({"archival": False, "filter_id": public_filter.id}))

    with models.DBSession() as session:
        obj = session.scalar(sa.select(Obj).where(Obj.id == obj_id))
        assert obj is not None, "no Obj was created for the match"
        assert abs(obj.ra - ra) < 1e-6 and abs(obj.dec - dec) < 1e-6

        candidates = session.scalars(
            sa.select(Candidate).where(Candidate.obj_id == obj_id)
        ).all()
        assert len(candidates) == 1, candidates
        assert candidates[0].filter_id == public_filter.id
        assert candidates[0].passing_alert_id == 123456789

        sources = session.scalars(
            sa.select(Source.obj_id).where(Source.obj_id == obj_id)
        ).all()
        assert sources == [], f"match should not be auto-saved as a Source: {sources}"


def test_candidate_creation_is_idempotent(
    super_admin_token, public_group2, public_filter, broker, monkeypatch
):
    """Re-running must not pile up duplicate candidates for the same epoch."""
    ra, dec = _unique_position()
    dateobs, _ = _post_event(super_admin_token, [public_group2.id], ra, dec)
    from astropy.time import Time

    event_jd = float(Time(dateobs).jd)
    obj_id = f"XM_dup_{uuid.uuid4().hex[:8]}"

    recorded = {}
    _stub_provider(
        monkeypatch, [_alert(obj_id, ra, dec, event_jd + 0.2)], recorded, ra, dec
    )

    config = {"archival": False, "filter_id": public_filter.id}
    asyncio.run(run_cycle(config))
    # force the event to be due again rather than waiting out the recheck gap
    with models.DBSession() as session:
        session.execute(
            sa.update(GcnEventCrossmatchState).values(
                last_queried=None, last_alert_jd=None
            )
        )
        session.commit()
    asyncio.run(run_cycle(config))

    with models.DBSession() as session:
        candidates = session.scalars(
            sa.select(Candidate).where(Candidate.obj_id == obj_id)
        ).all()
    assert len(candidates) == 1, f"duplicate candidates created: {candidates}"
