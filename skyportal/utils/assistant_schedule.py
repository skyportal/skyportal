"""Interval and on-demand runs for shared Assistant Queries."""

import asyncio
import hashlib
import json
import uuid
from datetime import timedelta

import sqlalchemy as sa

from baselayer.app.models import new_async_session
from baselayer.log import make_log

from ..models import (
    AssistantMessage,
    AssistantQuery,
    Classification,
    GcnEvent,
    GcnTag,
    Group,
    Localization,
    Obj,
    Photometry,
    Source,
)
from .assistant import is_enabled, post_to_assistant
from .assistant_triage import query_bot_id, task_message
from .naive_datetime import utcnow_naive

log = make_log("assistant_schedule")

GRB_LOOKBACK = timedelta(days=2)
STALE_RUN = timedelta(minutes=15)
MAX_EVENTS_PER_RUN = 10


def task_channel_prefix(query_id):
    return f"query:{query_id}:task:"


def update_schedule(query, now):
    query.next_run_at = (
        now + timedelta(minutes=query.interval_minutes)
        if query.active and query.interval_minutes
        else None
    )


def saved_source(group_id, source_id):
    return sa.select(Source.id).where(
        Source.group_id == group_id, Source.obj_id == source_id, Source.active.is_(True)
    )


def visible_events(group_id, public_group_name):
    return sa.select(GcnEvent).where(
        GcnEvent.groups.any(group_scope(group_id, public_group_name))
    )


def group_scope(group_id, public_group_name):
    return (Group.id == group_id) | (Group.name == public_group_name)


def _localization_evidence(localization):
    name = localization.localization_name
    try:
        _, _, radius_deg = map(float, name.split("_"))
    except (AttributeError, ValueError):
        radius_deg = None
    return {
        "name": name,
        "cone_radius_arcmin": None if radius_deg is None else round(radius_deg * 60, 4),
        "properties": [prop.data for prop in localization.properties],
    }


def grb_evidence(event):
    return {
        "aliases": sorted(event.aliases),
        "trigger_id": event.trigger_id,
        "trigger_utc": event.dateobs.isoformat(),
        "notices": [
            {"stream": notice.stream, "type": notice.notice_type, "id": notice.ivorn}
            for notice in event.gcn_notices
        ],
        "localizations": [
            _localization_evidence(loc)
            for loc in sorted(event.localizations, key=lambda loc: loc.id)
        ],
        "properties": [prop.data for prop in event.properties],
        "circulars": event.circulars,
        "extractions": [
            {
                "circular_id": extraction.circular_id,
                "origin": extraction.origin,
                "data": extraction.data,
            }
            for extraction in event.extractions[-8:]
        ],
    }


async def _grb_targets(session, query, now, public_group_name):
    events = await session.scalars(
        visible_events(query.group_id, public_group_name)
        .where(
            GcnEvent.dateobs.between(now - GRB_LOOKBACK, now),
            GcnEvent._tags.any(sa.func.lower(GcnTag.text) == "grb"),
        )
        .options(
            sa.orm.undefer(GcnEvent.circulars),
            sa.orm.selectinload(GcnEvent.gcn_notices),
            sa.orm.selectinload(GcnEvent.properties),
            sa.orm.selectinload(GcnEvent.extractions),
            sa.orm.selectinload(GcnEvent.localizations).selectinload(
                Localization.properties
            ),
        )
        .order_by(GcnEvent.dateobs.desc())
    )
    for event in events:
        evidence = json.dumps(grb_evidence(event), sort_keys=True, default=str)
        # Changing the prompt or enabling posting deserves a fresh review.
        digest = hashlib.sha256(
            json.dumps([query.prompt, query.dry_run, evidence]).encode()
        ).hexdigest()
        dateobs = event.dateobs.isoformat()
        channel = f"task:grb:{event.id}:{digest}"
        previous = await session.scalar(
            sa.select(AssistantMessage)
            .where(
                AssistantMessage.channel == f"query:{query.id}:{channel}",
                AssistantMessage.system.is_(False),
            )
            .order_by(AssistantMessage.id.desc())
            .limit(1)
        )
        if previous and (
            previous.run_status == "completed"
            or (previous.run_status == "queued" and previous.modified > now - STALE_RUN)
        ):
            continue
        yield "gcn_event", dateobs, channel, evidence


