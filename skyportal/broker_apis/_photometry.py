"""Shared read-only photometry passthrough for broker providers: everything
downstream of the ``_save.build_photometry_groups`` transform, so a provider only
implements the broker fetch. Nothing here writes photometry to Postgres.
"""

import time
import traceback

import numpy as np

from baselayer.app.env import load_env
from baselayer.log import make_log

from ..utils.cache import Cache, cache_folder, dict_to_bytes
from ..utils.survey import survey_from_object_id
from .interface import survey_permissions

_, cfg = load_env()

log = make_log("broker/photometry")

cache = Cache(
    cache_dir=f"{cache_folder}/broker_photometry",
    max_age=cfg.get("misc.minutes_to_keep_broker_photometry_cache", 30) * 60,
)

_FETCH_TIMEOUT_SECONDS = 10
_FAILURE_SKIP_SECONDS = 60
_skip_until: dict = {}

# stream_ids is left out: it gates visibility, not serialization.
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


def filter_groups_by_scope(groups, permissions):
    """Keep the groups whose ``(survey, programid)`` the requester's streams cover.
    ``permissions`` is ``survey_permissions()``, ``None`` the admin's full scope."""
    if permissions is None:
        return groups
    return {
        key: group
        for key, group in groups.items()
        if key[1] in (permissions.get(key[0]) or [])
    }


def _round_mjd(mjd):
    return round(mjd, 6) if mjd is not None else None


def _dedup_key(point):
    return (
        point.get("instrument_id"),
        point.get("filter"),
        _round_mjd(point.get("mjd")),
    )


def _phot_dedup_key(phot):
    return (phot.instrument_id, phot.filter, _round_mjd(phot.mjd))


def merge_photometry_points(db_points, broker_points):
    """Union DB and broker photometry, the DB point winning on (instrument, filter, mjd)."""
    seen = {_dedup_key(p) for p in db_points}
    return [*db_points, *(p for p in broker_points if _dedup_key(p) not in seen)]


def _serialize_points(phots, outsys, fmt, groups=False):
    from ..handlers.api.photometry import serialize

    return [
        serialize(
            phot,
            outsys,
            fmt,
            created_at=False,
            groups=groups,
            annotations=False,
            owner=False,
            stream=False,
            validation=False,
        )
        for phot in phots
    ]


async def fetch_broker_groups(cls, broker, object_id, survey, session):
    """The object's broker photometry as skyportal-unit groups, read through a cache
    and empty when the broker has no data for it or just failed. Persists nothing."""
    import asyncio

    import sqlalchemy as sa

    from ..models import Instrument
    from ._save import build_photometry_groups, programid_to_stream_ids

    key = f"{broker.id}_{survey}_{object_id}"
    cached = cache[key]
    if cached is not None:
        return np.load(cached, allow_pickle=True).item()
    if time.monotonic() < _skip_until.get((broker.id, survey), 0):
        return {}

    instrument_id = await session.scalar(
        sa.select(Instrument.id).where(Instrument.name == survey)
    )
    if instrument_id is None:
        raise ValueError(f"Instrument '{survey}' not found in the database.")
    programid2streamid = await programid_to_stream_ids(session)

    # a provider's timeout bounds one request, not its pagination walk
    data = await asyncio.wait_for(
        asyncio.get_event_loop().run_in_executor(
            None,
            lambda: cls.get_alert(
                broker, object_id, None, survey=survey, permissions=None
            ),
        ),
        timeout=_FETCH_TIMEOUT_SECONDS,
    )
    groups = (
        build_photometry_groups(
            object_id, survey, data, instrument_id, programid2streamid
        )
        if data
        else {}
    )
    cache[key] = dict_to_bytes(groups)
    if groups:
        from tornado.ioloop import IOLoop

        # spawn_callback, not ensure_future: a bare task can be GC'd before it runs
        IOLoop.current().spawn_callback(update_phot_stat_from_broker, object_id, groups)
    return groups


