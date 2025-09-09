import json

import requests

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log
from skyportal.models import Obj
from skyportal.utils.http import serialize_requests_response

log = make_log("hermes_submission_utils")

env, cfg = load_env()

HERMES_URL = cfg.get("app.hermes.endpoint")
HERMES_TOKEN = cfg.get("app.hermes.token")
HERMES_TOPIC = cfg.get("app.hermes.topic")
HERMES_TEST_TOPIC = cfg.get("app.hermes.test_topic", "skyportal.skyportal_test")


def check_hermes_configuration():
    """
    Check if the Hermes configuration is valid.
    """
    if not HERMES_URL:
        raise ValueError(
            "Hermes url is not configured. Please set 'app.hermes.endpoint' in the configuration. Skipping Hermes submission."
        )

    if not HERMES_TOKEN:
        raise ValueError(
            "Hermes token is not configured. Please set 'app.hermes.token' in the configuration. Skipping Hermes submission."
        )


def create_payload_and_header(obj, photometry, reporters, remarks, topic):
    """
    Create the payload and the header for Hermes and validate it by using the Hermes API
    """
    header = {
        "Authorization": f"Token {HERMES_TOKEN}",
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
        "topic": topic,
        "title": f"SkyPortal report for {obj.id}",
        "authors": reporters,
        "submitter": cfg.get("app.title", "SkyPortal"),
        "message_text": remarks or "",
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
        f"{HERMES_URL}/submit_message/validate/",
        data=payload,
        headers=header,
        timeout=5.0,
    )

    if response.status_code != 200:
        raise ValueError(
            f"Failed to validate payload: {response.status_code}: {response.text}"
        )


def submit_to_hermes(
    submission_request,
    sharing_service,
    user,
    photometry,
    reporters,
    remarks,
    session,
):
    flow = Flow()
    try:
        check_hermes_configuration()

        obj_id = submission_request.obj_id
        obj = session.scalar(Obj.select(user).where(Obj.id == obj_id))

        if sharing_service.testing:
            topic = HERMES_TEST_TOPIC
        elif HERMES_TOPIC is None:
            raise ValueError(
                "Hermes topic is not configured. Please set 'app.hermes.topic' in the configuration. Skipping Hermes submission."
            )
        else:
            topic = HERMES_TOPIC

        payload, header = create_payload_and_header(
            obj, photometry, reporters, remarks, topic
        )
        validate_payload_and_header(payload, header)
        response = requests.post(
            f"{HERMES_URL}/submit_message/",
            data=payload,
            headers=header,
            timeout=5.0,
        )
        if response.status_code != 200:
            log(
                f"Failed to publish to topic '{topic}' with status code {response.status_code}: {response.text}"
            )
            status = f"Error: Failed to publish to topic '{topic}' with status code {response.status_code}"
            notif_text = f"Hermes error: Failed to publish to topic '{topic}' with status code {response.status_code}"
        else:
            if sharing_service.testing:
                log(
                    f"Successfully submitted {obj_id} to Hermes test topic {topic} for sharing service {sharing_service.id}"
                )
                notif_text = (
                    f"Successfully submitted {obj_id} to Hermes test topic '{topic}'"
                )
                status = f"Testing mode, submitted to Hermes test topic '{topic}'."
            else:
                log(
                    f"Successfully submitted {obj_id} to Hermes with request ID {submission_request.id} for sharing service {sharing_service.id}"
                )
                status = f"Successfully submitted {obj_id} to Hermes."
                notif_text = status

        if isinstance(response, requests.models.Response):
            # we store the request's TNS response in the database for bookkeeping and debugging
            serialized_response = serialize_requests_response(response)
            submission_request.hermes_response = serialized_response
    except Exception as e:
        log(str(e))
        status = f"Error: {e}"
        notif_text = f"Hermes error: {e}"

    try:
        flow.push(
            "*",
            "skyportal/REFRESH_SHARING_SERVICE_SUBMISSIONS",
            payload={"sharing_service_id": sharing_service.id},
        )
        flow.push(
            user_id=submission_request.user_id,
            action_type="baselayer/SHOW_NOTIFICATION",
            payload={
                "note": notif_text,
                "type": "error" if "Error:" in status else "info",
                "duration": 8000,
            },
        )
    except Exception:
        pass

    submission_request.hermes_status = status
    session.commit()
