"""TESS sector coverage service.

Loads each TESS sector's four camera footprints as instrument fields, then
annotates objects with the sectors covering them so scanning can filter on
TESS coverage. Enable with `tess.enabled: true` in the config.
"""

import time
import uuid

import sqlalchemy as sa

from baselayer.app.env import load_env
from baselayer.app.models import DBSession, init_db, session_context_id
from baselayer.log import make_log
from skyportal.models import Annotation, Candidate, Instrument, InstrumentField, Obj
from skyportal.utils.services import check_loaded
from skyportal.utils.tess import (
    ANNOTATION_ORIGIN,
    INSTRUMENT_NAME,
    camera_region,
    current_sector,
    missing_field_data,
)
from skyportal.utils.tess_ingest import annotate_object

env, cfg = load_env()
log = make_log("tess_sector")

init_db(**cfg["database"])

tess_cfg = cfg.get("tess", {})

enabled = tess_cfg.get("enabled", False)
instrument_name = tess_cfg.get("instrument_name", INSTRUMENT_NAME)
interval = tess_cfg.get("interval_seconds", 3600)
batch_size = tess_cfg.get("batch_size", 500)
group_ids = tess_cfg.get("group_ids") or []
bot_user_id = tess_cfg.get("bot_user_id")


def is_configured():
    if not enabled:
        log("TESS sector service disabled (set tess.enabled: true to enable)")
        return False
    missing = [
        name
        for name, value in {
            "tess.bot_user_id": bot_user_id,
            "tess.group_ids": group_ids,
        }.items()
        if not value
    ]
    if missing:
        log(f"Not annotating TESS coverage, missing config: {', '.join(missing)}")
        return False
    return True


def find_instrument(session):
    return session.scalar(
        sa.select(Instrument).where(Instrument.name == instrument_name)
    )


def load_fields(session, instrument):
    """Add fields for any sector that does not have them yet."""
    from skyportal.handlers.api.instrument import add_tiles

    existing = session.scalars(
        sa.select(InstrumentField.field_id).where(
            InstrumentField.instrument_id == instrument.id
        )
    ).all()
    field_data = missing_field_data(existing)
    if field_data is None:
        return 0

    add_tiles(
        instrument.id,
        instrument.name,
        camera_region(),
        field_data,
        session=session,
    )
    session.commit()
    return len(field_data["ID"])


def stale_obj_ids(now):
    """Objects whose stored annotation disagrees with the sector observing now.

    `sectors` only grows, but which one is current changes every few weeks, so an
    annotation goes stale where the object did not.
    """
    stored = Annotation.data["in_current_sector"].astext.cast(sa.Boolean)
    if now is None:
        # Between sectors nothing is in one, so any stored true is stale.
        stale = stored.is_(True)
    else:
        in_now = Annotation.data["sectors"].contains(sa.func.to_jsonb(sa.literal(now)))
        stale = stored.is_distinct_from(in_now)
    return (
        sa.select(Annotation.obj_id)
        .where(Annotation.origin == ANNOTATION_ORIGIN, stale)
        .scalar_subquery()
    )


def annotate_batch(session, instrument):
    """Annotate candidates with no TESS annotation, and refresh stale ones."""
    annotated = (
        sa.select(Annotation.obj_id)
        .where(Annotation.origin == ANNOTATION_ORIGIN)
        .scalar_subquery()
    )
    objs = session.scalars(
        sa.select(Obj)
        .where(
            Obj.id.in_(sa.select(Candidate.obj_id)),
            Obj.healpix.isnot(None),
            sa.or_(
                Obj.id.notin_(annotated),
                Obj.id.in_(stale_obj_ids(current_sector())),
            ),
        )
        .limit(batch_size)
    ).all()
    for obj in objs:
        annotate_object(session, obj, instrument.id, bot_user_id, group_ids)
    session.commit()
    return len(objs)


def poll_once():
    session_context_id.set(uuid.uuid4().hex)
    with DBSession() as session:
        instrument = find_instrument(session)
        if instrument is None:
            log(f"No instrument named {instrument_name}; create it to load fields")
            return
        added = load_fields(session, instrument)
        if added:
            log(f"Loaded {added} TESS camera footprints")
        annotated = annotate_batch(session, instrument)
        if annotated:
            log(f"Annotated TESS coverage for {annotated} objects")


@check_loaded(logger=log)
def service(*args, **kwargs):
    log(f"Annotating TESS coverage every {interval}s")
    while True:
        try:
            poll_once()
        except Exception as e:
            log(f"Error annotating TESS coverage: {e}")
        time.sleep(interval)


if __name__ == "__main__":
    try:
        if is_configured():
            service()
    except Exception as e:
        log(f"Error starting TESS sector service: {e}")

    # Idle rather than exit so supervisor doesn't restart-loop.
    while True:
        time.sleep(3600)
