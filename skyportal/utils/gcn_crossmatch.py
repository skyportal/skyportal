"""Crossmatch broker alerts against active GCN localizations.

For every GCN event still inside its active window, ask each configured broker
for alerts near the event's localization, keep the ones genuinely inside the
credible region, save them as sources, and annotate them with how they relate to
the event (time offset, angular separation).

This replaces the standalone ep-ztf-xmatch service, which did the same for
Einstein Probe against Kowalski only. Nothing here is EP-specific: it works for
any GcnEvent whose localization can be bounded and any broker implementing
``query_alerts`` (BOOM, Babamul, ALeRCE, Fink, Lasair, ...).

Two invariants matter and are easy to get wrong:

* Sources and annotations inherit the *event's* groups. A restricted event's
  matches must not be visible to people who cannot see the event, or the
  association leaks what the group restriction exists to protect.
* The broker is queried with a bounding cone, which over-selects; membership is
  then decided by an exact containment check. The cone is never the answer.

The logic lives here rather than in the service module so it can be imported and
tested without the service's ``init_db`` side effect rebinding the session.
Configuration is passed in explicitly for the same reason.
"""

import json
import math
import traceback
from datetime import timedelta

import sqlalchemy as sa
from astropy.time import Time
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from baselayer.app import models
from baselayer.log import make_log
from skyportal.broker_apis.interface import survey_permissions
from skyportal.models import (
    Annotation,
    Broker,
    Filter,
    GcnEvent,
    GcnEventCrossmatchState,
    Group,
    User,
)
from skyportal.utils.crossmatch import (
    DEFAULT_CUMPROB,
    contained_in_localization,
    great_circle_distance,
    search_cone,
)
from skyportal.utils.naive_datetime import utcnow_naive

log = make_log("gcn_crossmatch")

DEFAULTS = {
    "max_event_age": 31.0,
    "recheck_interval_minutes": 10.0,
    "delta_t_before": 1.0,
    "delta_t_after": 31.0,
    "max_radius_deg": 5.0,
    "credible_level": 90,
    "cumprob": DEFAULT_CUMPROB,
    # SkyPortal Filter whose broker-side pipeline holds the quality cuts; None
    # falls back to the built-in ZTF cuts ported from ep-ztf-xmatch.
    "filter_id": None,
    "survey": "ZTF",
    "max_alerts": 500,
    # One-shot search of the window before the event, to spot positions that
    # were already active and so cannot be counterparts.
    "archival": True,
    "archival_days": 31.0,
}

ANNOTATION_ORIGIN = "GCN-crossmatch"


def conf(config, key):
    """Read a crossmatch setting, falling back to the documented default."""
    return (config or {}).get(key, DEFAULTS[key])


def alert_position(alert):
    """(ra, dec) for a broker alert, tolerating the common payload shapes."""
    for container in (alert, alert.get("candidate") or {}):
        if not isinstance(container, dict):
            continue
        ra, dec = container.get("ra"), container.get("dec")
        if ra is not None and dec is not None:
            return float(ra), float(dec)

    # BOOM's raw alert documents carry the position only as GeoJSON, with
    # longitude shifted into [-180, 180]; pipeline results are raw documents,
    # unlike cone_search results which are decorated with ra/dec.
    coords = ((alert.get("coordinates") or {}).get("radec_geojson") or {}).get(
        "coordinates"
    )
    if isinstance(coords, (list, tuple)) and len(coords) == 2:
        return float(coords[0]) + 180.0, float(coords[1])
    return None


def alert_jd(alert):
    """Detection JD for a broker alert, or None."""
    for container in (alert, alert.get("candidate") or {}):
        if not isinstance(container, dict):
            continue
        for key in ("jd", "mjd"):
            value = container.get(key)
            if value is not None:
                return float(value) + (2400000.5 if key == "mjd" else 0.0)
    return None


def alert_object_id(alert):
    for key in ("objectId", "object_id", "objectid", "oid"):
        value = alert.get(key)
        if value:
            return str(value)
    return None


# Alert fields carried onto the annotation, as (annotation key, candidate key).
ALERT_ANNOTATION_FIELDS = (
    ("drb", "drb"),
    ("sgscore", "sgscore1"),
    ("distpsnr", "distpsnr1"),
    ("ssdistnr", "ssdistnr"),
    ("ssmagnr", "ssmagnr"),
    ("ndethist", "ndethist"),
)


def _candidate(alert):
    candidate = alert.get("candidate")
    return candidate if isinstance(candidate, dict) else {}


