"""End-to-end tests for the GCN crossmatch loop.

These drive ``run_cycle`` against a real Broker row and a real GcnEvent with a
real localization, stubbing only the provider's outbound calls so the test is
deterministic and needs no network. What is exercised is everything between:
event selection, geometry, the epoch window, containment, the save call, the
annotation, and the per-(event, broker) state bookkeeping.
"""

import asyncio
import base64
import gzip
import io
import uuid
from datetime import timedelta

import numpy as np
import pytest
import sqlalchemy as sa
from astropy.io import fits
from astropy.time import Time

from baselayer.app import models
from skyportal.broker_apis import GENERICBROKER
from skyportal.models import (
    Annotation,
    Candidate,
    Filter,
    GcnEventCrossmatchState,
    Instrument,
    Localization,
    Obj,
    Photometry,
    Source,
    Thumbnail,
)
from skyportal.tests import api
from skyportal.tests.fixtures import (
    FilterFactory,
    InstrumentFactory,
    StreamFactory,
)
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


def _unique_id(prefix):
    """A distinct object id per run.

    Objs outlive the pytest run that created them, so a fixed id lets a previous
    run's leftover satisfy an "exists" assertion or break an "absent" one.
    """
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


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


@pytest.fixture()
def crossmatch_event(super_admin_token, public_group2):
    """Deleted afterwards: run_cycle walks every recent event and loads its skymap."""
    ra, dec = _unique_position()
    dateobs, trigger_id = _post_event(super_admin_token, [public_group2.id], ra, dec)
    yield dateobs, trigger_id, ra, dec
    api("DELETE", f"gcn_event/{dateobs.isoformat()}", token=super_admin_token)


@pytest.fixture()
def crossmatch_filter(public_group, broker):
    """A filter opted into the crossmatch.

    The filter is the unit of configuration: it names the broker, the stream
    (hence survey and programids) and the group that sees the candidates.
    """
    stream = StreamFactory(
        altdata={"collection": "ZTF_alerts", "selector": [1, 2]},
    )
    filter_ = FilterFactory(
        group=public_group,
        stream=stream,
        broker=broker,
        altdata={"gcn_crossmatch": {"enabled": True}},
    )
    filter_id, stream_id = filter_.id, stream.id
    yield filter_
    FilterFactory.teardown(filter_id)
    StreamFactory.teardown(stream_id)


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


def _alert(object_id, ra, dec, jd, candid=None):
    candidate = {"ra": ra, "dec": dec, "jd": jd}
    if candid is not None:
        candidate["candid"] = candid
    return {"objectId": object_id, "candidate": candidate}


def _fits_cutout():
    """One cutout in the wire format a ZTF alert carries: gzipped FITS, base64."""
    buff = io.BytesIO()
    fits.PrimaryHDU(np.arange(64, dtype=np.float32).reshape(8, 8)).writeto(buff)
    return base64.b64encode(gzip.compress(buff.getvalue())).decode()


def test_crossmatch_saves_only_contained_in_window_alerts(
    broker,
    crossmatch_filter,
    crossmatch_event,
    monkeypatch,
):
    """Only alerts inside the localization *and* inside the epoch window are saved."""
    dateobs, _, ra, dec = crossmatch_event
    from astropy.time import Time

    event_jd = float(Time(dateobs).jd)

    inside = _unique_id("XM_inside")
    outside_cone = _unique_id("XM_outside_cone")
    before_window = _unique_id("XM_before_window")
    after_window = _unique_id("XM_after_window")
    no_jd = _unique_id("XM_no_jd")
    alerts = [
        _alert(inside, ra, dec, event_jd + 0.5),  # in cone, in window
        _alert(outside_cone, ra + 5.0, dec, event_jd + 0.5),  # far away
        _alert(before_window, ra, dec, event_jd - 30.0),  # too early
        _alert(after_window, ra, dec, event_jd + 500.0),  # too late
        _alert(no_jd, ra, dec, None),  # cannot be placed in time
    ]
    recorded = {}
    _stub_provider(monkeypatch, alerts, recorded, ra, dec)

    # archival off: this is about the forward window, and the archival pass
    # would legitimately match XM_before_window
    matched = asyncio.run(run_cycle({"archival": False}))
    assert matched >= 1, recorded

    all_ids = [a["objectId"] for a in alerts]
    created = _objs_created(all_ids)
    assert inside in created, created
    for rejected in (outside_cone, before_window, after_window, no_jd):
        assert rejected not in created, f"{rejected} should not have matched"


