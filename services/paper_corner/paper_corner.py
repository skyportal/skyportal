import time
import uuid
from datetime import UTC, datetime, timedelta

import requests
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert

from baselayer.app.env import load_env
from baselayer.app.models import DBSession, init_db, session_context_id
from baselayer.log import make_log
from skyportal.models import Obj, PaperCornerCache, Source, tns_paper_sources
from skyportal.utils.paper_corner import paper_corner_enabled, search_ads
from skyportal.utils.services import check_loaded

_, cfg = load_env()
log = make_log("paper_corner")


def refresh(batch_size):
    session_context_id.set(uuid.uuid4().hex)
    now = datetime.now(UTC)
    cache = PaperCornerCache.c
    eligible = tns_paper_sources(
        sa.select(Source.obj_id, Obj.tns_name).select_from(Source),
        cfg["misc.public_group_name"],
    ).outerjoin(
        PaperCornerCache,
        sa.and_(cache.obj_id == Source.obj_id, cache.tns_name == Obj.tns_name),
    )
    with DBSession() as session:
        batch = session.execute(
            eligible.where(
                sa.or_(
                    cache.checked_at.is_(None),
                    cache.checked_at < now - timedelta(days=7),
                )
            )
            .order_by(
                (
                    Source.saved_at >= now.replace(tzinfo=None) - timedelta(days=30)
                ).desc(),
                cache.checked_at.asc().nulls_first(),
                Source.saved_at.desc(),
                Source.obj_id,
            )
            .limit(batch_size)
        ).all()

    for obj_id, tns_name in batch:
        checked_at = datetime.now(UTC)
        try:
            matches = search_ads(tns_name, cfg["paper_corner.ads_token"])
        except requests.HTTPError as exc:
            status = exc.response.status_code
            if status in {401, 403, 429} or status >= 500:
                raise
            log(f"ADS returned HTTP {status} for a TNS source")
            continue
        with DBSession() as session:
            stmt = insert(PaperCornerCache).values(
                obj_id=obj_id,
                tns_name=tns_name,
                checked_at=checked_at,
                matches=matches,
            )
            session.execute(
                stmt.on_conflict_do_update(
                    index_elements=[cache.obj_id],
                    set_={
                        "tns_name": stmt.excluded.tns_name,
                        "checked_at": stmt.excluded.checked_at,
                        "matches": stmt.excluded.matches,
                    },
                    where=cache.checked_at <= stmt.excluded.checked_at,
                )
            )
            session.commit()


@check_loaded(logger=log)
def service():
    interval = max(3600, int(cfg["paper_corner.refresh_interval_seconds"]))
    batch_size = max(1, int(cfg["paper_corner.batch_size"]))
    while True:
        try:
            refresh(batch_size)
        except Exception as exc:
            # HTTP errors can contain the full designation query.
            log(f"Paper Corner refresh failed ({type(exc).__name__})")
        time.sleep(interval)


if __name__ == "__main__" and paper_corner_enabled(cfg):
    init_db(**cfg["database"])
    service()
