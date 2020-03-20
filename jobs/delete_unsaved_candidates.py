#!/usr/bin/env python

import datetime
from skyportal.models import init_db, Candidate, DBSession
from baselayer.app.env import load_env


env, cfg = load_env()
init_db(**cfg["database"])

cutoff_datetime = datetime.datetime.now() - datetime.timedelta(
    days=cfg["misc"]["days_to_keep_unsaved_candidates"]
)

c = Candidate.query.filter(Candidate.source_id.is_(None)).filter(
    Candidate.created_at <= cutoff_datetime
).delete()

DBSession.commit()

print("Deleted", c, "unsaved candidates.")
