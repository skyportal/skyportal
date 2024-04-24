import uuid

import asyncio

from baselayer.app.models import session_context_id
from baselayer.log import make_log

log = make_log("async")


def run_async(func, *args, **kwargs):
    """Run any method using the database asynchronously, in its own session scope

    Parameters
    ----------
    func: function
        The function to call in its own async scope
    args: list
        Arguments passed to the method, in order
    kwargs: dict
        kwargs pased to the method
    """

    def wrapper():
        session_context_id.set(str(uuid.uuid4()))
        try:
            func(*args, **kwargs)
        except Exception as e:
            log(f"Error running async function {func.__name__}: {e}")

    try:
        event_loop = asyncio.get_event_loop()
    except Exception:
        event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(event_loop)
    event_loop.run_in_executor(None, wrapper)
