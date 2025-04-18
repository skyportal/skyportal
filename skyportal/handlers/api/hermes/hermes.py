import functools
import json

import requests

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.app.handlers.base import BaseHandler
from baselayer.log import make_log

# from services.tns_submission_queue.tns_submission_queue import (
#     TNSReportError,
#     validate_obj_id,
# )
from skyportal.models import Obj, Source, TNSRobot

from ..tns.tns_robot import (
    check_instruments,
    check_streams,
    validate_photometry_options,
)

_, cfg = load_env()
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
            tns_robot_id = data["tns_robot_id"]
            instrument_ids = data["instrument_ids"]
            stream_ids = data.get("stream_ids")
            photometry_options = data.get("photometry_options")

            check_instruments(session, instrument_ids)
            check_streams(session, stream_ids)

            obj = session.scalar(
                Obj.select(session.user_or_token, mode="read").where(Obj.id == obj_id)
            )
            if not obj:
                return self.error("Object not found")

            tns_robot = session.scalars(
                TNSRobot.select(session.user_or_token).where(
                    TNSRobot.id == tns_robot_id
                )
            ).first()
            if tns_robot is None:
                return self.error(f"TNSRobot not available")

            # Check if the user has access to the TNSRobot
            accessible_group_ids = [g.id for g in self.current_user.accessible_groups]
            tns_robot_groups = [
                tns_robot_group
                for tns_robot_group in tns_robot.groups
                if tns_robot_group.group_id in accessible_group_ids
            ]
            if len(tns_robot_groups) == 0:
                raise ValueError(
                    f"User {self.current_user.id} does not have access to any group with TNSRobot {tns_robot_id}"
                )

            request_headers = {
                "User-Agent": f'tns_marker{{"tns_id":{tns_robot.bot_id},"type":"bot", "name":"{tns_robot.bot_name}"}}'
            }

            photometry_options = validate_photometry_options(
                photometry_options, tns_robot.photometry_options
            )

            # try:
            #     validate_obj_id(obj_id, tns_robot.source_group_id)
            # except TNSReportError as e:
            #     return self.error(e)

            source = session.scalar(
                Source.select(session.user_or_token)
                .where(
                    Source.obj_id == obj_id,
                    Source.active.is_(True),
                    Source.group_id.in_([group.group_id for group in tns_robot_groups]),
                )
                .order_by(Source.saved_at.asc())
            )
            if source is None:
                return self.error(
                    f"Source {obj_id} not saved to any group with TNSRobot {tns_robot_id}."
                )

            return source

            payload, header = create_payload_and_header(obj, data)
            validate_payload_and_header(payload, header)

            if tns_robot.testing:
                try:
                    flow = Flow()
                    flow.push(
                        action_type="baselayer/SHOW_NOTIFICATION",
                        payload={
                            "note": "Successfully validate by the API (testing mode, not sent to Hermes)",
                            "type": "info",
                        },
                    )
                except Exception:
                    pass
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
