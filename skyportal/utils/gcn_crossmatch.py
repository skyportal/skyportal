"""Crossmatch broker alerts against active GCN localizations.

For every GCN event still inside its active window, ask each configured broker
for alerts near the event's localization, keep the ones genuinely inside the
credible region, raise them as candidates to scan, and annotate them with how
they relate to the event (time offset, angular separation).

A match is a suggestion, not a conclusion, so nothing is saved as a Source: the
candidate appears on the scanning page and becomes a Source only when a human
saves it.

This replaces the standalone ep-ztf-xmatch service, which did the same for
Einstein Probe against Kowalski only. Nothing here is EP-specific: it works for
any GcnEvent whose localization can be bounded and any broker implementing
``query_alerts`` (BOOM, Babamul, ALeRCE, Fink, Lasair, ...).

Two invariants matter and are easy to get wrong:

* Annotations inherit the *event's* groups, so the link between an object and a
  restricted event stays as restricted as the event. Note the Candidate itself
  is visible to the configured filter's group, so point ``filter_id`` at a
  filter whose group matches the audience for the events being crossmatched.
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

import healpy
import numpy as np
import sqlalchemy as sa
from astropy.time import Time
from sqlalchemy.orm import selectinload, undefer
from sqlalchemy.orm.attributes import flag_modified

from baselayer.app import models
from baselayer.log import make_log
from skyportal.broker_apis._save import save_object_photometry
from skyportal.broker_apis.interface import survey_permissions
from skyportal.models import (
    Annotation,
    Broker,
    Candidate,
    Filter,
    GcnEvent,
    GcnEventCrossmatchState,
    GcnEventObj,
    Group,
    Localization,
    Obj,
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
    "recheck_interval_minutes": 60.0,
    "delta_t_before": 1.0,
    "delta_t_after": 31.0,
    "max_radius_deg": 5.0,
    "credible_level": 90,
    "cumprob": DEFAULT_CUMPROB,
    "max_alerts": 500,
    # One-shot search of the window before the event, to spot positions that
    # were already active and so cannot be counterparts.
    "archival": True,
    "archival_days": 31.0,
    # How long to leave a broker alone after it answers 429. Lasair's quota is
    # hourly, so anything shorter just spends the next window's allowance.
    "rate_limit_backoff_minutes": 60.0,
}

ANNOTATION_ORIGIN = "GCN-crossmatch"

# Brokers rate-limit per account, not per query, so a 429 means every later call
# this window fails too -- and the quota is shared with the rest of the app, so
# retrying also starves interactive users. Park the whole broker rather than
# burning the remaining allowance one event at a time. Held in memory: a restart
# retrying once is harmless, and it keeps this off the state table.
_rate_limited_until: dict = {}


# Filter configuration changes rarely, so reporting it every cycle is noise --
# but never reporting it hides a misconfiguration. Log only when it changes.
_last_filter_report: dict = {}


def report_once(key, message):
    """Log `message` only when it differs from the last one for `key`."""
    if _last_filter_report.get(key) == message:
        return
    _last_filter_report[key] = message
    log(message)


def rate_limited_until(broker_id):
    """When this broker's backoff expires, or None if it is not backed off."""
    until = _rate_limited_until.get(broker_id)
    if until is None:
        return None
    if utcnow_naive() >= until:
        del _rate_limited_until[broker_id]
        return None
    return until


def note_rate_limited(broker_id, minutes):
    until = utcnow_naive() + timedelta(minutes=float(minutes))
    _rate_limited_until[broker_id] = until
    return until


def is_rate_limited(error):
    """True for a broker refusing on quota (HTTP 429)."""
    return getattr(getattr(error, "response", None), "status_code", None) == 429


def conf(config, key):
    """Read a crossmatch setting, falling back to the documented default."""
    return (config or {}).get(key, DEFAULTS[key])


CROSSMATCH_ALTDATA_KEY = "gcn_crossmatch"


def filter_settings(filter_, config):
    """Crossmatch settings for one filter: global config, then its overrides.

    A filter is the unit of configuration -- it already names a broker, a stream
    (hence survey and programids) and the group that sees the candidates -- so
    per-survey differences (LSST's cadence and depth are not ZTF's) belong here
    rather than in one global block.
    """
    overrides = (filter_.altdata or {}).get(CROSSMATCH_ALTDATA_KEY) or {}
    merged = dict(config or {})
    merged.update({k: v for k, v in overrides.items() if k != "enabled"})
    return merged


def crossmatch_enabled(filter_):
    return bool(
        ((filter_.altdata or {}).get(CROSSMATCH_ALTDATA_KEY) or {}).get("enabled")
    )