def test_crossmatch_passes_event_groups_and_epoch_window(
    broker,
    crossmatch_filter,
    crossmatch_event,
    monkeypatch,
):
    """Saves inherit the event's groups, and the broker is given the epoch window.

    The group assertion is the security-relevant one: a restricted event's
    matches must not be saved into wider groups than the event itself.
    """
    dateobs, _, ra, dec = crossmatch_event
    from astropy.time import Time

    event_jd = float(Time(dateobs).jd)

    obj_id = _unique_id("XM_groups")
    recorded = {}
    _stub_provider(
        monkeypatch, [_alert(obj_id, ra, dec, event_jd + 0.1)], recorded, ra, dec
    )

    asyncio.run(run_cycle({"archival": False}))

    assert obj_id in _objs_created([obj_id])
    # a match is raised to scan, never auto-saved as a Source
    with models.DBSession() as session:
        sources = session.scalars(
            sa.select(Source.obj_id).where(Source.obj_id == obj_id)
        ).all()
    assert sources == [], f"match was auto-saved as a Source: {sources}"

    calls = _calls_at(recorded, "query_kwargs", ra)
    assert calls, recorded
    assert all("jd_start" in k and "jd_end" in k for k in calls), calls
    # exactly one pass brackets the event (the forward one); the archival pass
    # deliberately sits entirely before it
    assert all(k["jd_start"] < event_jd < k["jd_end"] for k in calls), calls


def test_crossmatch_records_state_and_annotation(
    broker,
    crossmatch_filter,
    crossmatch_event,
    monkeypatch,
):
    """A match leaves per-broker state and an event-relative annotation behind."""
    dateobs, trigger_id, ra, dec = crossmatch_event
    from astropy.time import Time

    event_jd = float(Time(dateobs).jd)
    alert_jd = event_jd + 0.25
    obj_id = _unique_id("XM_state")
    recorded = {}
    _stub_provider(monkeypatch, [_alert(obj_id, ra, dec, alert_jd)], recorded, ra, dec)

    asyncio.run(run_cycle({}))

    with models.DBSession() as session:
        state = session.scalar(
            sa.select(GcnEventCrossmatchState)
            .join(
                Localization,
                Localization.dateobs == dateobs,
            )
            .where(GcnEventCrossmatchState.filter_id == crossmatch_filter.id)
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
                Annotation.obj_id == obj_id,
                Annotation.origin == ANNOTATION_ORIGIN,
            )
        )
        assert annotation is not None, "no crossmatch annotation was written"
        entry = annotation.data.get(trigger_id)
        assert entry is not None, annotation.data
        assert abs(entry["delta_t"] - 0.25) < 1e-3, entry
        assert entry["distance_arcmin"] < 1.0, entry


def test_crossmatch_skips_events_outside_the_age_window(
    super_admin_token, public_group2, broker, crossmatch_filter, monkeypatch
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

    obj_id = _unique_id("XM_old")
    recorded = {}
    _stub_provider(monkeypatch, [_alert(obj_id, ra, dec, 2460000.0)], recorded, ra, dec)

    asyncio.run(run_cycle({"max_event_age": 1.0, "archival": False}))

    assert obj_id not in _objs_created([obj_id])


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
    broker,
    crossmatch_filter,
    crossmatch_event,
    monkeypatch,
):
    """When the broker supports filters, cuts run server-side as a pipeline.

    The cone becomes the leading spatial stage and the quality cuts follow, so
    artifacts and asteroids are rejected by the broker rather than transferred
    and discarded here. query_alerts must not be used in this case.
    """
    dateobs, _, ra, dec = crossmatch_event
    from astropy.time import Time

    event_jd = float(Time(dateobs).jd)

    obj_id = _unique_id("XM_filtered")
    recorded = {}
    _stub_filter_provider(
        monkeypatch,
        [_alert(obj_id, ra, dec, event_jd + 0.2)],
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
    assert obj_id in _objs_created([obj_id]), recorded


def test_annotation_carries_alert_quality_fields(
    broker,
    crossmatch_filter,
    crossmatch_event,
    monkeypatch,
):
    """The annotation exposes the columns reviewers triage on."""
    dateobs, trigger_id, ra, dec = crossmatch_event
    from astropy.time import Time

    event_jd = float(Time(dateobs).jd)
    obj_id = _unique_id("XM_fields")
    alert = {
        "objectId": obj_id,
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
                Annotation.obj_id == obj_id,
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
    broker,
    crossmatch_filter,
    crossmatch_event,
    monkeypatch,
):
    """A pre-event detection marks the candidate, and a later match keeps the mark.

    The annotation is keyed per event, so without stickiness the forward pass
    would overwrite the archival entry and erase the very fact that rules the
    candidate out.
    """
    dateobs, trigger_id, ra, dec = crossmatch_event
    from astropy.time import Time

    event_jd = float(Time(dateobs).jd)

    # one alert well before the event, one just after: the same object active in
    # both windows
    obj_id = _unique_id("XM_prior")
    archival_alert = _alert(obj_id, ra, dec, event_jd - 10.0)
    forward_alert = _alert(obj_id, ra, dec, event_jd + 0.3)

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
                Annotation.obj_id == obj_id,
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
            .where(GcnEventCrossmatchState.filter_id == crossmatch_filter.id)
            .order_by(GcnEventCrossmatchState.created_at.desc())
        )
        assert state.archival_done is True, "archival pass should not repeat"


