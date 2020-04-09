#!/usr/bin/env python

import datetime
from skyportal.models import init_db, Source, DBSession
from baselayer.app.env import load_env


env, cfg = load_env()
init_db(**cfg["database"])

cutoff_datetime = datetime.datetime.now() - datetime.timedelta(
    days=cfg["misc.days_to_keep_unsaved_candidates"]
)

n_deleted = (
    Source.query
    .filter(Source.is_candidate.is_(True))
    .filter(Source.is_source.is_(False))
    .filter(Source.created_at <= cutoff_datetime)
    .delete()
)

DBSession.commit()

print(f"Deleted {n_deleted} unsaved candidates.")
