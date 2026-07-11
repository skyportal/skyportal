import asyncio
import time

import sqlalchemy as sa
from sqlalchemy.orm import selectinload

from baselayer.app import models
from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.app.models import init_db
from baselayer.log import make_log
from skyportal.models import (
    Obj,
    Thumbnail,
)
from skyportal.utils.services import check_loaded

env, cfg = load_env()
log = make_log("thumbnail_queue")

init_db(**cfg["database"])

THUMBNAIL_TYPES = {"sdss", "ls", "ps1"}

# Defensive guardrail so a stuck cutout/scan query can't wedge a backend.
STATEMENT_TIMEOUT = "120s"


async def set_statement_timeout(session):
    """Bound query time for this session. Under pgbouncer transaction pooling
    this applies per-transaction, so set it right after opening a session."""
    await session.execute(sa.text(f"SET statement_timeout = '{STATEMENT_TIMEOUT}'"))


async def fetch_obj(session):
    """Fetch the object with the most recent created_at timestamp that is missing at least one thumbnail.

    Parameters
    ----------
    session : `sqlalchemy.ext.asyncio.AsyncSession`
        The async database session to use for the query.

    Returns
    -------
    obj : `skyportal.models.Obj` or None
        The object with the most recent created_at timestamp that is missing at least one thumbnail.
    err : `Exception` or None
        The exception that occurred, if any.
    """

    obj = None
    try:
        stmt = (
            sa.select(Obj.id)
            .where(
                ~sa.exists(
                    sa.select(Thumbnail.obj_id)
                    .where(
                        sa.and_(
                            Thumbnail.obj_id == Obj.id,
                            Thumbnail.type.in_(THUMBNAIL_TYPES),
                        )
                    )
                    .group_by(Thumbnail.obj_id)
                    .having(
                        sa.func.count(sa.distinct(Thumbnail.type))
                        == len(THUMBNAIL_TYPES)
                    )
                )
            )
            .order_by(Obj.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        objs = result.scalars().all()
        if len(objs) == 0:
            return None, None
        else:
            # eager-load thumbnails: we read obj.thumbnails below, which would
            # otherwise lazy-load under the async session.
            obj = await session.scalar(
                sa.select(Obj)
                .options(selectinload(Obj.thumbnails))
                .where(Obj.id == objs[0])
            )
            return obj, None
    except Exception as e:
        return None, e


async def _run_loop():
    # start a timer we'll use to have a heartbeat every 60 seconds
    heartbeat = time.time()
    while True:
        if time.time() - heartbeat > 60:
            heartbeat = time.time()
            log("Thumbnail queue heartbeat.")
        try:
            internal_key = None
            # 1. Read/claim: find one obj missing thumbnails and snapshot what we
            # need, then release the connection before the slow cutout fetch so
            # we don't sit idle-in-transaction across it.
            # Access via the module: init_db() (above) rebinds the factory after
            # this module is imported, so a direct `from ... import` would keep
            # the pre-init None and call None() ('NoneType' object is not callable).
            async with models.async_plain_session_factory() as session:
                await set_statement_timeout(session)
                obj, err = await fetch_obj(session)
                if err is not None:
                    log(f"Error fetching object with missing thumbnails: {str(err)}")
                    await asyncio.sleep(1)
                    continue
                if obj is None:
                    await asyncio.sleep(5)
                    continue
                existing_thumbnail_types = [thumb.type for thumb in obj.thumbnails]
                thumbnails = list(THUMBNAIL_TYPES - set(existing_thumbnail_types))
                obj_id = obj.id
                if len(thumbnails) == 0:
                    log(f"Source {obj_id} has all thumbnails.")
                    continue
                log(f"Processing thumbnail request for object {obj_id}.")

            # 2. Resolve the slow PanSTARRS cutout URL off the event loop with no
            # DB transaction open. `obj` is detached but its attributes are loaded.
            ps1_url = None
            if "ps1" in thumbnails:
                ps1_url = await asyncio.to_thread(lambda o=obj: o.panstarrs_url)

            # 3. Short write txn: just the Thumbnail INSERTs.
            async with models.async_plain_session_factory() as session:
                await set_statement_timeout(session)
                try:
                    obj = await session.get(Obj, obj_id)
                    if obj is not None:
                        await obj.add_linked_thumbnails(
                            thumbnails, session, ps1_url=ps1_url
                        )
                        internal_key = obj.internal_key
                except Exception as e:
                    log(
                        f"Error processing thumbnail request for object {obj_id}: {str(e)}"
                    )
                    if isinstance(e, sa.exc.SQLAlchemyError):
                        try:
                            await session.rollback()
                        except Exception as rollback_err:
                            log(
                                f"Error rolling back session after thumbnail failure for object {obj_id}: {str(rollback_err)}"
                            )

            if internal_key is not None:
                flow = Flow()
                flow.push(
                    "*",
                    "skyportal/REFRESH_SOURCE",
                    payload={"obj_key": internal_key},
                )
                flow.push(
                    "*",
                    "skyportal/REFRESH_CANDIDATE",
                    payload={"id": internal_key},
                )
        except Exception as e:
            log(f"Error processing thumbnail request: {str(e)}")
            await asyncio.sleep(5)


@check_loaded(logger=log)
def service(*args, **kwargs):
    asyncio.run(_run_loop())


if __name__ == "__main__":
    try:
        service()
    except Exception as e:
        log(f"Error starting thumbnail queue: {str(e)}")
        raise e
