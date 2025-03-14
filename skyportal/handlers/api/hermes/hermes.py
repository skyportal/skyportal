import functools

import requests

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from baselayer.app.handlers.base import BaseHandler
from baselayer.log import make_log
from skyportal.models import Obj

env, cfg = load_env()
log = make_log("api/hermes")


def catch_timeout_and_no_endpoint(func):
    """
    Catch timeout and missing endpoint errors from the Hermes server
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.Timeout:
            raise ValueError("Unable to reach the Hermes server")
        except KeyError as e:
            if "endpoint" in str(e):
                raise ValueError("Hermes endpoint is missing from configuration")
            else:
                raise e

    return wrapper


def create_payload_and_header(obj, data):
    """
    Create the payload qnd the header for Hermes and validate it by using the Hermes API
    """
    header = {"Authorization": f"Token {data['hermes_token']}"}

    payload = {
        "topic": data["topic"],
        "title": data["title"],
        "submitter": data["submitter"],
        "data": {
            "targets": [
                {
                    "name": obj.id,
                    "ra": obj.ra,
                    "dec": obj.dec,
                }
            ],
            "photometry": [
                {
                    "target_name": obj.id,
                    "date_obs": p.jd,
                    "telescope": p.instrument.telescope.name,
                    "instrument": p.instrument.name,
                    "bandpass": p.filter,
                    "brightness": p.mag,
                    **({"brightness_error": p.e_mag} if p.e_mag else {}),
                    "unit": "AB mag",
                    **(
                        {
                            "limiting_brightness": p.limiting_mag,
                            "limiting_brightness_unit": "AB mag",
                        }
                        if p.original_user_data and p.original_user_data["limiting_mag"]
                        else {}
                    ),
                }
                for p in obj.photometry
            ],
        },
    }

    response = requests.post(
        f"{cfg['app.hermes_endpoint']}/submit_message/validate/",
        data=payload,
        headers=header,
        timeout=5.0,
    )

    if response.status_code != 200:
        raise ValueError(
            f"Failed to validate payload: {response.status_code}: {response.text}"
        )
    else:
        return payload, header


class HermesHandler(BaseHandler):
    @auth_or_token
    @catch_timeout_and_no_endpoint
    async def post(self, obj_id=None):
        if not obj_id:
            return self.error("Missing object ID")

        data = self.get_json()

        for field in ["hermes_token", "topic", "title", "submitter"]:
            if field not in data:
                return self.error(f"Missing required field: {field}")

        with self.Session() as session:
            obj = session.scalar(
                Obj.select(session.user_or_token, mode="read").where(Obj.id == obj_id)
            )

            if not obj:
                return self.error("Object not found")

            payload, header = create_payload_and_header(obj, data)

            response = requests.post(
                f"{cfg['app.hermes_endpoint']}/submit_message/",
                data=payload,
                headers=header,
                timeout=5.0,
            )

            if response.status_code != 200:
                return self.error(
                    f"Failed to publish to Hermes: status code {response.status_code}"
                )
