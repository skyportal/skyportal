"""Shared read-only photometry passthrough for broker providers.

A provider's ``get_photometry`` fetches an object's photometry from the broker
and returns the per-(survey, programid) groups built by
``_save.build_photometry_groups``. This module holds everything downstream of
that — the broker-agnostic half — so a provider only implements the fetch.

The pattern is broker-canonical / marshal-as-cache: Postgres stays the system of
record for *saved* photometry, but display-only views (a source page, a candidate
lightcurve) are served straight from the broker through a Valkey read-through
cache, and **nothing here writes photometry to Postgres**.

Design points:

* The cache key includes a hash of the requester's access scope (groups +
  streams), and broker points are scope-filtered *before* caching, so a cached
  payload is already scope-correct and can never leak across scopes.
* The unit conversions and programid->stream mapping come from
  ``build_photometry_groups``, shared verbatim with the persisting path, so the
  passthrough can never drift from what the saved rows would have been.
* The pure functions (scope/variant hashing, the scope filter, the merge) carry
  the security-critical logic and are directly unit-testable with no broker or
  Valkey.
"""

import hashlib
import json
import traceback

from baselayer.log import make_log

log = make_log("broker/photometry")

# Group keys that form a PhotFluxFlexible payload for standardize_photometry_data
# (everything except stream_ids, which gates visibility, not serialization).
_PAYLOAD_KEYS = (
    "obj_id",
    "instrument_id",
    "mjd",
    "flux",
    "fluxerr",
    "filter",
    "zp",
    "magsys",
    "ra",
    "dec",
)


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _short_sha(value) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()[:16]


def scope_hash(user_id, group_ids, stream_ids, is_admin=False) -> str:
    """Hash the access-determining identity that gates *which* photometry a user
    may see.

    Mirrors the row-level-security inputs: the user's id plus their accessible
    group and stream ids (sorted, so membership order is irrelevant). Admins,
    who bypass row filtering, collapse to a single ``"admin"`` bucket.

    Putting this in the cache key is the no-leakage guarantee: a payload cached
    for one access scope can never be served to a different scope (the key
    differs), and a membership change moves the requester to a different key
    automatically — the stale entry simply ages out.
    """
    if is_admin:
        return "admin"
    payload = {
        "u": int(user_id),
        "g": sorted(int(g) for g in (group_ids or [])),
        "s": sorted(int(s) for s in (stream_ids or [])),
    }
    return _short_sha(payload)


def variant_hash(params: dict) -> str:
    """Hash the serialization-shape args (e.g. ``format``/``magsys``) that change
    *how* a response renders but not *which* rows are visible. Kept separate from
    :func:`scope_hash` so visibility and rendering are never conflated."""
    return _short_sha({k: params[k] for k in sorted(params or {})})


def photometry_key(broker_id, obj_id, scope, variant, version="v1") -> str:
    """Full cache key for an ephemeral photometry payload. Keyed by broker too:
    two brokers may serve the same object with different data."""
    return f"photcache:{version}:{broker_id}:{obj_id}:{scope}:{variant}"


def filter_groups_by_streams(groups, accessible_stream_ids, is_admin=False):
    """Drop photometry groups the requester is not permitted to see.

    ``groups`` is the mapping from ``build_photometry_groups`` — keyed by
    ``(survey, programid)``, each value carrying the ``stream_ids`` that gate it.
    A group is kept iff the requester is an admin, or at least one of the group's
    ``stream_ids`` is in ``accessible_stream_ids``. This reproduces, before
    caching, the same stream gating the persisted-row query would apply (e.g.
    ZTF partnership vs public programs).
    """
    if is_admin:
        return dict(groups)
    accessible = {int(s) for s in (accessible_stream_ids or [])}
    kept = {}
    for key, group in groups.items():
        group_streams = {int(s) for s in (group.get("stream_ids") or [])}
        if group_streams & accessible:
            kept[key] = group
    return kept


def _dedup_key(point):
    """Identity of a photometry point for merge deduplication: the same
    observation across the DB and the broker shares (instrument, filter, mjd).
    mjd is rounded to absorb float noise (1e-6 day ~= 0.09 s)."""
    mjd = point.get("mjd")
    return (
        point.get("instrument_id"),
        point.get("filter"),
        round(mjd, 6) if mjd is not None else None,
    )


