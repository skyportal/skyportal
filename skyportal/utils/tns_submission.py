import json
import re
import time

import requests
import sqlalchemy as sa
from astropy.time import Time

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log
from skyportal.handlers.api.photometry import serialize
from skyportal.models import Stream
from skyportal.utils.http import serialize_requests_response
from skyportal.utils.parse import is_null
from skyportal.utils.tns import (
    SNCOSMO_TO_TNSFILTER,
    TNS_INSTRUMENT_IDS,
    TNS_SOURCE_GROUP_NAMING_CONVENTIONS,
    TNS_URL,
    get_IAUname,
    get_internal_names,
    get_tns_headers,
    get_tns_url,
)

env, cfg = load_env()

log = make_log("tns_submission_utils")


# Custom exception to catch sharing issues we want to notify as warnings
class TNSWarning(Exception):
    pass


def apply_existing_tns_report_rules(sharing_service, submission_request):
    """Apply the rules for existing TNS reports to the submission request.

    Parameters
    ----------
    sharing_service : `~skyportal.models.SharingService`
        The sharing service to use for the submission.
    submission_request : `~skyportal.models.SharingServiceSubmission`
        The submission request.
    """
    # if the sharing service is set up to only report objects to TNS if they are not already there,
    # we check if an object is already on TNS (within 2 arcsec of the object's position)
    # and if it is, we skip the submission
    # otherwise, we submit as long as there are no reports with the same internal source name
    # (i.e. the same obj_id from the same survey)
    altdata = sharing_service.tns_altdata
    obj_id = submission_request.obj_id
    tns_headers = get_tns_headers(
        sharing_service.tns_bot_id, sharing_service.tns_bot_name
    )

    # if the sharing service is in test mode, we skip the existing TNS report check
    if sharing_service.testing:
        log(f"Skipping existing TNS report check for {obj_id} in test mode.")
        return

    _, existing_tns_name = get_IAUname(
        altdata["api_key"], tns_headers, obj_id=obj_id, closest=True
    )
    if existing_tns_name is not None:
        if not sharing_service.publish_existing_tns_objects:
            raise TNSWarning(f"{obj_id} already posted to TNS as {existing_tns_name}.")
        else:
            # look if the object on TNS has already been reported by the same survey (same internal name, here being the obj_id)
            internal_names = get_internal_names(
                altdata["api_key"], tns_headers, tns_name=existing_tns_name
            )
            if len(internal_names) > 0 and obj_id in internal_names:
                raise TNSWarning(
                    f"{obj_id} already posted to TNS with the same internal source name."
                )


