__all__ = ["enqueue_backfill"]

import requests

from baselayer.app.env import load_env
from baselayer.log import make_log

_, cfg = load_env()
log = make_log("broker_backfill_utils")


def enqueue_backfill(broker_id, filter_id, user_id, **kwargs):
    """Ask the backfill service to ingest a broker's stored matches for a filter.

    Returns (accepted, message). The caller reports the message, so a service
    that is not running reads as a refusal rather than as a queued job nothing
    will run.
    """
    url = f"http://{cfg['hosts.broker_backfill']}:{cfg['ports.broker_backfill']}"
    payload = {
        "broker_id": broker_id,
        "filter_id": filter_id,
        "user_id": user_id,
        **kwargs,
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
    except Exception as e:
        log(f"could not reach the backfill queue ({e})")
        return False, "The backfill service is not reachable."
    if response.status_code == 200:
        return True, "Backfill queued."
    try:
        message = response.json().get("message") or response.text
    except Exception:
        message = response.text
    log(f"backfill queue refused filter {filter_id} ({message})")
    return False, message