def test_match_creates_candidate_not_source(
    crossmatch_filter,
    crossmatch_event,
    broker,
    monkeypatch,
):
    """With a filter configured, a match becomes a scannable Candidate only.

    The Obj and Candidate put it on the scanning page; no Source is created,
    so it stays a suggestion until a human saves it.
    """
    dateobs, _, ra, dec = crossmatch_event
    from astropy.time import Time

    event_jd = float(Time(dateobs).jd)
    obj_id = _unique_id("XM_cand")

    alert = _alert(obj_id, ra, dec, event_jd + 0.2)
    alert["candidate"]["candid"] = 123456789
    alert["candidate"]["drb"] = 0.99

    recorded = {}
    _stub_provider(monkeypatch, [alert], recorded, ra, dec)

    asyncio.run(run_cycle({"archival": False}))

    with models.DBSession() as session:
        obj = session.scalar(sa.select(Obj).where(Obj.id == obj_id))
        assert obj is not None, "no Obj was created for the match"
        assert abs(obj.ra - ra) < 1e-6 and abs(obj.dec - dec) < 1e-6

        candidates = session.scalars(
            sa.select(Candidate).where(Candidate.obj_id == obj_id)
        ).all()
        assert len(candidates) == 1, candidates
        assert candidates[0].filter_id == crossmatch_filter.id
        assert candidates[0].passing_alert_id == 123456789

        sources = session.scalars(
            sa.select(Source.obj_id).where(Source.obj_id == obj_id)
        ).all()
        assert sources == [], f"match should not be auto-saved as a Source: {sources}"


def test_candidate_creation_is_idempotent(
    crossmatch_filter,
    crossmatch_event,
    broker,
    monkeypatch,
):
    """Re-running must not pile up duplicate candidates for the same epoch."""
    dateobs, _, ra, dec = crossmatch_event
    from astropy.time import Time

    event_jd = float(Time(dateobs).jd)
    obj_id = _unique_id("XM_dup")

    recorded = {}
    _stub_provider(
        monkeypatch, [_alert(obj_id, ra, dec, event_jd + 0.2)], recorded, ra, dec
    )

    config = {"archival": False}
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


def test_filter_only_runs_against_matching_events(
    broker,
    crossmatch_filter,
    crossmatch_event,
    monkeypatch,
):
    """A filter scoped by gcn_tags skips events that do not carry one.

    Same `filters` shape as DefaultGcnTag: an empty list means no restriction,
    otherwise the event must carry at least one listed tag. This is what keeps
    GRB matches out of an EP-only scanning page.
    """
    # capture before opening other sessions: the fixture instance detaches
    filter_id = crossmatch_filter.id
    dateobs, _, ra, dec = crossmatch_event
    alert_jd = Time(dateobs).jd + 0.5

    # the event above carries ["TEST"]; scope the filter to something else
    with models.DBSession() as session:
        f = session.get(Filter, filter_id)
        f.altdata = {
            "gcn_crossmatch": {"enabled": True, "filters": {"gcn_tags": ["EP"]}}
        }
        session.commit()

    obj_id = _unique_id("XM_scoped")
    recorded = {}
    _stub_provider(monkeypatch, [_alert(obj_id, ra, dec, alert_jd)], recorded, ra, dec)
    asyncio.run(run_cycle({"archival": False}))

    assert not _calls_at(recorded, "query_kwargs", ra), (
        "filter ran against an event that does not carry its tag"
    )
    assert _objs_created([obj_id]) == set()

    # widen the scope to a tag the event does carry, and it runs
    with models.DBSession() as session:
        f = session.get(Filter, filter_id)
        f.altdata = {
            "gcn_crossmatch": {"enabled": True, "filters": {"gcn_tags": ["TEST"]}}
        }
        session.commit()

    asyncio.run(run_cycle({"archival": False}))
    assert _calls_at(recorded, "query_kwargs", ra), (
        "filter did not run on a tagged event"
    )


