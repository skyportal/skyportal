import json
import re
import time
import urllib

import requests
import sqlalchemy as sa
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log
from skyportal.handlers.api.photometry import serialize
from skyportal.models import Stream
from skyportal.utils.http import serialize_requests_response
from skyportal.utils.parse import is_null

log = make_log("tns_submission_utils")

env, cfg = load_env()

TNS_URL = cfg.get("app.tns.endpoint")

tns_url_dict = {
    "search": "api/get/search",
    "search_frontend": "search",
    "object": "api/get/object",
    "report": "api/set/bulk-report",
    "report_reply": "api/get/bulk-report-reply",
}

TNS_INSTRUMENT_IDS = {
    "alfosc": 41,
    "asas-sn": 195,
    "atlas": [153, 159, 160, 255, 256, 167],
    "decam": 172,
    "efosc2": 30,
    "gaia": 163,
    "goodman": 136,
    "goto": [218, 264, 265, 266],
    "ps1": [98, 154, 155, 257],
    "sedm": [149, 225],
    "sprat": 156,
    "ztf": 196,
}

SNCOSMO_TO_TNSFILTER = {
    "atlasc": 71,
    "atlaso": 72,
    "sdssu": 20,
    "sdssg": 21,
    "sdssr": 22,
    "sdssi": 23,
    "sdssz": 24,
    "desu": 20,
    "desg": 21,
    "desr": 22,
    "desi": 23,
    "desz": 24,
    "desy": 81,
    "gaia::g": 75,
    "gotol": 121,
    "gotor": 122,
    "gotog": 123,
    "gotob": 124,
    "ps1::g": 56,
    "ps1::r": 57,
    "ps1::i": 58,
    "ps1::z": 59,
    "ps1::w": 26,
    "ztfg": 110,
    "ztfr": 111,
    "ztfi": 112,
}

TNSFILTER_TO_SNCOSMO = {v: k for k, v in SNCOSMO_TO_TNSFILTER.items()}

# here we store regex patterns, to validate that a source name is in the correct format
# for a given TNS source group. Used to not submit incorrect sources to TNS.
TNS_SOURCE_GROUP_NAMING_CONVENTIONS = {
    48: r"ZTF\d{2}[a-z]{7}",  # ZTF: ZTF + 2 digits + 7 lowercase characters
    135: r"[ACT]20\d{6}\d{7}[pm]\d{6}",  # DECAM: A or C or T + 20 + 6 digits + 7 digits + p or m + 6 digits
}


def get_tns_headers(publishing_bot):
    """Get the headers to use for TNS requests.
    Parameters
    ----------
    publishing_bot : `~skyportal.models.ExternalPublishingBot`
        The bot to use for the submission.
    Returns
    -------
    dict
        The headers to use for TNS requests.
    """
    return {
        "User-Agent": f'tns_marker{{"tns_id":{publishing_bot.bot_id},"type":"bot", "name":"{publishing_bot.bot_name}"}}'
    }


def get_tns_url(url_type):
    """Get the TNS URL for the specified type.
    Parameters
    ----------
    url_type : str
        Type of TNS URL to retrieve.
    Returns
    -------
    str
        The TNS URL for the specified type.
    """
    if TNS_URL is None:
        raise ValueError(
            "TNS URL is not configured. Please set 'app.tns.endpoint' in the configuration."
        )
    if url_type not in tns_url_dict:
        raise ValueError(
            "Invalid TNS URL type specified. Valid types are: "
            + ", ".join(tns_url_dict.keys())
        )
    return urllib.parse.urljoin(TNS_URL, tns_url_dict[url_type])