def build_annotation_data(event_jd, ra0, dec0, radius_deg, alert, archival=False):
    """Event-relative and alert-quality values for one matched alert.

    Mirrors ep_fritz.py's annotation, so the same columns are available for
    sorting. Its ``ep_mjd`` is ``event_mjd`` here, nothing being EP-specific.
    """
    data = {}
    jd = alert_jd(alert)
    if jd is not None and event_jd is not None:
        data["delta_t"] = round(jd - event_jd, 4)

    position = alert_position(alert)
    if position is not None:
        separation = float(great_circle_distance(ra0, dec0, *position))
        data["distance_arcmin"] = round(separation * 60.0, 4)
        if radius_deg:
            data["distance_ratio"] = round(separation / radius_deg, 4)

    candidate = _candidate(alert)
    for key, source in ALERT_ANNOTATION_FIELDS:
        value = candidate.get(source)
        if value is not None:
            data[key] = round(value, 4) if isinstance(value, float) else value

    # days since the object's first detection: separates a months-old variable
    # from a genuinely new transient
    jdstarthist = candidate.get("jdstarthist")
    if jd is not None and jdstarthist is not None:
        data["age"] = round(jd - float(jdstarthist), 4)

    if event_jd is not None:
        data["event_mjd"] = round(event_jd - 2400000.5, 6)

    # An archival match means the position was already active before the event,
    # so it cannot be a counterpart. Recorded as its own flag rather than as the
    # window this entry came from, because the annotation is keyed per event: a
    # later contemporaneous match would otherwise overwrite the very fact that
    # rules the candidate out.
    if archival:
        data["prior_activity"] = True
    return data


async def annotate_match(
    session, user, obj_id, event_key, event_dateobs, group_ids, data
):
    """Attach (or refresh) this event's entry on an object's crossmatch annotation.

    One object can fall inside several events' localizations, so the annotation
    is keyed by event name within a single origin rather than one annotation per
    event -- the same shape ep_fritz.py used.
    """
    if not data:
        return

    annotation = await session.scalar(
        Annotation.select(user, mode="update").where(
            Annotation.obj_id == obj_id, Annotation.origin == ANNOTATION_ORIGIN
        )
    )
    payload = dict(data)
    payload["dateobs"] = event_dateobs.isoformat()

    if annotation is None:
        annotation = Annotation(
            obj_id=obj_id,
            origin=ANNOTATION_ORIGIN,
            data={event_key: payload},
            author_id=user.id,
        )
        annotation.groups = (
            await session.scalars(sa.select(Group).where(Group.id.in_(group_ids)))
        ).all()
        session.add(annotation)
    else:
        merged = dict(annotation.data or {})
        if (merged.get(event_key) or {}).get("prior_activity"):
            payload["prior_activity"] = True
        merged[event_key] = payload
        annotation.data = merged
        flag_modified(annotation, "data")


