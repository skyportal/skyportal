import functools
import json

import requests

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from skyportal.utils import http
from skyportal.utils.calculations import deg2dms, deg2hms

env, cfg = load_env()


def catch_timeout_and_no_endpoint(func):
    """
    Catch timeout and missing endpoint errors from the MMT server
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.Timeout:
            raise ValueError("Unable to reach the MMT server")
        except KeyError as e:
            if "endpoint" in str(e):
                raise ValueError("MMT endpoint is missing from configuration")
            else:
                raise e

    return wrapper


def check_mmt_payload(payload):
    """
    Check the validity of the payload for fields common to all MMT instruments
    """
    if payload.get("observation_type") not in [
        "Imaging",
        "Spectroscopy",
    ]:
        raise ValueError("A valid observation type must be provided")
    if payload.get("pa") is None or payload["pa"] < -360.0 or payload["pa"] > 360.0:
        raise ValueError("A valid parallactic angle must be provided")
    if payload.get("pm_ra") is None:
        raise ValueError("A valid Proper Motion RA must be provided")
    if payload.get("pm_dec") is None:
        raise ValueError("A valid Proper Motion DEC must be provided")
    if payload.get("exposure_counts") is None or payload["exposure_counts"] < 1:
        raise ValueError("A valid number of exposures must be provided")
    if payload.get("visits") is None:
        raise ValueError("A valid number of visits must be provided")
    if payload.get("priority") not in [1, 2, 3]:
        raise ValueError("A valid priority must be provided")
    if not isinstance(payload.get("photometric"), bool):
        raise ValueError("A valid photometric value must be provided")
    if not isinstance(payload.get("target_of_opportunity"), bool):
        raise ValueError("A valid target of opportunity value must be provided")
    if not isinstance(payload.get("one_visit_per_night"), bool):
        raise ValueError("A valid one visit per night value must be provided")

    if payload.get("observation_type") == "Imaging":
        if payload.get("exposure_time") is None:
            raise ValueError("A valid exposure time must be provided")


def sanitize_obj_id(obj_id):
    """
    Sanitize the object ID to avoid using special characters in the MMT request
    """
    if len(obj_id) > 50:
        obj_id = obj_id[:50]
    return "".join(c if c.isalnum() else "X" for c in obj_id)


def check_obj_for_mmt(obj):
    """
    Check the validity of the required object fields for an MMT request
    """
    if not obj.id or len(obj.id) < 2:
        raise ValueError("Object ID must be more than 2 characters")
    if not obj.ra:
        raise ValueError("Missing the 'ra' value on the object")
    if not obj.dec:
        raise ValueError("Missing the 'dec' value on the object")
    if not obj.photstats or not obj.photstats[0].last_detected_mag:
        raise ValueError("Missing the 'magnitude' value on the object")


def get_mmt_json_payload(obj, altdata, payload):
    """
    Get the JSON payload common to all MMT instruments
    """
    json_payload = {
        "token": altdata["token"],
        "objectid": sanitize_obj_id(obj.id),
        "ra": deg2hms(obj.ra),
        "dec": deg2dms(obj.dec),
        "magnitude": obj.photstats[0].last_detected_mag,
        "epoch": 2000.0,
        "pa": payload.get("pa"),
        "pm_ra": payload.get("pm_ra"),
        "pm_dec": payload.get("pm_dec"),
        "numberexposures": payload.get("exposure_counts"),
        "visits": payload.get("visits"),
        "priority": payload.get("priority"),
        "photometric": payload.get("photometric"),
        "targetofopportunity": payload.get("target_of_opportunity"),
        "filter": payload.get("filters"),
        "onevisitpernight": 1 if payload.get("one_visit_per_night") else 0,
        "notes": payload.get("notes"),
    }
    if payload.get("observation_type") == "Imaging":
        return {
            **json_payload,
            "observationtype": "imaging",
            "maskid": payload.get("mask_id"),
            "exposuretime": payload.get("exposure_time"),
        }
    else:
        return {
            **json_payload,
            "observationtype": "longslit",
        }

def submit_mmt_request(
    session, request, specific_payload, instrument_id, log, **kwargs
):
    """
    Submit a request to MMT

    Parameters
    ----------
    session : SQLAlchemy session
        The current session
    request : FollowupRequest
        The request to submit
    specific_payload : dict
        The payload specific to an instrument
    instrument_id : int
        The instrument ID to submit the request to
    log : callable
        The logging function associated with the instrument
    kwargs : dict
        Additional keyword arguments
    """
    from ...models import FacilityTransaction

    if cfg["app.mmt_endpoint"] is None:
        raise ValueError("MMT endpoint not configured")

    altdata = request.allocation.altdata
    if not altdata or "token" not in altdata:
        raise ValueError("Missing allocation information.")

    json_payload = {
        **get_mmt_json_payload(request.obj, altdata, request.payload),
        **specific_payload,
        "instrumentid": instrument_id,
    }

    response = requests.post(
        f"{cfg['app.mmt_endpoint']}/catalogTarget",
        json=json_payload,
        data=None,
        files=None,
        timeout=5.0,
    )

    if response.status_code != 200:
        if response.status_code == 500 and "Invalid token" in response.text:
            request.status = f"rejected: invalid token"
        else:
            request.status = f"rejected: status code {response.status_code}"
    else:
        request.status = "submitted"

    transaction = FacilityTransaction(
        request=http.serialize_requests_request(response.request),
        response=http.serialize_requests_response(response),
        followup_request=request,
        initiator_id=request.last_modified_by_id,
    )

    session.add(transaction)
    session.commit()

    try:
        flow = Flow()
        if kwargs.get("refresh_source", False):
            flow.push(
                "*",
                "skyportal/REFRESH_SOURCE",
                payload={"obj_key": request.obj.internal_key},
            )
        if kwargs.get("refresh_requests", False):
            flow.push(
                request.last_modified_by_id, "skyportal/REFRESH_FOLLOWUP_REQUESTS"
            )
    except Exception as e:
        log(f"Failed to send notification: {str(e)}")


def delete_mmt_request(session, request, log, **kwargs):
    """
    Delete a request from the MMT queue

    Parameters
    ----------
    session : SQLAlchemy session
        The current session
    request : FollowupRequest
        The request to delete
    log : callable
        The logging function associated with the instrument
    kwargs : dict
        Additional keyword arguments
    """
    from ...models import FacilityTransaction, FollowupRequest

    last_modified_by_id = request.last_modified_by_id
    obj_internal_key = request.obj.internal_key

    # this happens for failed submissions, just go ahead and delete
    if len(request.transactions) == 0 or str(request.status).startswith("rejected"):
        session.query(FollowupRequest).filter(FollowupRequest.id == request.id).delete()
        session.commit()
    else:
        request_response = request.transactions[-1].response
        if request_response is None or request_response.get("content") is None:
            raise ValueError("No request information found")

        id_to_delete = json.loads(request_response["content"]).get("id")

        if id_to_delete is None:
            raise ValueError("No request ID found to delete")

        if cfg["app.mmt_endpoint"] is None:
            raise ValueError("MMT endpoint not configured")

        altdata = request.allocation.altdata
        if not altdata or "token" not in altdata:
            raise ValueError("Missing allocation information.")

        response = requests.delete(
            f"{cfg['app.mmt_endpoint']}/catalogTarget/{id_to_delete}",
            timeout=5.0,
        )

        if response.status_code != 200 or not response.json().get("success"):
            raise ValueError(
                f"Failed to delete request: status code {response.status_code}"
            )
        else:
            request.status = "deleted"

        transaction = FacilityTransaction(
            request=http.serialize_requests_request(response.request),
            response=http.serialize_requests_response(response),
            followup_request=request,
            initiator_id=request.last_modified_by_id,
        )

        session.add(transaction)
        session.commit()

    try:
        flow = Flow()
        if kwargs.get("refresh_source", False):
            flow.push(
                "*",
                "skyportal/REFRESH_SOURCE",
                payload={"obj_key": obj_internal_key},
            )
        if kwargs.get("refresh_requests", False):
            flow.push(
                last_modified_by_id,
                "skyportal/REFRESH_FOLLOWUP_REQUESTS",
            )
    except Exception as e:
        log(f"Failed to send notification: {str(e)}")


mmt_properties = {
    "observation_type": {
        "type": "string",
        "title": "Observation Type",
        "enum": [
            "Imaging",
            "Spectroscopy",
        ],
        "default": "Imaging",
    },
    "pa": {
        "type": "number",
        "title": "Parallactic Angle",
        "default": 0.0,
        "minimum": -360.0,
        "maximum": 360.0,
    },
    "pm_ra": {
        "type": "number",
        "title": "Proper Motion RA",
        "default": 0.0,
    },
    "pm_dec": {
        "type": "number",
        "title": "Proper Motion DEC",
        "default": 0.0,
    },
    "exposure_counts": {
        "type": "integer",
        "title": "Number of Exposures",
        "default": 1,
    },
    "visits": {
        "type": "integer",
        "title": "Number of Visits",
        "default": 1,
    },
    "priority": {
        "type": "integer",
        "title": "Priority",
        "enum": [1, 2, 3],
        "default": 3,
    },
    "notes": {
        "type": "string",
        "title": "Notes",
        "default": "This request comes from SkyPortal",
    },
    "photometric": {
        "type": "boolean",
        "title": "Require photometric conditions",
        "default": False,
    },
    "target_of_opportunity": {
        "type": "boolean",
        "title": "Target of Opportunity",
        "default": False,
    },
    "one_visit_per_night": {
        "type": "boolean",
        "title": "One Visit Per Night",
        "default": True,
    },
}

mmt_imager_schema = {
    "properties": {
        "exposure_time": {
            "type": "number",
            "title": "Exposure Time (s)",
        },
    },
    "required": [
        "exposure_time",
    ],
}

mmt_required = [
    "observation_type",
    "pa",
    "pm_ra",
    "pm_dec",
    "exposure_counts",
    "visits",
    "priority",
    "photometric",
    "target_of_opportunity",
]

mmt_aldata = {
    "type": "object",
    "properties": {
        "token": {
            "type": "string",
            "title": "Token",
        },
    },
    "required": ["token"],
}