def get_IAUname(
    api_key, headers, obj_id=None, ra=None, dec=None, radius=2.0, closest=False
):
    """Query TNS to get IAU name (if exists)
    Parameters
    ----------
    api_key : str
        TNS api key
    objname : str
        Name of the object to query TNS for
    headers : str
        TNS query headers
    obj_id : str
        Object name to search for
    ra : float
        Right ascension of object to search for
    dec : float
        Declination of object to search for
    radius : float
        Radius of object to search for
    Returns
    -------
    list
        IAU prefix, IAU name
    """

    if obj_id is not None:
        req_data = {
            "ra": "",
            "dec": "",
            "radius": "",
            "units": "",
            "objname": "",
            "objname_exact_match": 0,
            "internal_name": obj_id.replace("_", " "),
            "internal_name_exact_match": 0,
            "objid": "",
        }
    elif ra is not None and dec is not None:
        c = SkyCoord(ra=ra * u.degree, dec=dec * u.degree, frame="icrs")
        req_data = {
            "ra": c.ra.to_string(unit=u.hour, sep=":", pad=True),
            "dec": c.dec.to_string(unit=u.degree, sep=":", alwayssign=True, pad=True),
            "radius": f"{radius}",
            "units": "arcsec",
            "objname": "",
            "objname_exact_match": 0,
            "internal_name": "",
            "internal_name_exact_match": 0,
            "objid": "",
        }
    else:
        raise ValueError("Must define obj_id or ra/dec.")

    data = {"api_key": api_key, "data": json.dumps(req_data)}
    r = requests.post(get_tns_url("search"), headers=headers, data=data)

    count = 0
    count_limit = 24  # 6 * 4 * 10 = 4 minutes of retries
    while r.status_code == 429 and count < count_limit:
        try:
            content = r.json()
        except Exception:
            content = r.text
        log(
            f"TNS request rate limited: {str(content)}.  Waiting 10 seconds to try again."
        )
        time.sleep(10)
        r = requests.post(get_tns_url("search"), headers=headers, data=data)
        count += 1

    if r.status_code not in [200, 429, 401]:
        try:
            content = r.json()
        except Exception:
            content = r.text
        raise ValueError(f"Request failed, {str(content)}.")

    if r.status_code == 401:
        raise ValueError("Request failed, invalid TNS API key.")

    if count == count_limit:
        raise ValueError("Request failed, request rate exceeded.")

    try:
        reply = r.json().get("data", {})
    except Exception as e:
        log(f"Failed to parse TNS response: {str(e)} ({str(r.json())})")
        reply = []

    if len(reply) > 0:
        prefix, objname = reply[-1]["prefix"], reply[-1]["objname"]
        if closest and len(reply) > 1:
            closest_separation = float(radius)
            for obj in reply:
                data = {
                    "api_key": api_key,
                    "data": json.dumps(
                        {
                            "objname": obj["objname"],
                        }
                    ),
                }
                status_code = 429
                n_retries = 0
                r = None
                while (
                    status_code == 429 and n_retries < 24
                ):  # 6 * 4 * 10 seconds = 4 minutes of retries
                    r = requests.post(
                        get_tns_url("object"),
                        headers=headers,
                        data=data,
                        allow_redirects=True,
                        stream=True,
                        timeout=10,
                    )
                    status_code = r.status_code
                    if status_code == 429:
                        n_retries += 1
                        time.sleep(10)
                    else:
                        break

                if status_code != 200 or r is None:
                    # ignore this object
                    continue

                try:
                    source_data = r.json().get("data", {})
                except Exception:
                    source_data = None
                if source_data:
                    tns_ra, tns_dec = source_data["radeg"], source_data["decdeg"]
                    from skyportal.utils.calculations import great_circle_distance

                    separation = (
                        great_circle_distance(ra, dec, tns_ra, tns_dec) * 3600
                    )  # arcsec
                    if separation < closest_separation:
                        closest_separation = separation
                        prefix, objname = obj["prefix"], obj["objname"]

        return prefix, objname

    else:
        return None, None


