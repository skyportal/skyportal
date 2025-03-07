import functools
import requests
from baselayer.app.env import load_env
from . import FollowUpAPI

env, cfg = load_env()

def catch_timeout_and_no_endpoint(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.Timeout:
            raise ValueError("Unable to reach the MMT server")
        except KeyError as e:
            if "endpoint" in str(e):
                raise ValueError("MMT endpoint is missing from configuration")

    return wrapper

class MMTAPI(FollowUpAPI):
    """SkyPortal interface to the MMT"""

    @staticmethod
    @catch_timeout_and_no_endpoint
    def submit(request, session, **kwargs):
        return

    @staticmethod
    @catch_timeout_and_no_endpoint
    def get(request, session, **kwargs):
        return


    @staticmethod
    @catch_timeout_and_no_endpoint
    def delete(request, session, **kwargs):
        return

    form_json_schema = {
        "type": "object",
        "properties": {
        },
        "required": [
        ],
    }

    form_json_schema_altdata = {
        "type": "object",
        "properties": {
        },
        "required": [
        ],
    }
