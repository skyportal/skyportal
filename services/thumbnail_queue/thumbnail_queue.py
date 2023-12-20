import time

import sqlalchemy as sa

from baselayer.app.models import init_db
from baselayer.app.env import load_env
from baselayer.log import make_log
from baselayer.app.flow import Flow

from skyportal.models import (
    DBSession,
    Obj,
    Thumbnail,
)
from skyportal.utils.services import check_loaded

env, cfg = load_env()
log = make_log('thumbnail_queue')

init_db(**cfg['database'])

THUMBNAIL_TYPES = ["sdss", "ls", "ps1"]


def fetch_obj(session):
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
                    sa.func.count(sa.distinct(Thumbnail.type)) == len(THUMBNAIL_TYPES)
                )
            )
        )
        .order_by(Obj.created_at.desc())
        .limit(1)
    )
    objs = session.execute(stmt).scalars().all()
    if len(objs) == 0:
        return None
    else:
        return session.scalar(sa.select(Obj).where(Obj.id == objs[0]))


@check_loaded(logger=log)
def service(*args, **kwargs):
    while True:
        try:
            internal_key = None
            with DBSession() as session:
                try:
                    obj = fetch_obj(session)
                except Exception as e:
                    log(f"Error fetching object with missing thumbnails: {str(e)}")
                    time.sleep(5)
                    continue

                if obj is None:
                    time.sleep(5)
                    continue

                log(f"Processing thumbnail request for object {obj.id}.")

                try:
                    existing_thumbnail_types = [thumb.type for thumb in obj.thumbnails]
                    thumbnails = list(
                        set(THUMBNAIL_TYPES) - set(existing_thumbnail_types)
                    )
                    if len(thumbnails) == 0:
                        log(f"Source {obj.id} has all thumbnails.")
                        continue

                    obj.add_linked_thumbnails(thumbnails, session)
                    internal_key = obj.internal_key
                except Exception as e:
                    log(
                        f"Error processing thumbnail request for object {obj.id}: {str(e)}"
                    )
                    session.rollback()
                    continue

            if internal_key is None:
                continue

            flow = Flow()
            flow.push(
                '*',
                "skyportal/REFRESH_SOURCE",
                payload={"obj_key": internal_key},
            )
            flow.push(
                '*',
                "skyportal/REFRESH_CANDIDATE",
                payload={"id": internal_key},
            )
        except Exception as e:
            log(f"Error processing thumbnail request: {str(e)}")
            time.sleep(5)


if __name__ == "__main__":
    try:
        service()
    except Exception as e:
        log(f"Error starting thumbnail queue: {str(e)}")
        raise e