def build_tns_report(
    submission_request,
    sharing_service,
    reporters,
    remarks,
    photometry,
    photometry_options,
    stream_ids,
    session,
):
    """Build the AT report for a TNS submission.

    Parameters
    ----------
    submission_request : `~skyportal.models.SharingServiceSubmission`
        The submission request.
    sharing_service : `~skyportal.models.SharingService`
        The sharing service to use for the submission.
    reporters : str
        The reporters to use for the submission.
    remarks : str
        The remarks to use for the submission (optional)
    photometry : list of `~skyportal.models.Photometry`
        The photometry to submit.
    photometry_options : dict
        The photometry options to use.
    stream_ids : list of int
        The stream IDs that were used to query for the photometry.
    session : `~sqlalchemy.orm.Session`
        The database session to use.

    Returns
    -------
    at_report : dict
        The AT report to submit.
    """
    from skyportal.models import Obj

    obj_id = submission_request.obj_id
    archival = submission_request.archival
    archival_comment = submission_request.archival_comment

    # non detections are those with mag=None
    detections, non_detections = [], []

    for phot in photometry:
        if is_null(phot["mag"]):
            non_detections.append(phot)
        else:
            detections.append(phot)

    # sort each by mjd ascending and filter out non-detections that are after the first detection
    detections.sort(key=lambda k: k["mjd"])
    non_detections = sorted(
        (p for p in non_detections if p["mjd"] < detections[0]["mjd"]),
        key=lambda p: p["mjd"],
    )

    first = detections[0]
    time_first = first["mjd"]
    phot_first = {
        "obsdate": Time(time_first, format="mjd").jd,
        "flux": first["mag"],
        "flux_error": first["magerr"],
        "flux_units": "1",
        "filter_value": SNCOSMO_TO_TNSFILTER[first["filter"]],
        "instrument_value": TNS_INSTRUMENT_IDS[first["instrument_name"].lower()],
    }
    phot_last = None
    if len(detections) > 1:
        last = detections[-1]
        phot_last = {
            "obsdate": Time(last["mjd"], format="mjd").jd,
            "flux": last["mag"],
            "flux_error": last["magerr"],
            "flux_units": "1",
            "filter_value": SNCOSMO_TO_TNSFILTER[last["filter"]],
            "instrument_value": TNS_INSTRUMENT_IDS[last["instrument_name"].lower()],
        }

    # Manage archival mode if there are no non-detections
    if (
        not non_detections
        and submission_request.auto_submission
        and photometry_options.get("auto_sharing_allow_archival")
    ):
        archival = True
        if stream_ids:
            stream_names = session.scalars(
                sa.select(Stream.name).where(Stream.id.in_(stream_ids))
            ).all()
            stream_names = list(set(stream_names))
            plural = "s" if len(stream_names) > 1 else ""
            archival_comment = f"No non-detections prior to first detection in {', '.join(stream_names)} alert stream{plural}"
        else:
            archival_comment = "No non-detections prior to first detection"

    if not non_detections and not archival:
        raise TNSWarning(
            f"for sharing service {sharing_service.id} publishing to TNS requires at least one non-detection prior to the first detection, but none were found. Select Archival mode to submit without non-detections."
        )

    if archival:
        non_detection = {
            "archiveid": "0",
            "archival_remarks": archival_comment,
        }
    else:
        last_nd = non_detections[-1]
        non_detection = {
            "obsdate": Time(last_nd["mjd"], format="mjd").jd,
            "limiting_flux": last_nd["limiting_mag"],
            "flux_units": "1",
            "filter_value": SNCOSMO_TO_TNSFILTER[last_nd["filter"]],
            "instrument_value": TNS_INSTRUMENT_IDS[last_nd["instrument_name"].lower()],
        }

    proprietary_period = {
        "proprietary_period_value": 0,
        "proprietary_period_units": "years",
    }

    obj = session.scalar(sa.select(Obj).where(Obj.id == obj_id))

    at_report = {
        "ra": {"value": obj.ra},
        "dec": {"value": obj.dec},
        "reporting_group_id": sharing_service.tns_source_group_id,
        "discovery_data_source_id": sharing_service.tns_source_group_id,
        "internal_name_format": {
            "prefix": phot_first["instrument_value"],
            "year_format": "YY",
            "postfix": "",
        },
        "internal_name": obj_id,
        "reporter": reporters,
        "discovery_datetime": Time(time_first, format="mjd").datetime.strftime(
            "%Y-%m-%d %H:%M:%S.%f"
        ),
        "at_type": 1,  # allow other options?
        "proprietary_period_groups": [sharing_service.tns_source_group_id],
        "proprietary_period": proprietary_period,
        "non_detection": non_detection,
        "photometry": {"photometry_group": {"0": phot_first}},
    }

    if phot_last:
        at_report["photometry"]["photometry_group"]["1"] = phot_last

    if remarks and str(remarks).strip():
        at_report["remarks"] = remarks

    return {"at_report": {"0": at_report}}