async def process_event_broker(
    session, user, event, localization, broker, state, config=None, archival=False
):
    """Query one broker for one event and save whatever genuinely matches.

    ``archival`` searches the window *before* the event instead of around it.
    Those alerts cannot have been caused by the event, so they exist to rule a
    candidate out: a position already flaring last month is a variable, not a
    counterpart.
    """
    cone = search_cone(
        localization,
        max_radius_deg=float(conf(config, "max_radius_deg")),
        credible_level=int(conf(config, "credible_level")),
    )
    if cone is None:
        state.status = "skipped"
        state.last_queried = utcnow_naive()
        return 0

    ra0, dec0, radius = cone
    event_jd = float(Time(event.dateobs).jd)

    if archival:
        # A one-shot look back; nothing new appears in a window that has closed.
        jd_end = event_jd - float(conf(config, "delta_t_before"))
        jd_start = jd_end - float(conf(config, "archival_days"))
    else:
        # Lower bound: resume from the newest alert already seen rather than from
        # wall-clock, because brokers make alerts queryable some time after the
        # alert's own JD. Anchoring on wall-clock would step over that lag and
        # silently lose late-arriving alerts.
        jd_start = event_jd - float(conf(config, "delta_t_before"))
        if state.last_alert_jd is not None:
            jd_start = max(jd_start, state.last_alert_jd)
        jd_end = event_jd + float(conf(config, "delta_t_after"))

    # Only offer the broker the alert programs the event's own groups are
    # entitled to, so the crossmatch cannot pull in data the audience for this
    # event could not otherwise see.
    streams = []
    for group in event.groups:
        streams.extend(group.streams or [])
    permissions = survey_permissions(streams)

    implements = broker.broker_class.implements()
    survey = conf(config, "survey")

    if implements.get("test_filter"):
        # Preferred path: run the quality cuts as a broker-side filter pipeline,
        # with the cone prepended as a spatial stage. This keeps the cuts in the
        # same versioned, editable place as every other broker filter, and means
        # artifacts, asteroids and variable stars are rejected before they cross
        # the wire rather than after.
        cuts, cuts_source = await resolve_quality_pipeline(
            session, broker, conf(config, "filter_id")
        )
        result = broker.broker_class.test_filter(
            broker,
            session,
            pipeline=[cone_match_stage(ra0, dec0, radius), *cuts],
            survey=survey,
            permissions=permissions,
            start_jd=jd_start,
            end_jd=jd_end,
            sort_by="candidate.jd",
            sort_order="Descending",
            limit=int(conf(config, "max_alerts")),
        )
        alerts = (
            result.get("results", []) if isinstance(result, dict) else (result or [])
        )
        log(
            f"{broker.name}: {len(alerts)} alert(s) for {event.dateobs} "
            f"using {cuts_source}"
        )
    else:
        # Fallback for providers with no filter support: an unfiltered positional
        # query. Correct, but noisier -- nothing rejects artifacts or asteroids.
        alerts = (
            broker.broker_class.query_alerts(
                broker,
                session,
                ra=ra0,
                dec=dec0,
                radius=radius,
                radius_units="deg",
                jd_start=jd_start,
                jd_end=jd_end,
                permissions=permissions,
            )
            or []
        )

    # Honouring jd_start/jd_end is best-effort per the BrokerAPI contract (BOOM
    # pushes it into its Mongo filter; a provider whose backend cannot express it
    # may ignore it), so the window is re-checked here. Skipping this check would
    # let an unbounded provider match alerts years from the event and annotate
    # them with a delta_t to match -- a failure that reads as data, not as a bug.
    positions, keep = [], []
    undated = 0
    for alert in alerts:
        position = alert_position(alert)
        object_id = alert_object_id(alert)
        if position is None or object_id is None:
            continue
        jd = alert_jd(alert)
        if jd is None:
            # Without a JD the alert cannot be placed relative to the event, and
            # keeping it would assert a temporal association we cannot check.
            undated += 1
            continue
        if not (jd_start <= jd <= jd_end):
            continue
        positions.append(position)
        keep.append(alert)

    if undated:
        log(
            f"{broker.name}: dropped {undated} alert(s) with no JD near "
            f"{event.dateobs} (cannot place them in the event window)"
        )

    inside = await contained_in_localization(
        session,
        localization,
        positions,
        cumprob=float(conf(config, "cumprob")),
    )

    group_ids = [g.id for g in event.groups]
    newest_jd = state.last_alert_jd
    matched = 0

    # Everything the loop needs is captured as plain values first. save_as_source
    # commits, and a commit expires every ORM object in the session -- touching
    # event.dateobs or state.* afterwards would trigger a lazy refresh, which in
    # an async session raises MissingGreenlet rather than reloading.
    event_key = str(event.trigger_id or event.dateobs)
    event_dateobs = event.dateobs
    state_id = state.id

    for index in sorted(inside):
        alert = keep[index]
        object_id = alert_object_id(alert)
        try:
            await broker.broker_class.save_as_source(
                broker,
                object_id,
                session,
                user,
                group_ids,
                permissions=permissions,
            )
            await annotate_match(
                session,
                user,
                object_id,
                event_key,
                event_dateobs,
                group_ids,
                build_annotation_data(
                    event_jd, ra0, dec0, radius, alert, archival=archival
                ),
            )
            await session.commit()
            matched += 1
        except Exception as e:
            await session.rollback()
            log(f"Failed to save {object_id} for {event_dateobs}: {e}")
            continue

        jd = alert_jd(alert)
        if jd is not None and (newest_jd is None or jd > newest_jd):
            newest_jd = jd

    # Re-fetch rather than reuse the (possibly expired) instance for the same
    # reason.
    state = await session.get(GcnEventCrossmatchState, state_id)
    if state is not None:
        if archival:
            state.archival_done = True
        else:
            state.last_alert_jd = newest_jd
        state.last_queried = utcnow_naive()
        state.status = "done"
        state.error = None
        state.n_matches = (state.n_matches or 0) + matched
    return matched


