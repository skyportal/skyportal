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

_CACHE_MAX_AGE = cfg.get("misc.minutes_to_keep_broker_photometry_cache", 30) * 60
cache = Cache(
    cache_dir=f"{cache_folder}/broker_photometry",
    max_age=_CACHE_MAX_AGE,
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
        point.get("obj_id"),
        point.get("instrument_id"),
        point.get("filter"),
        _round_mjd(point.get("mjd")),
    )


def _phot_dedup_key(phot):
    return (phot.obj_id, phot.instrument_id, phot.filter, _round_mjd(phot.mjd))


def merge_photometry_points(db_points, broker_points):
    """Union DB and broker photometry, the DB point winning on (obj, instrument, filter, mjd)."""
    seen = {_dedup_key(p) for p in db_points}
    return [*db_points, *(p for p in broker_points if _dedup_key(p) not in seen)]


def _serialize_points(
    phots,
    outsys,
    fmt,
    *,
    groups=False,
    created_at=False,
    owner=False,
    stream=False,
    validation=False,
    annotations=False,
    extinction_by_obj=None,
):
    from ..handlers.api.photometry import serialize

    return [
        serialize(
            phot,
            outsys,
            fmt,
            created_at=created_at,
            groups=groups,
            annotations=annotations,
            owner=owner,
            stream=stream,
            validation=validation,
            extinction_dict=(extinction_by_obj or {}).get(phot.obj_id),
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
        # a read touches the file, so Cache's max_age never expires a hot source
        payload = np.load(cached, allow_pickle=True).item()
        if time.time() - (payload.get("fetched_at") or 0) < _CACHE_MAX_AGE:
            return payload["groups"]
    if time.monotonic() < _skip_until.get((broker.id, survey), 0):
        return {}

    instrument_id = await session.scalar(
        sa.select(Instrument.id).where(Instrument.name == survey)
    )
    if instrument_id is None:
        raise ValueError(f"Instrument '{survey}' not found in the database.")
    programid2streamid = await programid_to_stream_ids(session)

    try:
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
    except TimeoutError:
        # only a stall is broker-wide; a per-object failure must not skip the rest
        _skip_until[(broker.id, survey)] = time.monotonic() + _FAILURE_SKIP_SECONDS
        raise
    except Exception as e:
        if getattr(getattr(e, "response", None), "status_code", None) != 404:
            raise
        data = None
    groups = (
        build_photometry_groups(
            object_id, survey, data, instrument_id, programid2streamid
        )
        if data
        else {}
    )
    cache[key] = dict_to_bytes({"fetched_at": time.time(), "groups": groups})
    if groups:
        from tornado.ioloop import IOLoop

        # spawn_callback, not ensure_future: a bare task can be GC'd before it runs
        IOLoop.current().spawn_callback(update_phot_stat_from_broker, object_id, groups)
    return groups


async def super_obj_obj_ids(object_id, user, session):
    """``object_id`` plus the objs the requester can read that share a SuperObj with
    it, what ``includeSuperObjsPhotometry`` expands to on GET /sources/{id}/photometry."""
    import sqlalchemy as sa

    from ..models import Obj, ObjToSuperObj

    members = (
        await session.scalars(
            sa.select(ObjToSuperObj.obj_id).where(
                ObjToSuperObj.super_obj_id.in_(
                    sa.select(ObjToSuperObj.super_obj_id).where(
                        ObjToSuperObj.obj_id == object_id
                    )
                )
            )
        )
    ).all()
    readable = set(
        (
            await session.scalars(
                Obj.select(user, columns=[Obj.id]).where(Obj.id.in_(members))
            )
        ).all()
    )
    return list(dict.fromkeys([object_id, *(m for m in members if m in readable)]))


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
    owner=False,
    stream=False,
    validation=False,
    annotations=False,
    extinction=False,
):
    """Object photometry for display: the access-controlled DB rows merged with
    photometry fetched on demand from the broker, degrading to DB-only on failure.
    ``include_super_objs`` serves the objs sharing a SuperObj too, each fetched
    under its own survey. The ``owner``/``stream``/``validation``/``annotations``/
    ``extinction`` flags mirror GET /sources/{id}/photometry and only ever apply to
    the DB half: a broker point is not persisted, so it has none of those."""
    from ..models import Stream

    permissions = (
        None
        if user.is_system_admin
        else survey_permissions((await session.scalars(Stream.select(user))).all())
    )
    obj_ids = (
        await super_obj_obj_ids(object_id, user, session)
        if include_super_objs
        else [object_id]
    )
    served = cls.configured_surveys(broker.altdata)

    broker_phots = []
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
            broker_phots += await transient_photometry(
                filter_groups_by_scope(groups, permissions), session
            )
        except Exception:
            log(
                f"passthrough broker fetch failed for {obj_survey}/{obj_id}; serving "
                f"DB photometry only: {traceback.format_exc()}"
            )

    return merge_photometry_points(
        await db_photometry_points(
            obj_ids,
            user,
            session,
            outsys=outsys,
            fmt=fmt,
            owner=owner,
            stream=stream,
            validation=validation,
            annotations=annotations,
            extinction=extinction,
        ),
        _serialize_points(
            broker_phots,
            outsys,
            fmt,
            extinction_by_obj=(
                await extinction_by_filter(broker_phots, session)
                if extinction and fmt != "plot"
                else None
            ),
        ),
    )


async def extinction_by_filter(phots, session):
    """``{obj_id: {filter: extinction}}`` for the filters the points actually use,
    what ``serialize(extinction_dict=...)`` reads."""
    import sqlalchemy as sa

    from ..handlers.api.photometry import nan_to_none
    from ..models import Obj
    from ..utils.extinction import calculate_extinction

    filters = {}
    for phot in phots:
        filters.setdefault(phot.obj_id, set()).add(phot.filter)
    if not filters:
        return None
    rows = (
        await session.execute(
            sa.select(Obj.id, Obj.ra, Obj.dec).where(Obj.id.in_(filters))
        )
    ).all()
    return {
        obj_id: {filt: calculate_extinction(ra, dec, filt) for filt in filters[obj_id]}
        for obj_id, ra, dec in rows
        if nan_to_none(ra) is not None and nan_to_none(dec) is not None
    }


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


async def db_photometry_points(
    obj_ids,
    user,
    session,
    outsys="ab",
    fmt="mag",
    *,
    owner=False,
    stream=False,
    validation=False,
    annotations=False,
    extinction=False,
):
    """Serialize the objects' persisted photometry, eager-loading what ``serialize()``
    reads (a lazy load would raise under the async session)."""
    from sqlalchemy.orm import joinedload, selectinload

    from ..handlers.api.photometry_validation import USE_PHOTOMETRY_VALIDATION
    from ..models import Group, Instrument, Photometry, Stream, User

    options = [
        joinedload(Photometry.instrument).load_only(Instrument.name),
        joinedload(Photometry.groups).load_only(
            Group.id, Group.name, Group.nickname, Group.single_user_group
        ),
    ]
    if annotations:
        options.append(joinedload(Photometry.annotations))
    if owner:
        options.append(
            joinedload(Photometry.owner).load_only(
                User.id, User.username, User.first_name, User.last_name
            )
        )
    if stream:
        options.append(joinedload(Photometry.streams).load_only(Stream.id, Stream.name))
    if validation and USE_PHOTOMETRY_VALIDATION:
        options.append(selectinload(Photometry.validations))

    stmt = Photometry.select(user, options=options).where(
        Photometry.obj_id.in_(obj_ids)
    )
    phots = (await session.scalars(stmt)).unique().all()
    return _serialize_points(
        phots,
        outsys,
        fmt,
        groups=True,
        created_at=True,
        owner=owner,
        stream=stream,
        validation=validation,
        annotations=annotations,
        extinction_by_obj=(
            await extinction_by_filter(phots, session)
            if extinction and fmt != "plot"
            else None
        ),
    )


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