def event_matches(filter_, event, localization):
    """Whether this filter should be run against this event.

    Uses the same ``filters`` shape as DefaultGcnTag and the default
    observation-plan/follow-up requests: an absent or empty list means "no
    restriction", otherwise the event must match at least one listed value.
    Lets one filter serve only EP events while another serves GRBs.
    """
    filters = ((filter_.altdata or {}).get(CROSSMATCH_ALTDATA_KEY) or {}).get(
        "filters"
    ) or {}

    wanted = filters.get("gcn_tags") or []
    if wanted and not any(tag in (event.tags or []) for tag in wanted):
        return False

    wanted = filters.get("localization_tags") or []
    if wanted:
        tags = [t.text for t in (localization.tags or [])]
        if not any(tag in tags for tag in wanted):
            return False

    return True


def filter_survey(filter_):
    """Survey a filter covers, from its stream's collection (ZTF_alerts -> ZTF)."""
    collection = ((filter_.stream.altdata or {}) if filter_.stream else {}).get(
        "collection"
    )
    return str(collection).split("_")[0].upper() if collection else None


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


def build_annotation_data(
    event_jd, ra0, dec0, radius_deg, alert, archival=False, distance_at=None
):
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

    # For a 3D (GW) skymap, what distance the event implies *here*. Recorded
    # rather than cut on: an alert rarely has a host redshift at discovery, so
    # this is for a scanner to compare against once one is known.
    if distance_at is not None and position is not None:
        distance = distance_at(*position)
        if distance is not None:
            data["dist_mean"], data["dist_std"] = (
                round(distance[0], 2),
                round(distance[1], 2),
            )

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


async def ensure_candidate(session, user, alert, obj_id, filter_id, survey=None):
    """Create the Obj (if new) and a Candidate for it, without saving a Source.

    A match is something for a human to scan, not something already accepted:
    the Obj and Candidate make it appear on the scanning page, and it only
    becomes a Source once someone saves it. Photometry is ingested separately
    (see ``ingest_match_photometry``) -- a light curve is what a scanner judges
    the candidate on, and it implies no acceptance.

    Returns True if a candidate now exists for this (obj, filter, epoch).
    """
    candidate = _candidate(alert)
    position = alert_position(alert)

    obj = await session.scalar(sa.select(Obj).where(Obj.id == obj_id))
    if obj is None:
        if position is None:
            log(f"Cannot create {obj_id}: alert carries no position")
            return False
        obj = Obj(
            id=obj_id,
            ra=position[0],
            dec=position[1],
            ra_dis=position[0],
            dec_dis=position[1],
            score=candidate.get("drb"),
            origin=survey,
        )
        session.add(obj)
        await session.flush()

    if filter_id is None:
        # Nothing to scan against. The annotation is still written, so the
        # match is not lost, but it will not appear on a scanning page.
        return False

    jd = alert_jd(alert)
    passed_at = Time(jd, format="jd").datetime if jd is not None else utcnow_naive()

    existing = await session.scalar(
        sa.select(Candidate).where(
            Candidate.obj_id == obj_id,
            Candidate.filter_id == int(filter_id),
            Candidate.passed_at == passed_at,
        )
    )
    if existing is not None:
        return True

    session.add(
        Candidate(
            obj_id=obj_id,
            filter_id=int(filter_id),
            passing_alert_id=candidate.get("candid") or alert.get("candid"),
            passed_at=passed_at,
            uploader_id=user.id,
        )
    )
    return True


async def ingest_match_photometry(session, user, broker, obj_id, survey):
    """Ingest the matched object's light curve, so a scanner has something to
    judge it on.

    The crossmatch query projects only enough of each alert to place it in space
    and time -- no detection history -- so the full object is refetched here.
    Photometry only: the obj is a candidate awaiting review, not a Source.

    Best effort. A broker that cannot serve the history, or an object it no
    longer has, must not cost us the match itself.
    """
    if not broker.broker_class.implements().get("get_alert"):
        return False
    try:
        data = broker.broker_class.get_alert(broker, obj_id, session, survey=survey)
        if not data:
            return False
        await save_object_photometry(data, survey, session, user)
        return True
    except Exception as e:
        log(f"No photometry ingested for {obj_id}: {e}")
        return False


