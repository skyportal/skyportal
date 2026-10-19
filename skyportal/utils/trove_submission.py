import requests

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log
from skyportal.models import Obj
from skyportal.utils.http import serialize_requests_response

log = make_log("trove_submission_utils")

env, cfg = load_env()

TROVE_URL = cfg.get("app.trove.endpoint")
TROVE_TEST_URL = cfg.get("app.trove.test_endpoint")


def create_payload(obj, photometry):
    payload_photometry = []
    for p in photometry:
        p_dict = p.to_dict_public()
        phot_entry = {
            "jd": p.jd,
            "telescope": f"{p.instrument.telescope.nickname}-{p.instrument.name}",
            "filter": p_dict.get("filter"),
        }
        if p_dict.get("mag") is not None:
            phot_entry["magnitude"] = p_dict["mag"]
            if p_dict.get("magerr") is not None:
                phot_entry["error"] = p_dict["magerr"]
        elif p_dict.get("limiting_mag") is not None:
            phot_entry["limit"] = p_dict["limiting_mag"]
        else:
            continue
        payload_photometry.append(phot_entry)

    payload = {
        "name": obj.id,
        "ra": obj.ra,
        "dec": obj.dec,
        "permissions": "PUBLIC",
        "type": "SIDEREAL",
        "epoch": 2000,
    }
    if payload_photometry:
        payload["photometry"] = payload_photometry

    return payload


def submit_to_trove(submission_request, sharing_service, user, photometry, session):
    flow = Flow()
    sharing_service_id = sharing_service.id
    user_id = submission_request.user_id
    try:
        testing = sharing_service.testing
        trove_url = TROVE_TEST_URL if testing else TROVE_URL
        if not trove_url:
            setting = "test_endpoint" if testing else "endpoint"
            raise ValueError(
                f"TROVE url is not configured. Please set 'app.trove.{setting}' in the configuration. Skipping TROVE submission."
            )

        trove_altdata = sharing_service.trove_altdata
        if "username" not in trove_altdata or "password" not in trove_altdata:
            raise ValueError("Missing TROVE username or password.")

        obj_id = submission_request.obj_id
        obj = session.scalar(Obj.select(user).where(Obj.id == obj_id))

        payload = create_payload(obj, photometry)
        submission_request.trove_payload = payload

        session.commit()

        response = requests.post(
            f"{trove_url.rstrip('/')}/api/target/upload",
            json=[payload],
            auth=(trove_altdata["username"], trove_altdata["password"]),
            timeout=180,
        )
        if not response.ok:
            log(
                f"Failed to submit {obj_id} to TROVE with status code {response.status_code}: {response.text}"
            )
            status = f"Error: Failed to submit to TROVE with status code {response.status_code}"
            notif_text = f"TROVE error: Failed to submit to TROVE with status code {response.status_code}"
        elif testing:
            log(
                f"Successfully submitted {obj_id} to TROVE test server for sharing service {sharing_service_id}"
            )
            notif_text = f"Successfully submitted {obj_id} to TROVE test server"
            status = "Testing mode, submitted to TROVE test server."
        else:
            log(
                f"Successfully submitted {obj_id} to TROVE for sharing service {sharing_service_id}"
            )
            status = f"Successfully submitted {obj_id} to TROVE."
            notif_text = status

        submission_request.trove_response = serialize_requests_response(response)
    except Exception as e:
        log(str(e))
        status = f"Error: {e}"
        notif_text = f"TROVE error: {e}"

    try:
        flow.push(
            "*",
            "skyportal/REFRESH_SHARING_SERVICE_SUBMISSIONS",
            payload={"sharing_service_id": sharing_service_id},
        )
        flow.push(
            user_id=user_id,
            action_type="baselayer/SHOW_NOTIFICATION",
            payload={
                "note": notif_text,
                "type": "error" if "Error:" in status else "info",
                "duration": 8000,
            },
        )
    except Exception:
        pass

    submission_request.trove_status = status
    session.commit()