def send_tns_report(submission_request, sharing_service, report):
    """Build and send an AT report to TNS.

    Parameters
    ----------
    submission_request : `~skyportal.models.SubmissionRequest`
        The submission request to send to TNS.
    sharing_service : `~skyportal.models.SharingService`
        The sharing service to use for the submission.
    report : dict
        The AT report to send to TNS.

    Returns
    -------
    status : str
        The status of the submission.
    submission_id : str or None
        The submission ID if the submission was successful, otherwise None.
    serialized_response : str or None
        The serialized response from the TNS API if the submission was successful, otherwise None.
    """
    tns_headers = get_tns_headers(
        sharing_service.tns_bot_id, sharing_service.tns_bot_name
    )
    obj_id = submission_request.obj_id
    data = {
        "api_key": sharing_service.tns_altdata["api_key"],
        "data": json.dumps(report),
    }

    submission_id = None
    serialized_response = None

    if sharing_service.testing:
        log(
            f"Sharing service {sharing_service.id} is in testing mode, skipping TNS submission for {obj_id}."
        )
        return "Testing mode, not submitted", None, None

    # 24 * 10 seconds = 4 minutes of retries
    max_retries = 24
    retry_delay = 10
    r = None
    exceeded_rate_message = f"Exceeded TNS API rate limit when submitting {obj_id} with sharing service {sharing_service.id}"
    for attempt in range(max_retries):
        r = requests.post(get_tns_url("report"), headers=tns_headers, data=data)
        if r.status_code != 429:
            break  # If not rate-limited, exit the retry loop

        log(
            f"{exceeded_rate_message}, waiting {retry_delay} seconds before retrying..."
        )
        time.sleep(retry_delay)

    if r.status_code == 200:
        submission_id = r.json()["data"]["report_id"]
        log(
            f"Successfully submitted {obj_id} to TNS with request ID {submission_id} for sharing service {sharing_service.id}"
        )
        status = "submitted"
    elif r.status_code == 401:
        status = f"Error: Unauthorized to submit {obj_id} to TNS with sharing service {sharing_service.id}, credentials may be invalid"
    elif r.status_code == 429:
        status = f"Error: {exceeded_rate_message}, and exceeded number of retries ({max_retries})"
    else:
        status = f"Error: Failed to submit {obj_id} to TNS with sharing service {sharing_service.id}: {r.content}"

    if isinstance(r, requests.models.Response):
        # we store the request's TNS response in the database for bookkeeping and debugging
        serialized_response = serialize_requests_response(r)

    return status, submission_id, serialized_response


def submit_to_tns(
    submission_request,
    sharing_service,
    photometry,
    photometry_options,
    stream_ids,
    reporters,
    remarks,
    warning,
    session,
):
    notif_type = "info"
    try:
        if not TNS_URL:
            raise ValueError(
                "TNS URL is not configured. Please set 'app.tns.endpoint' in the configuration to use TNS submission."
            )

        obj_id = submission_request.obj_id
        tns_altdata = sharing_service.tns_altdata

        if not tns_altdata or "api_key" not in tns_altdata:
            raise ValueError(
                f"No TNS API key found for sharing service {sharing_service.id}."
            )

        # Validate that the object ID is valid for submission to TNS with the given TNS source group ID.
        if (
            sharing_service.tns_source_group_id
            not in TNS_SOURCE_GROUP_NAMING_CONVENTIONS
        ):
            raise ValueError(
                f"Unknown naming convention for TNS source group ID {sharing_service.tns_source_group_id}, cannot validate object ID."
            )
        regex_pattern = TNS_SOURCE_GROUP_NAMING_CONVENTIONS[
            sharing_service.tns_source_group_id
        ]
        if not re.match(regex_pattern, obj_id):
            raise ValueError(
                f"Object ID {obj_id} does not match the expected naming convention for TNS source group ID {sharing_service.tns_source_group_id}."
            )

        apply_existing_tns_report_rules(sharing_service, submission_request)

        archival = submission_request.archival
        archival_comment = submission_request.archival_comment
        if archival and not archival_comment:
            raise ValueError(
                f"Archival submission requested for {obj_id} but no archival_comment provided."
            )

        photometry = [serialize(phot, "ab", "mag") for phot in photometry]
        tns_report = build_tns_report(
            submission_request,
            sharing_service,
            reporters,
            remarks,
            photometry,
            photometry_options,
            stream_ids,
            session,
        )
        submission_request.tns_payload = json.dumps(tns_report)

        # submit the report to TNS
        status, submission_id, serialized_response = send_tns_report(
            submission_request, sharing_service, tns_report
        )
        submission_request.tns_submission_id = submission_id
        submission_request.tns_response = serialized_response

        notif_text = status
        if status in ["submitted", "Testing mode, not submitted"]:
            if status == "Testing mode, not submitted":
                notif_text = f"Successfully created TNS report for {submission_request.obj_id} (testing mode, not submitted)."
            else:
                notif_text = (
                    f"Successfully submitted {submission_request.obj_id} to TNS."
                )
            if warning:
                status += f"(warning: {warning})"
                notif_text += f"(warning: {warning})"
    except TNSWarning as e:
        notif_type = "warning"
        notif_text = f"TNS warning: {e}"
        status = f"Error: {e}"
        log(str(e))

    except Exception as e:
        notif_type = "error"
        notif_text = f"TNS error: {e}"
        status = f"Error: {e}"
        log(str(e))

    try:
        flow = Flow()
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
                "type": notif_type,
                "duration": 8000,
            },
        )
    except Exception:
        pass

    submission_request.tns_status = status
    session.commit()