def merge_photometry_points(db_points, broker_points):
    """Union persisted (DB) photometry with on-demand broker photometry for
    display.

    The DB is authoritative: a broker point that matches a DB point on
    (instrument_id, filter, mjd) is dropped, so the broker only *augments* the
    DB with points not yet saved. DB points keep their identity (e.g. ``id``,
    groups); broker-only points are appended.
    """
    seen = {_dedup_key(p) for p in db_points}
    merged = list(db_points)
    for point in broker_points:
        if _dedup_key(point) not in seen:
            merged.append(point)
    return merged


async def fetch_broker_groups(cls, broker, object_id, survey, session):
    """Fetch ``object_id``'s photometry from the broker and transform it into
    skyportal-unit groups, WITHOUT persisting anything.

    The DB lookups (instrument, programid->stream) run on the loop; the broker
    call (``get_alert``, blocking network I/O that never touches ``session``) is
    handed to a thread executor so a slow broker can't stall the IO loop — this
    backs the source-page lightcurve, a hot read path. Returns the per-(survey,
    programid) groups, or ``None`` if the broker has no data for the object.
    """
    import asyncio

    import sqlalchemy as sa

    from ..models import Instrument
    from ._save import build_photometry_groups, programid_to_stream_ids

    instrument_id = await session.scalar(
        sa.select(Instrument.id).where(Instrument.name == survey)
    )
    if instrument_id is None:
        raise ValueError(f"Instrument '{survey}' not found in the database.")
    programid2streamid = await programid_to_stream_ids(session)

    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(
        None, lambda: cls.get_alert(broker, object_id, None, survey=survey)
    )
    if not data:
        return None
    return build_photometry_groups(
        object_id, survey, data, instrument_id, programid2streamid
    )


async def display_photometry(
    cls,
    broker,
    object_id,
    session,
    user,
    *,
    cache=None,
    survey=None,
    outsys="ab",
    fmt="mag",
    refresh=False,
):
    """Object photometry for display: the persisted, access-controlled DB rows
    merged with photometry fetched on demand from the broker.

    The broker half is scope-filtered *before* being cached (per object + access
    scope) and is never written to Postgres; a broker failure degrades to DB-only
    rather than erroring, since this backs the source-page lightcurve. On a fresh
    broker fetch, the object's PhotStat summary is recomputed fire-and-forget.
    Shared by every provider via the interface's default ``get_photometry``.
    """
    survey = survey or (broker.altdata or {}).get("survey")

    user_id, group_ids, stream_ids, is_admin = await resolve_scope(user, session)
    key = photometry_key(
        broker.id,
        object_id,
        scope_hash(user_id, group_ids, stream_ids, is_admin),
        variant_hash({"format": fmt, "magsys": outsys}),
    )

    broker_points = None if (refresh or cache is None) else await cache.get_json(key)
    if broker_points is None:
        broker_points = []
        try:
            groups = await fetch_broker_groups(cls, broker, object_id, survey, session)
            kept = filter_groups_by_streams(groups or {}, stream_ids, is_admin)
            broker_points = await serialized_broker_points(
                kept, session, outsys=outsys, fmt=fmt
            )
            if cache is not None:
                await cache.set_json(key, broker_points)
            # Fresh broker data: refresh the object's PhotStat (from the full DB ∪
            # broker set) so listings/scanning reflect it. Fire-and-forget via
            # spawn_callback — the IOLoop keeps the task alive (a bare
            # ensure_future can be GC'd before it runs) and logs any exception.
            if groups:
                from tornado.ioloop import IOLoop

                IOLoop.current().spawn_callback(
                    update_phot_stat_from_broker, object_id, groups
                )
        except Exception:
            log(
                f"passthrough broker fetch failed for {survey}/{object_id}; "
                f"serving DB photometry only: {traceback.format_exc()}"
            )
            broker_points = []

    db_points = await db_photometry_points(
        object_id, user, session, outsys=outsys, fmt=fmt
    )
    return merge_photometry_points(db_points, broker_points)


async def resolve_scope(user, session):
    """Resolve the (user, accessible groups, accessible streams) tuple that gates
    which photometry is visible — part of the cache key, and used to scope-filter
    broker points before caching. Admins bypass row-level filtering and share one
    bucket. Explicit selects avoid lazy relationship loads under the async
    session."""
    from ..models import Group, Stream

    if user.is_admin:
        return user.id, [], [], True
    group_ids = list(
        (await session.scalars(Group.select(user).with_only_columns(Group.id))).all()
    )
    stream_ids = list(
        (await session.scalars(Stream.select(user).with_only_columns(Stream.id))).all()
    )
    return user.id, group_ids, stream_ids, False


