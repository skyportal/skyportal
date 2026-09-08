"""NEOFixer target-list ingestion service.

Polls NEOFixer's per-site target list and annotates the solar system objects
SkyPortal already tracks with its score and priority. Enable with
`neofixer.enabled: true` in the config.
"""

import time
import uuid

from baselayer.app.env import load_env
from baselayer.app.models import DBSession, init_db, session_context_id
from baselayer.log import make_log
from skyportal.utils.neofixer import annotate_matching_objects, fetch_targets
from skyportal.utils.services import check_loaded

env, cfg = load_env()
log = make_log("neofixer_service")

init_db(**cfg["database"])

neofixer_cfg = cfg.get("neofixer", {})

enabled = neofixer_cfg.get("enabled", False)
endpoint = neofixer_cfg.get("endpoint")
site = neofixer_cfg.get("site")
interval = neofixer_cfg.get("interval_seconds", 3600)
timeout = neofixer_cfg.get("timeout_seconds", 300)
group_ids = neofixer_cfg.get("group_ids") or []
bot_user_id = neofixer_cfg.get("bot_user_id")


def is_configured():
    if not enabled:
        log("NEOFixer ingestion disabled (set neofixer.enabled: true to enable)")
        return False
    required = {
        "neofixer.endpoint": endpoint,
        "neofixer.site": site,
        "neofixer.bot_user_id": bot_user_id,
        "neofixer.group_ids": group_ids,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        log(f"Not polling NEOFixer, missing config: {', '.join(missing)}")
        return False
    return True


def poll_once():
    payload = fetch_targets(endpoint, site, timeout)
    generated = (payload.get("result") or {}).get("generated") or {}
    session_context_id.set(uuid.uuid4().hex)
    with DBSession() as session:
        try:
            counts = annotate_matching_objects(session, payload, bot_user_id, group_ids)
            session.commit()
        except Exception:
            session.rollback()
            raise
    log(
        f"NEOFixer list of {generated.get('time')}: matched {counts['matched']} of "
        f"{counts['considered']} tracked objects "
        f"({counts['created']} new, {counts['updated']} updated)"
    )


@check_loaded(logger=log)
def service(*args, **kwargs):
    log(f"Polling NEOFixer site {site} every {interval}s")
    while True:
        try:
            poll_once()
        except Exception as e:
            log(f"Error polling NEOFixer: {e}")
        time.sleep(interval)


if __name__ == "__main__":
    try:
        if is_configured():
            service()
    except Exception as e:
        log(f"Error starting NEOFixer service: {e}")

    # Idle rather than exit so supervisor doesn't restart-loop.
    while True:
        time.sleep(3600)
