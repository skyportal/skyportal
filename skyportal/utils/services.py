import functools
import time

import requests

from baselayer.app.env import load_env

from .app import get_app_base_url

env, cfg = load_env()

REQUEST_TIMEOUT_SECONDS = cfg["health_monitor.request_timeout_seconds"]

HOST = get_app_base_url()

# Probed directly: behind nginx, a failed probe takes a worker down for server.fail_timeout.
READINESS_PORTS = [
    cfg["ports.app_internal"] + i for i in range(cfg["server.processes"])
]


def is_loaded():
    for port in READINESS_PORTS:
        try:
            r = requests.get(
                f"http://localhost:{port}/api/sysinfo",
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except Exception:
            continue
        if r.status_code == 200:
            return True
    return False


# Polls at call time, not at decoration time, so the decorated name stays callable.
def check_loaded(*args, **kwargs):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*_wrapper_args, **_wrapper_kwargs):
            logger = kwargs.get("logger")
            while not is_loaded():
                if callable(logger):
                    logger("Waiting for the app to start...")
                time.sleep(10)

            return func(*args, **kwargs)

        return wrapper

    return decorator
