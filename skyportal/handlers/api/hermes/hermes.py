import functools
import json

import requests

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.app.handlers.base import BaseHandler
from baselayer.log import make_log

from ....models import TNSRobot
from ....utils.data_access import get_publishable_obj_photometry

_, cfg = load_env()
log = make_log("api/hermes")

is_configured = (
    cfg.get("app.hermes.endpoint")
    and cfg.get("app.hermes.topic")
    and cfg.get("app.hermes.token")
)


def catch_timeout_and_no_endpoint(func):
    """
    Catch timeout and missing endpoint errors from the Hermes server
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not is_configured:
            raise ValueError("This instance is not configured to use Hermes")
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


def create_payload_and_header(obj, photometry, data):
    """
    Create the payload qnd the header for Hermes and validate it by using the Hermes API
    """
    header = {
        "Authorization": f"Token {cfg['app.hermes.token']}",
        "Content-Type": "application/json",
    }

    payload_photometry = []
    for p in photometry:
        p_dict = p.to_dict_public()
        payload_photometry.append(
            {
                "target_name": obj.id,
                "date_obs": p.jd,
                "telescope": p.instrument.telescope.name,
                "instrument": p_dict.get("instrument_name"),
                "bandpass": p_dict.get("filter"),
                "brightness": p_dict.get("mag"),
                "brightness_error": p_dict["magerr"],
                "unit": "AB mag",
                "limiting_brightness": p_dict.get("limiting_mag"),
                "limiting_brightness_unit": "AB mag",
            }
        )

    payload = {
        "topic": cfg["app.hermes.topic"],
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
            "photometry": payload_photometry,
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
            name: tns_robot_id
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
          - in: query
            name: photometry_options
            required: true
            description: Photometry options
            schema:
              type: object
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
            "tns_robot_id",
            "title",
            "submitter",
            "instrument_ids",
            "stream_ids",
        ]:
            if required_data not in data:
                return self.error(f"Missing required field: {required_data}")

        with self.Session() as session:
            tns_robot_id = data["tns_robot_id"]
            instrument_ids = data["instrument_ids"]
            stream_ids = data.get("stream_ids")
            photometry_options = data.get("photometry_options")

            source, photometry = get_publishable_obj_photometry(
                session,
                self.current_user,
                tns_robot_id,
                obj_id,
                instrument_ids,
                stream_ids,
                photometry_options,
            )

            payload, header = create_payload_and_header(source, photometry, data)
            validate_payload_and_header(payload, header)

            tns_robot = session.scalars(
                TNSRobot.select(session.user_or_token).where(
                    TNSRobot.id == tns_robot_id
                )
            ).first()
            if tns_robot is None:
                return self.error(f"TNSRobot {tns_robot_id} not found")
            if tns_robot.testing:
                self.push(
                    action="baselayer/SHOW_NOTIFICATION",
                    payload={
                        "note": "Payload validated successfully (testing mode, not sent to Hermes)",
                        "type": "info",
                    },
                )
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