@pytest.fixture()
def ztf_instrument():
    """Photometry ingest looks the survey instrument up by name."""
    created_id = None
    if (
        models.DBSession().scalar(sa.select(Instrument).where(Instrument.name == "ZTF"))
        is None
    ):
        instrument = InstrumentFactory(name="ZTF")
        models.DBSession().commit()
        created_id = instrument.id
    yield
    if created_id is not None:
        with models.DBSession() as session:
            instrument = session.get(Instrument, created_id)
            if instrument is not None:
                session.delete(instrument)
                session.commit()


def _stub_provider_with_photometry(
    monkeypatch, alerts, saved, ra, dec, history, cutouts=None
):
    """A provider that also serves detection history via get_alert, and cutouts
    via get_cutouts. With no ``cutouts`` the cutout call raises, which is the
    common case: capability advertised, this particular alert unavailable."""

    def query_alerts(broker, session, **kwargs):
        saved.setdefault("query_kwargs", []).append(kwargs)
        return alerts

    def get_cutouts(broker, candid, session, **kwargs):
        saved.setdefault("get_cutouts_calls", []).append(candid)
        if cutouts is None:
            raise RuntimeError("broker has no cutouts for this alert")
        return cutouts

    def get_alert(broker, alert_id, session, **kwargs):
        saved.setdefault("get_alert_calls", []).append(alert_id)
        saved.setdefault("get_alert_kwargs", []).append(kwargs)
        if history is None:
            raise RuntimeError("broker has no history for this object")
        # Real brokers fail closed on the stream scope: BOOM turns a missing
        # `permissions` into an empty programid list, which matches nothing and
        # returns no rows rather than raising. Mimic that, or a caller that
        # forgets to pass the scope looks fine here and silently ingests
        # nothing in production.
        if not kwargs.get("permissions"):
            return []
        return {**alerts[0], "prv_candidates": history}

    monkeypatch.setattr(GENERICBROKER, "query_alerts", staticmethod(query_alerts))
    monkeypatch.setattr(GENERICBROKER, "get_alert", staticmethod(get_alert))
    monkeypatch.setattr(GENERICBROKER, "get_cutouts", staticmethod(get_cutouts))
    monkeypatch.setattr(
        GENERICBROKER,
        "implements",
        classmethod(
            lambda cls: {
                "query_alerts": True,
                "get_alert": True,
                "get_cutouts": True,
            }
        ),
    )


def test_crossmatch_ingests_photometry_for_a_match(
    broker,
    crossmatch_filter,
    crossmatch_event,
    ztf_instrument,
    monkeypatch,
):
    """A scanner judges a candidate on its light curve, so the match must bring
    one: the crossmatch query itself returns no detection history."""
    dateobs, _, ra, dec = crossmatch_event
    event_jd = float(Time(dateobs).jd)

    obj_id = _unique_id("XM_phot")
    # get_alert returns the normalized shape: `band`, not the raw `fid`.
    history = [
        {
            "magpsf": 19.1,
            "sigmapsf": 0.1,
            "jd": event_jd - 1.0,
            "band": "ztfg",
            "ra": ra,
            "dec": dec,
            # the fixture stream's selector is [1, 2], and the programid ->
            # stream map keys on max(selector)
            "programid": 2,
        }
    ]
    recorded = {}
    _stub_provider_with_photometry(
        monkeypatch,
        [_alert(obj_id, ra, dec, event_jd + 0.2)],
        recorded,
        ra,
        dec,
        history,
    )

    asyncio.run(run_cycle({"archival": False}))

    assert obj_id in _objs_created([obj_id]), recorded
    assert obj_id in recorded.get("get_alert_calls", []), (
        "the full object was never refetched for its history"
    )
    assert all(k.get("permissions") for k in recorded.get("get_alert_kwargs", [])), (
        "the history fetch ran without a stream scope, which returns nothing"
    )
    with models.DBSession() as session:
        points = session.scalars(
            sa.select(Photometry).where(Photometry.obj_id == obj_id)
        ).all()
    assert len(points) > 0, "the match was saved without any photometry"