async def process_event_filter(
    session, user, event, localization, filter_, state, config=None, archival=False
):
    """Query one filter's broker for one event and save whatever genuinely matches.

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

    broker = filter_.broker
    survey = filter_survey(filter_)
    # Bounded by the filter's own stream: its group is who sees the candidates,
    # so they already hold that stream.
    permissions = survey_permissions([filter_.stream] if filter_.stream else [])

    implements = broker.broker_class.implements()

    if implements.get("filter_pipeline") == "mongo":
        # Preferred path: run the quality cuts as a broker-side filter pipeline,
        # with the cone prepended as a spatial stage. This keeps the cuts in the
        # same versioned, editable place as every other broker filter, and means
        # artifacts, asteroids and variable stars are rejected before they cross
        # the wire rather than after.
        cuts, cuts_source = await resolve_quality_pipeline(session, broker, filter_.id)
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
            f"{filter_.name} via {broker.name}: {len(alerts)} alert(s) for "
            f"{event.dateobs} using {cuts_source}"
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
            f"{filter_.name} via {broker.name}: dropped {undated} alert(s) with "
            f"no JD near {event.dateobs} (cannot place them in the event window)"
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
    user_id = user.id
    distance_at = distance_lookup(localization)

    for index in sorted(inside):
        alert = keep[index]
        object_id = alert_object_id(alert)
        try:
            await ensure_candidate(
                session,
                user,
                alert,
                object_id,
                filter_.id,
                survey=survey,
            )
            await ingest_match_photometry(session, user, broker, object_id, survey)
            await annotate_match(
                session,
                user,
                object_id,
                event_key,
                event_dateobs,
                group_ids,
                build_annotation_data(
                    event_jd,
                    ra0,
                    dec0,
                    radius,
                    alert,
                    archival=archival,
                    distance_at=distance_at,
                ),
            )
            await propose_association(session, user_id, object_id, event_dateobs)
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

        # A filter is one crossmatch configuration: it names the broker, the
        # stream (hence survey and programids) and the group that sees the
        # candidates. Opt in per filter so a second survey is a filter, not code.
        filters = (
            (
                await session.scalars(
                    sa.select(Filter).options(
                        selectinload(Filter.stream), selectinload(Filter.broker)
                    )
                )
            )
            .unique()
            .all()
        )
        # A filter that opted in but cannot be used is a misconfiguration, not a
        # preference: say which and why, rather than dropping it silently and
        # looking like the service simply found nothing to do.
        opted_in = [f for f in filters if crossmatch_enabled(f)]
        filters = []
        for f in opted_in:
            problem = None
            if f.broker is None:
                problem = "no broker set on the filter"
            elif not f.broker.active:
                problem = f"broker {f.broker.name} is not active"
            elif not f.broker.broker_class.implements().get("query_alerts"):
                problem = f"broker {f.broker.name} does not implement query_alerts"
            elif filter_survey(f) is None:
                problem = (
                    "its stream names no survey "
                    "(needs altdata.collection, e.g. ZTF_alerts)"
                )
            if problem:
                report_once(
                    f"filter:{f.id}",
                    f"Filter {f.id} ({f.name}) opted in but is being skipped: {problem}",
                )
            else:
                report_once(f"filter:{f.id}", f"Filter {f.id} ({f.name}) is active")
                filters.append(f)

        if not filters:
            report_once(
                "active",
                f"No usable filter opted into the crossmatch ({len(opted_in)} opted "
                f"in); set altdata.{CROSSMATCH_ALTDATA_KEY}.enabled on a filter with "
                "an active broker and a survey stream",
            )
            return 0

        report_once(
            "active",
            f"Crossmatching against {len(filters)} filter(s): "
            + ", ".join(
                f"{f.name} [{filter_survey(f)} via {f.broker.name}]" for f in filters
            ),
        )

        events = (
            (
                await session.scalars(
                    sa.select(GcnEvent)
                    .where(GcnEvent.dateobs >= cutoff)
                    .options(
                        selectinload(GcnEvent.groups).selectinload(Group.streams),
                        # GcnEvent.tags is a hybrid over the _tags
                        # relationship, so event_matches would lazy-load it.
                        selectinload(GcnEvent._tags),
                        # tags eagerly: event_matches reads them, and a lazy
                        # load in an async session raises MissingGreenlet.
                        selectinload(GcnEvent.localizations).options(
                            selectinload(Localization.tags),
                            # deferred arrays: distance_lookup reads them, and a
                            # lazy load in an async session raises MissingGreenlet
                            undefer(Localization.uniq),
                            undefer(Localization.probdensity),
                            undefer(Localization.distmu),
                            undefer(Localization.distsigma),
                            undefer(Localization.distnorm),
                        ),
                    )
                )
            )
            .unique()
            .all()
        )

        for event in events:
            if not event.localizations:
                continue
            # Every localization, not just the newest: one EP observation reports
            # each detected source as its own cone under the shared observation
            # timestamp, so a single event can cover several unrelated patches of
            # sky. Searching only one silently drops the rest.
            localizations = sorted(event.localizations, key=lambda loc: loc.created_at)

            for localization in localizations:
                for filter_ in filters:
                    if not event_matches(filter_, event, localization):
                        continue
                    broker = filter_.broker
                    settings = filter_settings(filter_, config)
                    if rate_limited_until(broker.id) is not None:
                        continue
                    state = await session.scalar(
                        sa.select(GcnEventCrossmatchState).where(
                            GcnEventCrossmatchState.gcnevent_id == event.id,
                            GcnEventCrossmatchState.filter_id == filter_.id,
                            GcnEventCrossmatchState.localization_id == localization.id,
                        )
                    )
                    if state is None:
                        state = GcnEventCrossmatchState(
                            gcnevent_id=event.id,
                            filter_id=filter_.id,
                            localization_id=localization.id,
                            status="pending",
                        )
                        session.add(state)
                        await session.commit()
                    elif (
                        state.last_queried is not None
                        and state.last_queried > stale_before
                    ):
                        continue
                    elif state.status == "skipped":
                        continue

                    try:
                        # The pre-event window is searched once, before the first
                        # forward pass, so a candidate that was already active is
                        # flagged as such the first time anyone looks at it.
                        if conf(settings, "archival") and not state.archival_done:
                            total += await process_event_filter(
                                session,
                                user,
                                event,
                                localization,
                                filter_,
                                state,
                                settings,
                                archival=True,
                            )
                            await session.commit()
                            state = await session.get(GcnEventCrossmatchState, state.id)

                        total += await process_event_filter(
                            session, user, event, localization, filter_, state, settings
                        )
                    except Exception as e:
                        traceback.print_exc()
                        # A broker's HTTP body carries the actual reason (BOOM says
                        # e.g. which pipeline stage it rejected); raise_for_status
                        # alone reports only the status code.
                        detail = getattr(getattr(e, "response", None), "text", "") or ""
                        message = f"{e}{f' -- {detail[:300]}' if detail else ''}"
                        state.status = "failed"
                        state.error = message[:500]
                        state.last_queried = utcnow_naive()
                        if is_rate_limited(e):
                            until = note_rate_limited(
                                broker.id, conf(settings, "rate_limit_backoff_minutes")
                            )
                            log(
                                f"{broker.name} rate limited; backing off until "
                                f"{until.isoformat(timespec='seconds')}: {message}"
                            )
                        else:
                            log(
                                f"Crossmatch failed for {event.dateobs} / "
                                f"{filter_.name} ({broker.name}): {message}"
                            )
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


def distance_lookup(localization):
    """Return f(ra, dec) -> (mu, sigma) Mpc at that pixel, or None.

    The conditional distance at the candidate's own position, not the skymap's
    marginal distance: for a long arc spanning a range of distances the two
    disagree, and "in the localization volume" means the former. Rasterizing is
    expensive, so it happens once per localization and is then indexed per
    candidate.
    """
    if not localization.is_3d:
        return lambda ra, dec: None

    try:
        prob, distmu, distsigma, _ = localization.flat
    except Exception as e:
        log(f"Could not rasterize localization {localization.id} for distance: {e}")
        return lambda ra, dec: None

    nside = healpy.npix2nside(len(prob))

    def lookup(ra, dec):
        index = healpy.ang2pix(nside, float(ra), float(dec), lonlat=True)
        mu, sigma = float(distmu[index]), float(distsigma[index])
        if not (np.isfinite(mu) and np.isfinite(sigma)) or mu <= 0:
            return None
        return mu, sigma

    return lookup


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


async def propose_association(session, user_id, obj_id, event_dateobs):
    """Record the match as awaiting review: status stays 'pending' until a human
    confirms or rejects it. confirmer_id is NOT NULL, so it records the service
    user that proposed the row, not a verdict. Never overwrites an existing one."""
    existing = await session.scalar(
        sa.select(GcnEventObj).where(
            GcnEventObj.obj_id == obj_id,
            GcnEventObj.dateobs == event_dateobs,
        )
    )
    if existing is None:
        session.add(
            GcnEventObj(
                obj_id=obj_id,
                dateobs=event_dateobs,
                status="pending",
                confirmer_id=user_id,
            )
        )


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
        # Not logged: this is a configuration state, not an event, and the
        # caller already names the source on every query.
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