def get_internal_names(api_key, headers, tns_name=None):
    """Query TNS to get internal names of an object

    Parameters
    ----------
    api_key : str
        TNS api key
    headers : str
        TNS query headers
    tns_name : str
        Name of the object to query TNS for

    Returns
    -------
    list
        Internal names of the object
    """
    data = {
        "api_key": api_key,
        "data": json.dumps(
            {
                "objname": tns_name,
            }
        ),
    }

    status_code = 429
    n_retries = 0
    r = None
    while n_retries < 24:  # 6 * 4 * 10 = 4 minutes of retries
        r = requests.post(
            get_tns_url("object"),
            headers=headers,
            data=data,
            allow_redirects=True,
            stream=True,
            timeout=10,
        )
        status_code = r.status_code
        if status_code == 429:
            n_retries += 1
            try:
                content = r.json()
            except Exception:
                content = r.text
            log(
                f"TNS request rate limited: {str(content)}.  Waiting 10 seconds to try again."
            )
            time.sleep(10)
        else:
            break

    if not isinstance(r, requests.Response):
        raise ValueError("Request failed, no response received.")

    if r.status_code not in [200, 429, 401]:
        try:
            content = r.json()
        except Exception:
            content = r.text
        raise ValueError(f"Request failed, {str(content)}.")

    if status_code == 401:
        raise ValueError("Request failed, invalid TNSRobot API key.")

    if n_retries == 24:
        raise ValueError("TNS request failed: request rate exceeded.")

    try:
        reply = json.loads(r.text)
        internal_names = reply["data"]["internal_names"]
        # comma separated list of internal names, starting with a comma (so we fiter out the first empty string after splitting)
        internal_names = list(filter(None, map(str.strip, internal_names.split(","))))
    except Exception as e:
        raise ValueError(
            f"Failed to parse TNS response to retrieve internal names, {str(e)}"
        )

    return internal_names


def apply_existing_tnsreport_rules(publishing_bot, submission_request):
    """Apply the rules for existing TNS reports to the submission request.

    Parameters
    ----------
    publishing_bot : `~skyportal.models.ExternalPublishingBot`
        The bot to use for the submission.
    submission_request : `~skyportal.models.ExternalPublishingSubmission`
        The submission request.
    """
    # if the bot is set up to only report objects to TNS if they are not already there,
    # we check if an object is already on TNS (within 2 arcsec of the object's position)
    # and if it is, we skip the submission
    # otherwise, we submit as long as there are no reports with the same internal source name
    # (i.e. the same obj_id from the same survey)
    altdata = publishing_bot.tns_altdata
    obj_id = submission_request.obj_id
    tns_headers = get_tns_headers(publishing_bot)

    _, existing_tns_name = get_IAUname(
        altdata["api_key"], tns_headers, obj_id=obj_id, closest=True
    )
    if existing_tns_name is not None:
        if not publishing_bot.publish_existing_tns_objects:
            raise ValueError(
                f"ExternalPublishingWarning: {obj_id} already posted to TNS as {existing_tns_name}."
            )
        else:
            # look if the object on TNS has already been reported by the same survey (same internal name, here being the obj_id)
            internal_names = get_internal_names(
                altdata["api_key"], tns_headers, tns_name=existing_tns_name
            )
            if len(internal_names) > 0 and obj_id in internal_names:
                raise ValueError(
                    f"ExternalPublishingWarning: {obj_id} already posted to TNS with the same internal source name."
                )


