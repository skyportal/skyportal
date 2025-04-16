import functools
import json

import requests
from models import TNSRobot

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from baselayer.app.handlers.base import BaseHandler
from baselayer.log import make_log
from skyportal.models import Obj

from ....models import Instrument
from ....utils.tns import TNS_INSTRUMENT_IDS
from ..tns.obj_tns import check_instruments, check_streams

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
    header = {
        "Authorization": f"Token {cfg['app.hermes.token']}",
        "Content-Type": "application/json",
    }

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
                            "limiting_brightness": p.original_user_data["limiting_mag"],
                            "limiting_brightness_unit": "AB mag",
                        }
                        if p.original_user_data
                        and "limiting_mag" in p.original_user_data
                        else {}
                    ),
                }
                for p in obj.photometry
            ],
        },
    }

    return json.dumps(payload), header


def validate_payload_and_header(payload, header):
    response = requests.post(
        f"{cfg['app.hermes.endpoint']}/submit_message/validate/",
        data=payload,
        headers=header,
        timeout=5.0,
    )

    if response.status_code != 200:
        raise ValueError(
            f"Failed to validate payload: {response.status_code}: {response.text}"
        )


class HermesHandler(BaseHandler):
    @auth_or_token
    @catch_timeout_and_no_endpoint
    async def post(self, obj_id=None):
        """
        ---
        description: Publish a message to Hermes
        Tags:
          - Hermes
        parameters:
          - in: path
            name: obj_id
            required: true
            description: Object ID
            schema:
              type: string
          - in: query
            name: tnsrobotID
            required: true
            description: TNS robot ID
            schema:
              type: string
          - in: query
            name: instrument_ids
            required: true
            description: List of instrument IDs
            schema:
                type: array
                items:
                    type: string
          - in: query
            name: stream_ids
            required: true
            description: List of stream IDs
            schema:
                type: array
                items:
                    type: string
          - in: query
            name: topic
            required: true
            description: Topic to publish to
            schema:
              type: string
          - in: query
            name: title
            required: true
            description: Title of the message
            schema:
              type: string
          - in: query
            name: submitter
            required: true
            description: Submitter of the message
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        if not obj_id:
            return self.error("Missing object ID")

        data = self.get_json()

        for required_data in [
            "tnsrobotID",
            "topic",
            "title",
            "submitter",
            "instrument_ids",
            "stream_ids",
        ]:
            if required_data not in data:
                return self.error(f"Missing required field: {required_data}")

        if cfg["app.hermes.endpoint"] is None:
            return self.error("Hermes endpoint is not configured")
        if cfg["app.hermes.token"] is None:
            return self.error("Hermes token is not configured")
        with self.Session() as session:
            tnsrobotID = data["tnsrobotID"]
            instrument_ids = data["instrument_ids"]
            stream_ids = data.get("stream_ids")

            check_instruments(session, instrument_ids)
            check_streams(session, stream_ids)

            obj = session.scalar(
                Obj.select(session.user_or_token, mode="read").where(Obj.id == obj_id)
            )
            if not obj:
                return self.error("Object not found")

            tnsrobot = session.scalars(
                TNSRobot.select(session.user_or_token).where(TNSRobot.id == tnsrobotID)
            ).first()
            if tnsrobot is None:
                return self.error(f"No TNSRobot available with ID {tnsrobotID}")

            payload, header = create_payload_and_header(obj, data)
            validate_payload_and_header(payload, header)

            if tnsrobot.testing:
                return self.success()

            response = requests.post(
                f"{cfg['app.hermes.endpoint']}/submit_message/",
                data=payload,
                headers=header,
                timeout=5.0,
            )

            if response.status_code != 200:
                return self.error(
                    f"Failed to publish to Hermes: status code {response.status_code}"
                )
            return self.success()
