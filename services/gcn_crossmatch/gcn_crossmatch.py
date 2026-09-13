"""Runner for the GCN alert crossmatch.

All the logic lives in ``skyportal.utils.gcn_crossmatch`` so it can be imported
and tested without this module's ``init_db`` rebinding the session. This file
only reads configuration and drives the loop.
"""

import asyncio
import time
import traceback

from baselayer.app.env import load_env
from baselayer.app.models import init_db
from baselayer.log import make_log
from skyportal.utils.gcn_crossmatch import run_cycle
from skyportal.utils.services import check_loaded

env, cfg = load_env()

init_db(**cfg["database"])

log = make_log("gcn_crossmatch")


def is_configured(config):
    if not config.get("enabled", False):
        log("GCN crossmatch is disabled, skipping")
        return False
    return True


@check_loaded(logger=log)
def service(*args, **kwargs):
    config = cfg.get("gcn_crossmatch", {}) or {}
    if not is_configured(config):
        return

    interval = float(config.get("poll_interval", 300))
    log(f"Crossmatching GCN localizations against brokers every {interval:.0f}s")

    while True:
        try:
            matched = asyncio.run(run_cycle(config))
            if matched:
                log(f"Saved {matched} new crossmatch(es)")
        except Exception as e:
            traceback.print_exc()
            log(f"Crossmatch cycle failed: {e}")
        time.sleep(interval)


if __name__ == "__main__":
    try:
        service()
    except Exception as e:
        log(f"Error: {e}")