async def _source_targets(session, query, now, public_group_name):
    if not query.source_id or not await session.scalar(
        saved_source(query.group_id, query.source_id)
    ):
        raise ValueError("Select a source saved to this query's group.")
    pending = await session.scalar(
        sa.select(AssistantMessage.id)
        .where(
            AssistantMessage.channel.startswith(task_channel_prefix(query.id)),
            AssistantMessage.run_status == "queued",
            AssistantMessage.modified > now - STALE_RUN,
        )
        .limit(1)
    )
    if pending is not None:
        return
    source_id = query.source_id
    scope = group_scope(query.group_id, public_group_name)
    coordinates = (
        await session.execute(sa.select(Obj.ra, Obj.dec).where(Obj.id == source_id))
    ).one()
    photometry = await session.execute(
        sa.select(Photometry.mjd, Photometry.filter, Photometry.mag)
        .where(Photometry.obj_id == source_id, Photometry.groups.any(scope))
        .order_by(Photometry.mjd.desc())
        .limit(25)
    )
    classifications = await session.execute(
        sa.select(Classification.classification, Classification.probability)
        .where(Classification.obj_id == source_id, Classification.groups.any(scope))
        .order_by(Classification.id.desc())
        .limit(10)
    )
    evidence = {
        "source": source_id,
        "coordinates": dict(coordinates._mapping),
        "recent_photometry": [dict(row._mapping) for row in photometry],
        "classifications": [dict(row._mapping) for row in classifications],
    }
    yield (
        "source",
        source_id,
        f"task:source:{uuid.uuid4().hex}",
        json.dumps(evidence, default=str),
    )


async def queue_query_task(session, query, now, public_group_name):
    """The caller locks the query so manual and interval runs cannot overlap."""
    bot_id = await query_bot_id(session, query)
    if bot_id is None:
        raise ValueError("The query owner and skybot must belong to the query's group.")
    targets = (
        _grb_targets(session, query, now, public_group_name)
        if query.context_type == "gcn_event"
        else _source_targets(session, query, now, public_group_name)
    )
    jobs = []
    async for context_type, context_id, channel, evidence in targets:
        message = await task_message(
            session, query, bot_id, context_type, context_id, channel, evidence
        )
        message.run_status = "queued"
        session.add(message)
        jobs.append(message)
        if len(jobs) >= MAX_EVENTS_PER_RUN:
            break
    query.last_run_at = now
    query.last_run_count = len(jobs)
    await session.flush()
    return [job.id for job in jobs]


async def dispatch_query_jobs(session, cfg, message_ids):
    accepted = await asyncio.gather(
        *(
            asyncio.to_thread(post_to_assistant, cfg, message_id)
            for message_id in message_ids
        )
    )
    failed = [
        message_id
        for message_id, ok in zip(message_ids, accepted, strict=True)
        if not ok
    ]
    if failed:
        await session.execute(
            sa.update(AssistantMessage)
            .where(
                AssistantMessage.id.in_(failed), AssistantMessage.run_status == "queued"
            )
            .values(run_status="failed")
        )
        await session.commit()
    return len(message_ids) - len(failed)


async def run_due_queries(cfg):
    if not is_enabled(cfg):
        return
    now = utcnow_naive()
    async with new_async_session() as session:
        due = (
            AssistantQuery.active.is_(True),
            AssistantQuery.interval_minutes.is_not(None),
            AssistantQuery.next_run_at <= now,
        )
        query_ids = (
            await session.scalars(
                sa.select(AssistantQuery.id)
                .where(*due)
                .order_by(AssistantQuery.next_run_at)
                .limit(25)
            )
        ).all()
        for query_id in query_ids:
            query = await session.scalar(
                sa.select(AssistantQuery)
                .where(AssistantQuery.id == query_id, *due)
                .with_for_update(skip_locked=True)
            )
            if query is None:
                continue
            update_schedule(query, now)
            try:
                jobs = await queue_query_task(
                    session, query, now, cfg["misc.public_group_name"]
                )
            except ValueError as exc:
                log(f"Assistant query {query_id}: {exc}")
                query.last_run_at = now
                query.last_run_count = None
                jobs = []
            await session.commit()
            await dispatch_query_jobs(session, cfg, jobs)

        next_run = await session.scalar(
            sa.select(sa.func.min(AssistantQuery.next_run_at)).where(
                AssistantQuery.active.is_(True)
            )
        )
        return max(1, (next_run - utcnow_naive()).total_seconds()) if next_run else None
