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

BATCH_SIZE = 10
THUMBNAIL_TYPES = ["sdss", "ls", "ps1"]


def fetch_obj_ids():
    subquery = (
        sa.select(Thumbnail.obj_id)
        .where(Thumbnail.type.in_(THUMBNAIL_TYPES))
        .group_by(Thumbnail.obj_id)
        .having(sa.func.count(Thumbnail.obj_id) == len(THUMBNAIL_TYPES))
        .alias()
    )
    stmt = (
        sa.select(Obj.id, Obj.created_at)
        .outerjoin(subquery, Obj.id == subquery.c.obj_id)
        .filter(subquery.c.obj_id.is_(None))
    )
    # sort by created_at, most recent first
    stmt = stmt.order_by(sa.desc(Obj.created_at))
    # limit to 10 objects
    stmt = stmt.limit(BATCH_SIZE)

    with DBSession() as session:
        objs = session.execute(stmt).all()

    objs = sorted(objs, key=lambda o: o.created_at, reverse=True)
    objs_ids = [str(o.id) for o in objs]
    return objs_ids


def service():
    while True:
        try:
            obj_ids = fetch_obj_ids()
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