def check_at_report(submission_id, sharing_service):
    """Check the status of a report submission to TNS, verifying that the submission was successful (or not).

    Parameters
    ----------
    submission_id : int
        The ID of the submission request to check on TNS.
    sharing_service : `~skyportal.models.SharingService`
        The sharing service to use for the check.

    Returns
    -------
    obj_name : str
        The TNS name of the object for which the report was submitted.
    response : dict
        The response from TNS, serialized as a dictionary.
    """

    obj_name, response = None, None

    data = {
        "api_key": sharing_service.tns_altdata["api_key"],
        "report_id": submission_id,
    }

    # 24 * 10 seconds = 4 minutes of retries
    max_retries = 24
    retry_delay = 10
    r = None
    for _ in range(max_retries):
        r = requests.post(
            get_tns_url("report_reply"),
            headers=get_tns_headers(
                sharing_service.tns_bot_id, sharing_service.tns_bot_name
            ),
            data=data,
        )
        if r.status_code != 429:
            break
        time.sleep(retry_delay)

    if r.status_code not in [200, 400, 404]:
        raise ValueError(f"Error checking report: {r.text}")

    try:
        response = serialize_requests_response(r)
    except Exception as e:
        raise ValueError(f"Error serializing response: {e}")

    if r.status_code == 404:
        return None, response, "report not found"

    try:
        at_report = r.json().get("data", {}).get("feedback", {}).get("at_report", [])
    except Exception:
        raise ValueError("Could not find AT report in response.")

    if not at_report or not isinstance(at_report, list):
        raise ValueError("No AT report data found in response.")

    # An identical AT report (sender, RA\/DEC, discovery date) already exists.
    if "An identical AT report" in str(at_report):
        return None, response, None
    at_report = at_report[0]

    if r.status_code == 400:
        if at_report.get("reporting_groupid") and isinstance(
            at_report.get("reporting_groupid"), list
        ):
            return (
                None,
                response,
                f"Report could not be processed invalid reporting group ID ({at_report['reporting_groupid'][0].get('message')})",
            )
        else:
            return (
                None,
                response,
                f"Report could not be processed ({at_report.get('status_code')})",
            )

    try:
        # the at_report is a dict with keys 'status code' and 'at_rep'
        status_keys = set(at_report) - {"at_rep"}

        if not status_keys:
            raise ValueError("Report received but not yet processed.")

        if "100" in status_keys:
            # an object has been created along with the report
            obj_name = at_report["100"]["objname"]
            if obj_name is None:
                raise ValueError("Object created and report posted but no name found.")
        elif "101" in status_keys:
            # object already exists, no new object created but report processed
            obj_name = at_report["101"]["objname"]
            if obj_name is None:
                raise ValueError("Object found and report posted but no name found.")
    except Exception as e:
        log(f"Error checking report: {e}")
        raise ValueError(f"Error checking report: {e}")

    # for now catching errors from TNS is not implemented, so we just return None for the error
    return obj_name, response, None