async def run_cycle(config=None, user_id=1):
    """One pass over every due (event, broker) pair."""
    max_age = float(conf(config, "max_event_age"))
    recheck_minutes = float(conf(config, "recheck_interval_minutes"))
    now = utcnow_naive()
    cutoff = now - timedelta(days=max_age)
    stale_before = now - timedelta(minutes=recheck_minutes)

    total = 0
    async with models.async_plain_session_factory() as session:
        user = await session.scalar(sa.select(User).where(User.id == user_id))
        if user is None:
            log(f"User {user_id} not found in DB, cannot crossmatch")
            return 0
        session.user_or_token = user

        brokers = (
            (await session.scalars(sa.select(Broker).where(Broker.active.is_(True))))
            .unique()
            .all()
        )
        brokers = [
            b for b in brokers if b.broker_class.implements().get("query_alerts")
        ]
        if not brokers:
            return 0

        events = (
            (
                await session.scalars(
                    sa.select(GcnEvent)
                    .where(GcnEvent.dateobs >= cutoff)
                    .options(
                        selectinload(GcnEvent.groups).selectinload(Group.streams),
                        selectinload(GcnEvent.localizations),
                    )
                )
            )
            .unique()
            .all()
        )

        for event in events:
            if not event.localizations:
                continue
            localization = sorted(
                event.localizations, key=lambda loc: loc.created_at, reverse=True
            )[0]

            for broker in brokers:
                state = await session.scalar(
                    sa.select(GcnEventCrossmatchState).where(
                        GcnEventCrossmatchState.gcnevent_id == event.id,
                        GcnEventCrossmatchState.broker_id == broker.id,
                    )
                )
                if state is None:
                    state = GcnEventCrossmatchState(
                        gcnevent_id=event.id, broker_id=broker.id, status="pending"
                    )
                    session.add(state)
                    await session.commit()
                elif (
                    state.last_queried is not None and state.last_queried > stale_before
                ):
                    continue
                elif state.status == "skipped":
                    continue

                try:
                    # The pre-event window is searched once, before the first
                    # forward pass, so a candidate that was already active is
                    # flagged as such the first time anyone looks at it.
                    if conf(config, "archival") and not state.archival_done:
                        total += await process_event_broker(
                            session,
                            user,
                            event,
                            localization,
                            broker,
                            state,
                            config,
                            archival=True,
                        )
                        await session.commit()
                        state = await session.get(GcnEventCrossmatchState, state.id)

                    total += await process_event_broker(
                        session, user, event, localization, broker, state, config
                    )
                except Exception as e:
                    traceback.print_exc()
                    state.status = "failed"
                    state.error = str(e)[:500]
                    state.last_queried = utcnow_naive()
                    log(f"Crossmatch failed for {event.dateobs} / {broker.name}: {e}")
                await session.commit()

    return total


# ---------------------------------------------------------------------------
# Alert quality cuts
# ---------------------------------------------------------------------------

# Ported verbatim from ep-ztf-xmatch's Kowalski query (ep_xmatch.py) and its
# is_red_star() helper. Without cuts like these, every artifact, asteroid and
# variable star inside the error region is reported as a match, which is what
# made that service usable rather than noise.
#
# These are a starting point, not a policy: the intended production setup is to
# register them as a BOOM filter and point ``gcn_crossmatch.filter_id`` at the
# SkyPortal Filter wrapping it, so the cuts are versioned and editable in the
# filter builder instead of frozen here.
ZTF_QUALITY_CUTS = [
    {
        "$match": {
            # real/bogus: random-forest and deep-learning scores
            "candidate.rb": {"$gt": 0.3},
            "candidate.drb": {"$gt": 0.5},
            # positive-subtraction detections only
            "candidate.isdiffpos": {"$in": ["t", "T", "true", "True", True, "1", 1]},
            "$and": [
                {
                    # not a known solar-system object
                    "$or": [
                        {"candidate.ssdistnr": {"$lt": 0}},
                        {"candidate.ssdistnr": {"$gte": 12}},
                        {"candidate.ssmagnr": {"$lt": 0}},
                        {"candidate.ssmagnr": {"$gte": 21}},
                    ]
                },
                {
                    # not coincident with a PS1 point source
                    "$or": [
                        {"candidate.sgscore1": {"$lt": 0.7}},
                        {"candidate.distpsnr1": {"$gt": 2}},
                        {"candidate.distpsnr1": {"$lt": 0}},
                    ]
                },
                {
                    # not a red stellar contaminant: a close, star-like PS1
                    # counterpart with a very red colour in any band pair
                    "$nor": [
                        {
                            "$and": [
                                {"candidate.distpsnr1": {"$gte": 0, "$lte": 1.0}},
                                {"candidate.sgscore1": {"$gt": 0.2}},
                                {
                                    "$or": [
                                        {
                                            "$expr": {
                                                "$and": [
                                                    {"$gt": [f"$candidate.{a}", 0]},
                                                    {"$gt": [f"$candidate.{b}", 0]},
                                                    {
                                                        "$gt": [
                                                            {
                                                                "$subtract": [
                                                                    f"$candidate.{a}",
                                                                    f"$candidate.{b}",
                                                                ]
                                                            },
                                                            3,
                                                        ]
                                                    },
                                                ]
                                            }
                                        }
                                        for a, b in (
                                            ("srmag1", "simag1"),
                                            ("srmag1", "szmag1"),
                                            ("simag1", "szmag1"),
                                        )
                                    ]
                                },
                            ]
                        }
                    ]
                },
            ],
        }
    }
]


