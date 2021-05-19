#!/usr/bin/env python

import os
import time
from pathlib import Path


from baselayer.app.env import load_env


_, cfg = load_env()

try:
    expire_after_n_min = float(cfg["misc.minutes_to_keep_candidate_query_cache"])
except ValueError:
    raise ValueError(
        "Invalid (non-numeric) value provided for "
        "minutes_to_keep_candidate_query_cache in config file."
    )

cache_dir = Path("cache/candidate_queries")

for cache_file in cache_dir.glob("*.npy"):
    if (time.time() - cache_file.stat().st_mtime) > (expire_after_n_min * 60):
        try:
            os.remove(cache_file.absolute())
        except FileNotFoundError:
            pass
