#!/usr/bin/env python

import datetime
from skyportal.models import init_db, Source, DBSession
from baselayer.app.env import load_env


env, cfg = load_env()
init_db(**cfg["database"])

try:
    n_days = int(cfg["misc.days_to_keep_unsaved_candidates"])
except ValueError:
    raise ValueError("Invalid (non-integer) value provided for "
                     "days_to_keep_unsaved_candidates in config file.")

if not 1 <= n_days <= 30:
    raise ValueError("days_to_keep_unsaved_candidates must be an integer between 1 and 30")

cutoff_datetime = datetime.datetime.now() - datetime.timedelta(days=n_days)

n_deleted = (
    Source.query
    .filter(Source.is_candidate.is_(True))
    .filter(Source.is_source.is_(False))
    .filter(Source.created_at <= cutoff_datetime)
    .delete()
)

DBSession.commit()

print(f"Deleted {n_deleted} unsaved candidates.")
