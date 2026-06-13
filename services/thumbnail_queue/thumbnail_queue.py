import asyncio
import time

import sqlalchemy as sa
from sqlalchemy.orm import selectinload

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.app.models import async_plain_session_factory, init_db
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
            async with async_plain_session_factory() as session:
                obj, err = await fetch_obj(session)
                if err is not None:
                    log(f"Error fetching object with missing thumbnails: {str(err)}")
                    await asyncio.sleep(1)
                elif obj is None:
                    await asyncio.sleep(5)
                else:
                    log(f"Processing thumbnail request for object {obj.id}.")
                    try:
                        existing_thumbnail_types = [
                            thumb.type for thumb in obj.thumbnails
                        ]
                        thumbnails = list(
                            THUMBNAIL_TYPES - set(existing_thumbnail_types)
                        )
                        if len(thumbnails) > 0:
                            await obj.add_linked_thumbnails(thumbnails, session)
                            internal_key = obj.internal_key
                        else:
                            log(f"Source {obj.id} has all thumbnails.")
                    except Exception as e:
                        log(
                            f"Error processing thumbnail request for object {obj.id}: {str(e)}"
                        )
                        if isinstance(e, sa.exc.SQLAlchemyError):
                            try:
                                await session.rollback()
                            except Exception as rollback_err:
                                log(
                                    f"Error rolling back session after thumbnail failure for object {obj.id}: {str(rollback_err)}"
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
