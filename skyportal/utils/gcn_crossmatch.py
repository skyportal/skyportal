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


def build_annotation_data(event_jd, ra0, dec0, radius_deg, alert):
    """Event-relative quantities for one matched alert.

    These are the columns the ep-ztf-xmatch UI was built around: how long after
    the trigger the alert fired, how far off the localization centre it sits,
    and that separation as a fraction of the error radius.
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
        merged[event_key] = payload
        annotation.data = merged
        flag_modified(annotation, "data")


async def process_event_broker(
    session, user, event, localization, broker, state, config=None
):
    """Query one broker for one event and save whatever genuinely matches."""
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

    # Lower bound on the query window: resume from the newest alert already seen
    # rather than from wall-clock, because brokers make alerts queryable some
    # time after the alert's own JD. Anchoring on wall-clock would step over
    # that lag and silently lose late-arriving alerts.
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

    params = {
        "ra": ra0,
        "dec": dec0,
        "radius": radius,
        "radius_units": "deg",
        "jd_start": jd_start,
        "jd_end": jd_end,
        "permissions": permissions,
    }

    alerts = broker.broker_class.query_alerts(broker, session, **params) or []

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
                build_annotation_data(event_jd, ra0, dec0, radius, alert),
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
