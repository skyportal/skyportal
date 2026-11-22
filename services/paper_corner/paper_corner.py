import time
import uuid

import requests
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert

from baselayer.app.env import load_env
from baselayer.app.models import DBSession, init_db, session_context_id
from baselayer.log import make_log
from skyportal.models import Group, PaperCornerCache, Source
from skyportal.utils.paper_corner import paper_corner_enabled, search_ads
from skyportal.utils.services import check_loaded

_, cfg = load_env()
log = make_log("paper_corner")


def refresh():
    session_context_id.set(uuid.uuid4().hex)
    sources = cfg["paper_corner.sources"]
    with DBSession() as session:
        public_objects = session.scalars(
            sa.select(Source.obj_id)
            .join(Group, Source.group_id == Group.id)
            .where(
                Group.name == cfg["misc.public_group_name"],
                Source.active.is_(True),
                Source.obj_id.in_(list(sources)),
            )
            .distinct()
        ).all()

    for obj_id in public_objects:
        try:
            matches = [
                match
                for designation in dict.fromkeys(sources[obj_id])
                for match in search_ads(designation, cfg["paper_corner.ads_token"])
            ]
        except requests.HTTPError as exc:
            status = exc.response.status_code
            if status in {401, 403, 429} or status >= 500:
                raise
            log(f"ADS returned HTTP {status} for a configured source")
            continue
        with DBSession() as session:
            stmt = insert(PaperCornerCache).values(obj_id=obj_id, matches=matches)
            session.execute(
                stmt.on_conflict_do_update(
                    index_elements=[PaperCornerCache.c.obj_id],
                    set_={"matches": stmt.excluded.matches},
                )
            )
            session.commit()


@check_loaded(logger=log)
def service():
    interval = max(3600, int(cfg["paper_corner.refresh_interval_seconds"]))
    while True:
        try:
            refresh()
        except Exception as exc:
            # HTTP errors can contain the full designation query.
            log(f"Paper Corner refresh failed ({type(exc).__name__})")
        time.sleep(interval)


if __name__ == "__main__" and paper_corner_enabled(cfg):
    init_db(**cfg["database"])
    service()
