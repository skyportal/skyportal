import functools
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


# Decorator that defers a function until the app is loaded: when the wrapped
# function is called, poll until the app responds, then run it (passing through
# the args given to check_loaded, e.g. logger=log).
#
# The wait/run happens at *call* time rather than at decoration time so that
# importing the module has no side effects and the decorated name stays callable.
# (Previously this ran the function during decoration and returned None, so a
# service whose function returned early -- e.g. on missing config -- left
# `service` bound to None and the `service()` call in __main__ blew up with
# "'NoneType' object is not callable" instead of exiting cleanly.)
def check_loaded(*args, **kwargs):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*_wrapper_args, **_wrapper_kwargs):
            while True:
                if is_loaded():
                    break
                elif kwargs.get("logger") is not None and callable(kwargs["logger"]):
                    kwargs["logger"]("Waiting for the app to start...")
                time.sleep(10)

            return func(*args, **kwargs)

        return wrapper

    return decorator
