#!/usr/bin/env python

import arrow
import sqlalchemy as sa

from baselayer.app.env import load_env
from skyportal.models import DBSession, Obj, init_db
from skyportal.utils.candidates import stale_unsaved_candidates

BATCH_SIZE = 100

_, cfg = load_env()
init_db(**cfg["database"])

months = cfg["misc.months_to_keep_unsaved_candidates"]
criteria = stale_unsaved_candidates(arrow.utcnow().shift(months=-months).naive)
n_deleted = 0

with DBSession() as session:
    obj_ids = session.scalars(sa.select(Obj.id).where(criteria)).all()
    for i in range(0, len(obj_ids), BATCH_SIZE):
        # Objects may be saved or pass a filter again during the run.
        objs = session.scalars(
            sa.select(Obj).where(Obj.id.in_(obj_ids[i : i + BATCH_SIZE]), criteria)
        ).all()
        for obj in objs:
            session.delete(obj)
        session.commit()
        n_deleted += len(objs)

print(
    f"Deleted {n_deleted} of {len(obj_ids)} unsaved candidates "
    f"older than {months} months."
)