def build_tns_report(
    submission_request,
    publishing_bot,
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
    submission_request : `~skyportal.models.TNSRobotSubmission`
        The submission request.
    publishing_bot : `~skyportal.models.ExternalPublishingBot`
        The bot to use for the submission.
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

    if not detections:
        raise ValueError(
            f"ExternalPublishingWarning: Need at least one detection to report with publishing bot {publishing_bot.id}."
        )

    if photometry_options["first_and_last_detections"] is True and len(detections) < 2:
        raise ValueError(
            f"ExternalPublishingWarning: Publishing bot {publishing_bot.id} requires both first and last detections, but only one detection is available."
        )

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
        and photometry_options.get("auto_publish_allow_archival")
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
        raise ValueError(
            f"ExternalPublishingWarning: Publishing bot {publishing_bot.id} requires at least one non-detection before the first detection, but none are available."
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
        "reporting_group_id": publishing_bot.source_group_id,
        "discovery_data_source_id": publishing_bot.source_group_id,
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
        "proprietary_period_groups": [publishing_bot.source_group_id],
        "proprietary_period": proprietary_period,
        "non_detection": non_detection,
        "photometry": {"photometry_group": {"0": phot_first}},
    }

    if phot_last:
        at_report["photometry"]["photometry_group"]["1"] = phot_last

    if remarks and str(remarks).strip():
        at_report["remarks"] = remarks

    return {"at_report": {"0": at_report}}


def send_tns_report(submission_request, publishing_bot, report):
    """Build and send an AT report to TNS.

    Parameters
    ----------
    submission_request : `~skyportal.models.SubmissionRequest`
        The submission request to send to TNS.
    publishing_bot : `~skyportal.models.ExternalPublishingBot`
        The bot to use for the submission.
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
    tns_headers = get_tns_headers(publishing_bot)
    obj_id = submission_request.obj_id
    data = {
        "api_key": publishing_bot.tns_altdata["api_key"],
        "data": json.dumps(report),
    }

    submission_id = None
    serialized_response = None

    if publishing_bot.testing:
        log(
            f"Publishing bot {publishing_bot.id} is in testing mode, skipping TNS submission for {obj_id}."
        )
        return "testing mode, not submitted", None, None

    # 6 * 4 * 10 seconds = 4 minutes of retries
    max_retries = 24
    retry_delay = 10

    status_code = 0
    for attempt in range(max_retries):
        r = (requests.post(get_tns_url("report"), headers=tns_headers, data=data),)
        status_code = r.status_code

        if status_code == 429:
            status = f"Exceeded TNS API rate limit when submitting {obj_id} with publishing bot {publishing_bot.id}"
            log(f"{status}, waiting {retry_delay} seconds before retrying...")
            time.sleep(retry_delay)
            continue

        if status_code == 200:
            submission_id = r.json()["data"]["report_id"]
            log(
                f"Successfully submitted {obj_id} to TNS with request ID {submission_id} for publishing bot {publishing_bot.id}"
            )
        elif status_code == 401:
            status = f"Unauthorized to submit {obj_id} to TNS with publishing bot {publishing_bot.id}, credentials may be invalid"
        else:
            status = f"Failed to submit {obj_id} to TNS with publishing bot {publishing_bot.id}: {r.content}"
        break
    else:
        # If we reach here, it means we exhausted all retries (for loop completed without break)
        status = f"{status}, and exceeded number of retries ({max_retries})"

    status = f"error: {status}" if status_code != 200 else "submitted"

    if isinstance(r, requests.models.Response):
        # we store the request's TNS response in the database for bookkeeping and debugging
        serialized_response = serialize_requests_response(r)

    return status, submission_id, serialized_response


def submit_to_tns(
    submission_request,
    publishing_bot,
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
                "ExternalPublishingWarning: TNS URL is not configured. Please set 'app.tns.endpoint' in the configuration to use TNS submission."
            )

        obj_id = submission_request.obj_id
        tns_altdata = publishing_bot.tns_altdata

        if not tns_altdata or "api_key" not in tns_altdata:
            raise ValueError(
                f"ExternalPublishingError: No TNS API key found for publishing bot {publishing_bot.id}."
            )

        # Validate that the object ID is valid for submission to TNS with the given TNS source group ID.
        if publishing_bot.source_group_id not in TNS_SOURCE_GROUP_NAMING_CONVENTIONS:
            raise ValueError(
                f"ExternalPublishingError: Unknown naming convention for TNS source group ID {publishing_bot.source_group_id}, cannot validate object ID."
            )
        regex_pattern = TNS_SOURCE_GROUP_NAMING_CONVENTIONS[
            publishing_bot.source_group_id
        ]
        if not re.match(regex_pattern, obj_id):
            raise ValueError(
                f"ExternalPublishingError: Object ID {obj_id} does not match the expected naming convention for TNS source group ID {publishing_bot.source_group_id}."
            )

        apply_existing_tnsreport_rules(publishing_bot, submission_request)

        archival = submission_request.archival
        archival_comment = submission_request.archival_comment
        if archival and not archival_comment:
            raise ValueError(
                f"ExternalPublishingError: Archival submission requested for {obj_id} but no archival_comment provided."
            )

        photometry = [serialize(phot, "ab", "mag") for phot in photometry]
        tns_report = build_tns_report(
            submission_request,
            publishing_bot,
            reporters,
            remarks,
            photometry,
            photometry_options,
            stream_ids,
            session,
        )
        submission_request.payload = json.dumps(tns_report)

        # submit the report to TNS
        status, submission_id, serialized_response = send_tns_report(
            submission_request, publishing_bot, tns_report
        )
        submission_request.tns_submission_id = submission_id
        submission_request.tns_response = serialized_response

        notif_text = status
        if status in ["submitted", "testing mode, not submitted"]:
            if status == "testing mode, not submitted":
                notif_text = f"Successfully created TNS report for {submission_request.obj_id} (testing mode, not submitted)."
            else:
                notif_text = (
                    f"Successfully submitted {submission_request.obj_id} to TNS."
                )
            if warning:
                status = f"{status} (warning: {warning})"
                notif_text += f"; Warning: {warning}"

    except Exception as e:
        error = str(e)
        notif_type = (
            "warning"
            if "ExternalPublishingWarning:" in error or "already posted" in error
            else "error",
        )

        e = re.sub(r"ExternalPublishing(Error|Warning): ", "", error)
        notif_text = f"TNS error: {e}"
        status = f"Error: {e}"
        log(str(e))

    try:
        flow = Flow()
        flow.push(
            "*",
            "skyportal/REFRESH_EXTERNAL_PUBLISHING_SUBMISSIONS",
            payload={"external_publishing_bot_id": publishing_bot.id},
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


def check_at_report(submission_id, publishing_bot):
    """Check the status of a report submission to TNS, verifying that the submission was successful (or not).

    Parameters
    ----------
    submission_id : int
        The ID of the submission request to check on TNS.
    publishing_bot : `~skyportal.models.ExternalPublishingBot`
        The bot to use for the check.

    Returns
    -------
    obj_name : str
        The TNS name of the object for which the report was submitted.
    response : dict
        The response from TNS, serialized as a dictionary.
    """

    obj_name, response = None, None

    data = {
        "api_key": publishing_bot.tns_altdata["api_key"],
        "report_id": submission_id,
    }

    max_retries = 24
    retry_delay = 10
    status_code = None
    for _ in range(max_retries):
        r = requests.post(
            get_tns_url("report_reply"),
            headers=get_tns_headers(publishing_bot),
            data=data,
        )
        status_code = r.status_code
        if status_code != 429:
            break
        time.sleep(retry_delay)

    if status_code not in [200, 400, 404]:
        raise ValueError(f"ExternalPublishingError: Error checking report: {r.text}")

    try:
        response = serialize_requests_response(r)
    except Exception as e:
        raise ValueError(f"ExternalPublishingError: Error serializing response: {e}")

    if status_code == 404:
        return None, response, "report not found"

    try:
        at_report = r.json().get("data", {}).get("feedback", {}).get("at_report", [])
    except Exception:
        raise ValueError(
            "ExternalPublishingError: Could not find AT report in response."
        )

    if not at_report or not isinstance(at_report, list):
        raise ValueError(
            "ExternalPublishingError: No AT report data found in response."
        )

    # An identical AT report (sender, RA\/DEC, discovery date) already exists.
    if "An identical AT report" in str(at_report):
        return None, response, None
    at_report = at_report[0]

    if status_code == 400:
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
            raise ValueError(
                "ExternalPublishingError: Report received but not yet processed."
            )

        if "100" in status_keys:
            # an object has been created along with the report
            obj_name = at_report["100"]["objname"]
            if obj_name is None:
                raise ValueError(
                    "ExternalPublishingError: Object created and report posted but no name found."
                )
        elif "101" in status_keys:
            # object already exists, no new object created but report processed
            obj_name = at_report["101"]["objname"]
            if obj_name is None:
                raise ValueError(
                    "ExternalPublishingError: Object found and report posted but no name found."
                )
    except Exception as e:
        if "ExternalPublishingError:" in str(e):
            raise e
        log(f"Error checking report: {e}")
        raise ValueError(f"ExternalPublishingError: Error checking report: {e}")

    # for now catching errors from TNS is not implemented, so we just return None for the error
    return obj_name, response, None