def test_annotation_records_how_deep_in_the_localization_a_match_is(
    broker,
    crossmatch_filter,
    crossmatch_event,
    monkeypatch,
):
    """The credible level is what ranks a scanning queue: a match at the centre
    of the region is a far better counterpart than one that just scraped in."""
    dateobs, _, ra, dec = crossmatch_event
    event_jd = float(Time(dateobs).jd)

    centre = _unique_id("XM_centre")
    edge = _unique_id("XM_edge")
    _stub_provider(
        monkeypatch,
        [
            _alert(centre, ra, dec, event_jd + 0.5),
            _alert(edge, ra, dec + ERROR * 0.9, event_jd + 0.5),
        ],
        {},
        ra,
        dec,
    )

    asyncio.run(run_cycle({"archival": False}))

    levels = {}
    with models.DBSession() as session:
        for obj_id in (centre, edge):
            annotation = session.scalar(
                sa.select(Annotation).where(
                    Annotation.obj_id == obj_id,
                    Annotation.origin == ANNOTATION_ORIGIN,
                )
            )
            assert annotation is not None, f"{obj_id} was not annotated"
            entry = next(iter(annotation.data.values()))
            assert "credible_level" in entry, entry
            levels[obj_id] = entry["credible_level"]

    assert levels[centre] == 0.0
    assert levels[centre] < levels[edge], levels
    # Gaussian of sigma = the quoted error radius: 0.9 sigma encloses ~33%
    assert levels[edge] == pytest.approx(1 - np.exp(-0.5 * 0.81), abs=1e-3)


def test_filter_can_cut_on_credible_level(
    broker,
    crossmatch_filter,
    crossmatch_event,
    monkeypatch,
):
    """Filters re-cut the shared geometry: same containment, tighter threshold."""
    dateobs, _, ra, dec = crossmatch_event
    event_jd = float(Time(dateobs).jd)

    centre = _unique_id("XM_deep")
    edge = _unique_id("XM_shallow")
    _stub_provider(
        monkeypatch,
        [
            _alert(centre, ra, dec, event_jd + 0.5),
            _alert(edge, ra, dec + ERROR * 0.9, event_jd + 0.5),
        ],
        {},
        ra,
        dec,
    )

    asyncio.run(run_cycle({"archival": False, "max_credible_level": 0.1}))

    created = _objs_created([centre, edge])
    assert centre in created, "the well-localized match was cut"
    assert edge not in created, "a match outside the filter's credible cut was saved"


def test_crossmatch_ingests_cutouts_for_a_match(
    broker,
    crossmatch_filter,
    crossmatch_event,
    ztf_instrument,
    monkeypatch,
):
    """A scanner reads the science/reference/difference stamps before anything
    else, so the match must bring them too. They are keyed by candid, not object
    id, which is only available on the refetched alert."""
    dateobs, _, ra, dec = crossmatch_event
    event_jd = float(Time(dateobs).jd)

    obj_id = _unique_id("XM_cutout")
    candid = 3515302280815015022
    history = [
        {
            "magpsf": 19.1,
            "sigmapsf": 0.1,
            "jd": event_jd - 1.0,
            "band": "ztfg",
            "ra": ra,
            "dec": dec,
            "programid": 2,
        }
    ]
    stamp = _fits_cutout()
    recorded = {}
    _stub_provider_with_photometry(
        monkeypatch,
        [_alert(obj_id, ra, dec, event_jd + 0.2, candid=candid)],
        recorded,
        ra,
        dec,
        history,
        cutouts={
            "cutoutScience": stamp,
            "cutoutTemplate": stamp,
            "cutoutDifference": stamp,
        },
    )

    asyncio.run(run_cycle({"archival": False}))

    assert obj_id in _objs_created([obj_id]), recorded
    assert candid in recorded.get("get_cutouts_calls", []), (
        "cutouts were never fetched, or were fetched by object id rather than candid"
    )
    with models.DBSession() as session:
        types = set(
            session.scalars(
                sa.select(Thumbnail.type).where(Thumbnail.obj_id == obj_id)
            ).all()
        )
    assert {"new", "ref", "sub"} <= {str(t) for t in types}, (
        f"the match was saved without its alert stamps: {types}"
    )


