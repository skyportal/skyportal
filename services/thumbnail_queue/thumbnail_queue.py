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

env, cfg = load_env()
log = make_log('thumbnail_queue')

init_db(**cfg['database'])

queue = []

THUMBNAIL_TYPES = ["sdss", "ls", "ps1"]


def fetch_obj_ids():
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
                .having(sa.func.count(Thumbnail.obj_id) == len(THUMBNAIL_TYPES))
            )
        )
        .order_by(Obj.created_at.desc())
        .limit(1)
    )

    with DBSession() as session:
        objs = session.execute(stmt).all()

    objs_ids = [str(o.id) for o in objs]
    return objs_ids


def service():
    while True:
        try:
            obj_ids = fetch_obj_ids()
            if len(obj_ids) == 0:
                time.sleep(5)
                continue
            for obj_id in obj_ids:
                internal_key = None
                with DBSession() as session:
                    try:
                        obj = session.scalars(
                            sa.select(Obj).where(Obj.id == obj_id)
                        ).first()
                        if obj is None:
                            log(f"Source {obj_id} not found")
                            continue

                        existing_thumbnail_types = [
                            thumb.type for thumb in obj.thumbnails
                        ]
                        thumbnails = list(
                            set(THUMBNAIL_TYPES) - set(existing_thumbnail_types)
                        )
                        if len(thumbnails) == 0:
                            log(f"Source {obj_id} has all thumbnails.")
                            continue

                        obj.add_linked_thumbnails(thumbnails, session)
                        internal_key = obj.internal_key
                    except Exception as e:
                        log(
                            f"Error processing thumbnail request for object {obj_id}: {str(e)}"
                        )
                        session.rollback()
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


if __name__ == "__main__":
    try:
        log("Starting thumbnail queue...")
        service()
    except Exception as e:
        log(f"Error starting thumbnail queue: {str(e)}")
        raise e
