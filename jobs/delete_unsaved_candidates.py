#!/usr/bin/env python

import datetime
from skyportal.models import Candidate, DBSession
from baselayer.app.env import load_env


env, cfg = load_env()
cutoff_datetime = datetime.datetime.now() - datetime.timedelta(
    days=cfg["misc"]["days_to_keep_unsaved_candidates"]
)

Candidate.query.filter(Candidate.source_id.is_(None)).filter(
    Candidate.created_at <= cutoff_datetime
).delete()

DBSession.commit()