async def transient_photometry(groups, session):
    """Build *transient* (non-persisted) ``Photometry`` objects from broker
    groups, running each group through the same ``standardize_photometry_data``
    the DB-write path uses so the flux / zeropoint / magsys conversions are
    byte-for-byte identical. Shared by the serialized display points and the
    PhotStat recompute.
    """
    from ..handlers.api.photometry import standardize_photometry_data
    from ..models import Photometry

    phots = []
    for group in groups.values():
        payload = {k: group[k] for k in _PAYLOAD_KEYS if k in group}
        df, instrument_cache = await standardize_photometry_data(payload, session)
        for row in df.to_dict("records"):
            phot = Photometry(
                obj_id=row["obj_id"],
                instrument_id=row["instrument_id"],
                mjd=row["mjd"],
                filter=row["filter"],
                ra=row.get("ra"),
                dec=row.get("dec"),
                ra_unc=row.get("ra_unc"),
                dec_unc=row.get("dec_unc"),
                flux=row.get("standardized_flux"),
                fluxerr=row.get("standardized_fluxerr"),
                origin=row.get("origin"),
            )
            # serialize()/PhotStat read phot.instrument; attach the already-loaded
            # instrument from the standardize cache so it needs no DB round-trip.
            instrument = instrument_cache.get(row["instrument_id"])
            if instrument is not None:
                phot.instrument = instrument
            phots.append(phot)
    return phots


async def serialized_broker_points(groups, session, outsys="ab", fmt="mag"):
    """Serialize transient broker Photometry into skyportal's photometry display
    shape (the same ``serialize()`` used by ``GET /sources/{id}/photometry``), so
    broker points are shape-identical to DB points and the two can be merged.
    """
    from ..handlers.api.photometry import serialize

    return [
        serialize(
            phot,
            outsys,
            fmt,
            created_at=False,
            groups=False,
            annotations=False,
            owner=False,
            stream=False,
            validation=False,
        )
        for phot in await transient_photometry(groups, session)
    ]


async def db_photometry_points(object_id, user, session, outsys="ab", fmt="mag"):
    """Serialize the object's persisted, access-controlled photometry, using the
    same ``serialize()`` the standard photometry endpoint uses so DB and broker
    points share one shape. Eager-loads the relationships ``serialize()`` reads
    (instrument, groups) to avoid lazy loads under the async session.
    """
    from sqlalchemy.orm import joinedload

    from ..handlers.api.photometry import serialize
    from ..models import Group, Instrument, Photometry

    stmt = (
        Photometry.select(user)
        .where(Photometry.obj_id == object_id)
        .options(
            joinedload(Photometry.instrument).load_only(Instrument.name),
            joinedload(Photometry.groups).load_only(
                Group.id, Group.name, Group.nickname, Group.single_user_group
            ),
        )
    )
    phot = (await session.scalars(stmt)).unique().all()
    return [
        serialize(
            p,
            outsys,
            fmt,
            created_at=False,
            groups=True,
            annotations=False,
            owner=False,
            stream=False,
            validation=False,
        )
        for p in phot
    ]


async def update_phot_stat_from_broker(object_id, groups):
    """Recompute the object's PhotStat from DB ∪ all broker photometry and
    persist the summary (never the bulk photometry).

    Fire-and-forget from the read path: it opens its own session, logs and
    swallows any error, and must never affect the photometry response. Built
    from the *full, unfiltered* broker set so the per-object aggregate is
    viewer-independent (it does not depend on the requester's stream access).
    Broker points already saved are deduped out (by instrument/filter/mjd) so
    they are not double-counted against the DB rows.
    """
    import sqlalchemy as sa

    from baselayer.app import models as baselayer_models

    from ..models import Photometry, PhotStat

    try:
        async with baselayer_models.async_plain_session_factory() as session:
            broker_phot = await transient_photometry(groups, session)
            db_phot = list(
                (
                    await session.scalars(
                        sa.select(Photometry).where(Photometry.obj_id == object_id)
                    )
                ).all()
            )
            seen = {
                (p.instrument_id, p.filter, round(p.mjd, 6))
                for p in db_phot
                if p.mjd is not None
            }
            merged = db_phot + [
                p
                for p in broker_phot
                if p.mjd is None
                or (p.instrument_id, p.filter, round(p.mjd, 6)) not in seen
            ]
            if not merged:
                return
            phot_stat = (
                await session.scalars(
                    sa.select(PhotStat).where(PhotStat.obj_id == object_id)
                )
            ).first()
            if phot_stat is None:
                phot_stat = PhotStat(obj_id=object_id)
                session.add(phot_stat)
            phot_stat.full_update(merged)
            await session.commit()
    except Exception:
        log(f"phot_stat broker update failed for {object_id}: {traceback.format_exc()}")
