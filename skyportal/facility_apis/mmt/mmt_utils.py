import datetime
import functools
import io
import json

import requests

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from skyportal.utils import http
from skyportal.utils.asynchronous import run_async
from skyportal.utils.calculations import deg2dms, deg2hms
from skyportal.utils.parse import bool_to_int

env, cfg = load_env()

image_source_dict = {
    "DESI DR8": "desi",
    "ZTF Ref Image": "ztfref",
    "DSS2": "dss",
    "PS1": "ps1",
}


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
        raise ValueError("A valid position angle must be provided")
    if payload.get("pm_ra") is None:
        raise ValueError("A valid proper motion RA must be provided")
    if payload.get("pm_dec") is None:
        raise ValueError("A valid proper motion DEC must be provided")
    if payload.get("exposure_time") is None:
        raise ValueError("A valid exposure time must be provided")
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
    if not isinstance(payload.get("include_finder_chart"), bool):
        raise ValueError("A valid include finder chart value must be provided")
    if payload.get("include_finder_chart"):
        if payload.get("primary_image_source") not in image_source_dict:
            raise ValueError(f"A valid primary image source must be provided")
        if payload.get("offset_position_origin") not in ["ZTF Ref", "Gaia DR3"]:
            raise ValueError("A valid offset position origin must be provided")
        if (
            not isinstance(payload["number_offset_Stars"], int)
            or payload["number_offset_Stars"] < 0
            or payload["number_offset_Stars"] > 4
        ):
            raise ValueError("A valid number of offset stars must be provided")


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
    observation_type_dict = {
        "Imaging": "imaging",
        "Spectroscopy": "longslit",
    }
    return {
        "observationtype": observation_type_dict.get(payload["observation_type"]),
        "token": altdata["token"],
        "objectid": sanitize_obj_id(obj.id),
        "ra": deg2hms(obj.ra),
        "dec": deg2dms(obj.dec),
        "magnitude": obj.photstats[0].last_detected_mag,
        "epoch": 2000.0,
        "pa": payload.get("pa"),
        "pm_ra": payload.get("pm_ra"),
        "pm_dec": payload.get("pm_dec"),
        "exposuretime": payload.get("exposure_time"),
        "numberexposures": payload.get("exposure_counts"),
        "visits": payload.get("visits"),
        "priority": payload.get("priority"),
        "photometric": bool_to_int(payload.get("photometric")),
        "targetofopportunity": bool_to_int(payload.get("target_of_opportunity")),
        "onevisitpernight": bool_to_int(payload.get("one_visit_per_night")),
        "filter": payload.get("filters"),
        "notes": payload.get("notes"),
    }


def send_finder_to_mmt(finder_callable, id_to_upload_chart_to, altdata, user_id):
    # Finder generation
    result = finder_callable()

    filename = result["name"]
    data = io.BytesIO(result["data"])
    data.name = filename

    files = {
        "finding_chart_file": (filename, data, "application/pdf"),
    }
    upload_data = {
        "type": "finding_chart",
        "token": altdata["token"],
        "target_id": id_to_upload_chart_to,
    }
    upload_response = requests.post(
        f"{cfg['app.mmt_endpoint']}/catalogTarget/{id_to_upload_chart_to}",
        data=upload_data,
        files=files,
    )

    is_success = upload_response.status_code == 200
    if is_success:
        note = "Successfully uploaded finder chart to MMT"
    else:
        note = (
            f"Failed to upload finder chart to MMT: error {upload_response.status_code}"
        )

    flow = Flow()
    flow.push(
        user_id,
        action_type="baselayer/SHOW_NOTIFICATION",
        payload={
            "note": note,
            "type": "info" if is_success else "error",
        },
    )
    if not is_success:
        raise ValueError(
            f"Failed to upload finder chart: {upload_response.status_code} - {upload_response.text}"
        )


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
        timeout=10.0,
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

    # If include_finder_chart is True, we try to upload the finder chart
    if request.status == "submitted" and request.payload.get(
        "include_finder_chart", False
    ):
        from skyportal.handlers.api.source import get_finding_chart_callable

        if response.content is None:
            raise ValueError("Impossible to upload finder chart: no response content")
        id_to_upload_chart_to = json.loads(response.content).get("id")
        if id_to_upload_chart_to is None:
            raise ValueError("No ID found in response to upload finder chart to")

        finder_callable = get_finding_chart_callable(
            obj_id=request.obj.id,
            session=session,
            imsize=4.0,
            facility="Keck",
            image_source=image_source_dict[request.payload["primary_image_source"]],
            use_ztfref=request.payload["offset_position_origin"] == "ZTF Ref",
            obstime=datetime.datetime.utcnow().isoformat(),
            output_type="pdf",
            num_offset_stars=request.payload.get("number_offset_Stars", 3),
        )
        run_async(
            send_finder_to_mmt,
            finder_callable,
            id_to_upload_chart_to,
            altdata,
            session.user_or_token.id,
        )

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
        "default": "Spectroscopy",
    },
    "pa": {
        "type": "number",
        "title": "Position Angle",
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
    "exposure_time": {
        "type": "number",
        "title": "Exposure Time (s)",
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
    "include_finder_chart": {
        "type": "boolean",
        "title": "Include Finder Chart",
        "default": False,
    },
}

mmt_dependencies = {
    "include_finder_chart": {
        "oneOf": [
            {
                "properties": {
                    "include_finder_chart": {"enum": [True]},
                    "primary_image_source": {
                        "type": "string",
                        "title": "Primary Image Source",
                        "enum": [
                            "DESI DR8",
                            "ZTF Ref Image",
                            "DSS2",
                            "PS1",
                        ],
                        "default": "DESI DR8",
                    },
                    "offset_position_origin": {
                        "type": "string",
                        "title": "Offset Position Origin",
                        "enum": ["ZTF Ref", "Gaia DR3"],
                        "default": "Gaia DR3",
                    },
                    "number_offset_Stars": {
                        "type": "integer",
                        "title": "Number of Offset Stars",
                        "default": 3,
                        "minimum": 0,
                        "maximum": 4,
                    },
                }
            },
            {
                "properties": {
                    "include_finder_chart": {"enum": [False]},
                }
            },
        ]
    },
}

mmt_required = [
    "observation_type",
    "pa",
    "pm_ra",
    "pm_dec",
    "exposure_counts",
    "exposure_time",
    "visits",
    "priority",
    "photometric",
    "target_of_opportunity",
    "one_visit_per_night",
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

mmt_ui_json_schema = {
    "ui:order": [
        "*",
        "include_finder_chart",
        "primary_image_source",
        "offset_position_origin",
        "number_offset_Stars",
    ]
}