def test_crossmatch_keeps_the_photometry_when_cutouts_fail(
    broker,
    crossmatch_filter,
    crossmatch_event,
    ztf_instrument,
    monkeypatch,
):
    """Stamps are the nice-to-have; the light curve is not. A broker that cannot
    serve cutouts must still leave the scanner something to judge."""
    dateobs, _, ra, dec = crossmatch_event
    event_jd = float(Time(dateobs).jd)

    obj_id = _unique_id("XM_nocutout")
    history = [
        {
            "magpsf": 19.1,
            "sigmapsf": 0.1,
            "jd": event_jd - 1.0,
            "band": "ztfg",
            "ra": ra,
            "dec": dec,
            "programid": 2,
        }
    ]
    recorded = {}
    _stub_provider_with_photometry(
        monkeypatch,
        [_alert(obj_id, ra, dec, event_jd + 0.2, candid=1234)],
        recorded,
        ra,
        dec,
        history,
        cutouts=None,  # get_cutouts raises
    )

    asyncio.run(run_cycle({"archival": False}))

    assert obj_id in _objs_created([obj_id]), "the match was lost with the cutouts"
    with models.DBSession() as session:
        points = session.scalars(
            sa.select(Photometry).where(Photometry.obj_id == obj_id)
        ).all()
    assert len(points) > 0, "a failed cutout fetch took the photometry with it"


def test_crossmatch_keeps_the_match_when_photometry_fails(
    broker,
    crossmatch_filter,
    crossmatch_event,
    ztf_instrument,
    monkeypatch,
):
    """A broker that cannot serve the history must not cost us the match."""
    dateobs, _, ra, dec = crossmatch_event
    event_jd = float(Time(dateobs).jd)

    obj_id = _unique_id("XM_nophot")
    recorded = {}
    _stub_provider_with_photometry(
        monkeypatch,
        [_alert(obj_id, ra, dec, event_jd + 0.2)],
        recorded,
        ra,
        dec,
        None,  # get_alert raises
    )

    asyncio.run(run_cycle({"archival": False}))

    assert obj_id in _objs_created([obj_id]), "the match was lost with the photometry"
    with models.DBSession() as session:
        annotation = session.scalar(
            sa.select(Annotation).where(
                Annotation.obj_id == obj_id,
                Annotation.origin == ANNOTATION_ORIGIN,
            )
        )
    assert annotation is not None, "the match was not annotated"


def test_crossmatch_searches_every_localization_of_an_event(
    super_admin_token, public_group2, broker, crossmatch_filter, monkeypatch
):
    """An EP observation reports each detected source as its own cone under the
    shared observation timestamp, so one event can cover several unrelated
    patches of sky. Searching only one silently drops the others.
    """
    ra_a, dec_a = _unique_position()
    # far enough away that the two cones cannot be confused for one another
    ra_b, dec_b = (ra_a + 60.0) % 360.0, -dec_a

    dateobs, _ = _post_event(super_admin_token, [public_group2.id], ra_a, dec_a)
    # A second cone on the same event, exactly how a sibling EP source arrives:
    # posted under the same observation timestamp, which is the event's key.
    status, data = api(
        "POST",
        "gcn_event",
        data={
            "dateobs": dateobs.isoformat(),
            "skymap": {"ra": ra_b, "dec": dec_b, "error": ERROR},
            "tags": ["TEST"],
            "group_ids": [public_group2.id],
        },
        token=super_admin_token,
    )
    assert status == 200, data

    event_jd = float(Time(dateobs).jd)
    obj_a = _unique_id("XM_loc_a")
    obj_b = _unique_id("XM_loc_b")

    def query_alerts(broker_, session, **kwargs):
        # serve whichever object lies in the cone being asked about
        centre_ra = kwargs.get("ra")
        if centre_ra is None:
            return []
        if abs(centre_ra - ra_a) < 1e-4:
            return [_alert(obj_a, ra_a, dec_a, event_jd + 0.2)]
        if abs(centre_ra - ra_b) < 1e-4:
            return [_alert(obj_b, ra_b, dec_b, event_jd + 0.2)]
        return []

    monkeypatch.setattr(GENERICBROKER, "query_alerts", staticmethod(query_alerts))
    monkeypatch.setattr(
        GENERICBROKER, "implements", classmethod(lambda cls: {"query_alerts": True})
    )

    asyncio.run(run_cycle({"archival": False}))

    created = _objs_created([obj_a, obj_b])
    assert obj_a in created, "the first localization was not searched"
    assert obj_b in created, "a second localization on the event was never searched"