def cone_match_stage(ra, dec, radius_deg):
    """A pipeline stage restricting alerts to a cone.

    BOOM stores positions as GeoJSON with longitude shifted into [-180, 180]
    (see the +180 correction when reading cone_search results back), so the
    centre longitude is ``ra - 180``.
    """
    return {
        "$match": {
            "coordinates.radec_geojson": {
                "$geoWithin": {
                    "$centerSphere": [
                        [float(ra) - 180.0, float(dec)],
                        math.radians(float(radius_deg)),
                    ]
                }
            }
        }
    }


async def resolve_quality_pipeline(session, broker, filter_id):
    """The pipeline stages to apply as quality cuts, and where they came from.

    A configured SkyPortal Filter wins: its ``altdata["boom"]["filter_id"]``
    names a broker-side filter whose active version holds the pipeline, so the
    cuts stay versioned and editable in the filter builder. Falling back to the
    built-in cuts keeps the crossmatch usable before anyone has set one up.
    """
    if filter_id is None:
        return ZTF_QUALITY_CUTS, "built-in ZTF cuts"

    f = await session.scalar(sa.select(Filter).where(Filter.id == int(filter_id)))
    if f is None:
        log(f"Filter {filter_id} not found; falling back to the built-in cuts")
        return ZTF_QUALITY_CUTS, "built-in ZTF cuts (filter not found)"

    boom_filter_id = ((f.altdata or {}).get("boom") or {}).get("filter_id")
    if boom_filter_id is None:
        log(
            f"Filter {filter_id} has no altdata['boom']['filter_id']; "
            f"falling back to the built-in cuts"
        )
        return ZTF_QUALITY_CUTS, "built-in ZTF cuts (no broker filter)"

    try:
        remote = broker.broker_class.get_filters(
            broker, session, boom_filter_id=boom_filter_id
        )
    except Exception as e:
        log(f"Could not fetch broker filter {boom_filter_id}: {e}")
        return ZTF_QUALITY_CUTS, "built-in ZTF cuts (broker fetch failed)"

    return _pipeline_from_broker_filter(remote, boom_filter_id)


def _pipeline_from_broker_filter(remote, boom_filter_id):
    """Pull the active version's stages out of a broker filter record.

    BOOM returns versions under ``fv`` keyed by ``fid``, with ``active_fid``
    naming the live one, and each ``pipeline`` serialized as a JSON string.
    """
    if not isinstance(remote, dict):
        return ZTF_QUALITY_CUTS, "built-in ZTF cuts (unexpected filter payload)"

    versions = remote.get("fv") or []
    active_fid = remote.get("active_fid")
    version = next(
        (v for v in versions if v.get("fid") == active_fid),
        versions[0] if versions else None,
    )
    if version is None:
        return ZTF_QUALITY_CUTS, "built-in ZTF cuts (filter has no versions)"

    pipeline = version.get("pipeline")
    if isinstance(pipeline, str):
        try:
            pipeline = json.loads(pipeline)
        except ValueError:
            return ZTF_QUALITY_CUTS, "built-in ZTF cuts (unparseable pipeline)"
    if not isinstance(pipeline, list):
        return ZTF_QUALITY_CUTS, "built-in ZTF cuts (pipeline is not a list)"

    return pipeline, f"broker filter {boom_filter_id} version {version.get('fid')}"
