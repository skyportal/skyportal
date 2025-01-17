import time

import requests

from baselayer.app.env import load_env

env, cfg = load_env()

REQUEST_TIMEOUT_SECONDS = cfg["health_monitor.request_timeout_seconds"]

HOST = f"{cfg['server.protocol']}://{cfg['server.host']}" + (
    f":{cfg['server.port']}" if cfg["server.port"] not in [80, 443] else ""
)


def is_loaded():
    try:
        r = requests.get(f"{HOST}/api/sysinfo", timeout=REQUEST_TIMEOUT_SECONDS)
    except Exception:
        status_code = 0
    else:
        status_code = r.status_code

    if status_code == 200:
        return True
    else:
        return False


# provide a decorator to wrap a function with a check for whether the app is loaded
# if not loaded, keep looping until it is, with a 15 second sleep between attempts
def check_loaded(*args, **kwargs):
    def decorator(func):
        while True:
            if is_loaded():
                break
            elif kwargs.get("logger") is not None and callable(kwargs["logger"]):
                kwargs["logger"]("Waiting for the app to start...")
            time.sleep(10)

        func(*args, **kwargs)

    return decorator