async def super_obj_obj_ids(object_id, session):
    """``object_id`` plus the objs it shares a SuperObj with, what
    ``includeSuperObjsPhotometry`` expands to on GET /sources/{id}/photometry."""
    import sqlalchemy as sa

    from ..models import ObjToSuperObj

    members = await session.scalars(
        sa.select(ObjToSuperObj.obj_id).where(
            ObjToSuperObj.super_obj_id.in_(
                sa.select(ObjToSuperObj.super_obj_id).where(
                    ObjToSuperObj.obj_id == object_id
                )
            )
        )
    )
    return list(dict.fromkeys([object_id, *members.all()]))


async def display_photometry(
    cls,
    broker,
    object_id,
    session,
    user,
    *,
    survey=None,
    outsys="ab",
    fmt="mag",
    include_super_objs=False,
):
    """Object photometry for display: the access-controlled DB rows merged with
    photometry fetched on demand from the broker, degrading to DB-only on failure.
    ``include_super_objs`` serves the objs sharing a SuperObj too, each fetched
    under its own survey."""
    from ..models import Stream

    permissions = (
        None
        if user.is_system_admin
        else survey_permissions((await session.scalars(Stream.select(user))).all())
    )
    obj_ids = (
        await super_obj_obj_ids(object_id, session)
        if include_super_objs
        else [object_id]
    )
    served = cls.configured_surveys(broker.altdata)

    broker_points = []
    for obj_id in obj_ids:
        obj_survey = (
            (survey if obj_id == object_id else None)
            or survey_from_object_id(obj_id)
            or (broker.altdata or {}).get("survey")
        )
        if served and obj_survey not in served:
            continue
        try:
            groups = await fetch_broker_groups(cls, broker, obj_id, obj_survey, session)
            phots = await transient_photometry(
                filter_groups_by_scope(groups, permissions), session
            )
            broker_points += _serialize_points(phots, outsys, fmt)
        except Exception:
            _skip_until[(broker.id, obj_survey)] = (
                time.monotonic() + _FAILURE_SKIP_SECONDS
            )
            log(
                f"passthrough broker fetch failed for {obj_survey}/{obj_id}; serving "
                f"DB photometry only and skipping {broker.name}/{obj_survey} for "
                f"{_FAILURE_SKIP_SECONDS}s: {traceback.format_exc()}"
            )

    return merge_photometry_points(
        await db_photometry_points(obj_ids, user, session, outsys=outsys, fmt=fmt),
        broker_points,
    )


async def transient_photometry(groups, session):
    from sqlalchemy.orm.attributes import set_committed_value

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
            # serialize()/PhotStat read phot.instrument, which no query would load here
            instrument = instrument_cache.get(row["instrument_id"])
            if instrument is not None:
                # a plain assignment would append to Instrument.photometry
                set_committed_value(phot, "instrument", instrument)
            phots.append(phot)
    return phots


async def db_photometry_points(obj_ids, user, session, outsys="ab", fmt="mag"):
    """Serialize the objects' persisted photometry, eager-loading what ``serialize()``
    reads (a lazy load would raise under the async session)."""
    from sqlalchemy.orm import joinedload

    from ..models import Group, Instrument, Photometry

    stmt = (
        Photometry.select(user)
        .where(Photometry.obj_id.in_(obj_ids))
        .options(
            joinedload(Photometry.instrument).load_only(Instrument.name),
            joinedload(Photometry.groups).load_only(
                Group.id, Group.name, Group.nickname, Group.single_user_group
            ),
        )
    )
    phot = (await session.scalars(stmt)).unique().all()
    return _serialize_points(phot, outsys, fmt, groups=True)


async def update_phot_stat_from_broker(object_id, groups):
    """Recompute the object's PhotStat from DB ∪ the *unfiltered* broker groups, so
    the aggregate does not depend on who is looking."""
    import sqlalchemy as sa

    from baselayer.app import models as baselayer_models

    from ..models import Photometry, PhotStat

    try:
        async with baselayer_models.async_plain_session_factory() as session:
            broker_phot = await transient_photometry(groups, session)
            db_phot = (
                await session.scalars(
                    sa.select(Photometry).where(Photometry.obj_id == object_id)
                )
            ).all()
            seen = {_phot_dedup_key(p) for p in db_phot}
            merged = [
                *db_phot,
                *(p for p in broker_phot if _phot_dedup_key(p) not in seen),
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
