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
    SURVEYS,
    TNS_INSTRUMENT_IDS,
    TNS_OTHER_INSTRUMENT_ID,
    TNS_URL,
    get_IAUname,
    get_internal_names,
    get_tns_headers,
    get_tns_object_id_and_data_source_id,
    get_tns_url,
    tns_classification_id,
    tns_spectrum_type_id,
)

env, cfg = load_env()

log = make_log("tns_submission_utils")


# Custom exception to catch sharing issues we want to notify as warnings
class TNSWarning(Exception):
    pass


def apply_existing_tns_report_rules(
    sharing_service, submission_request, internal_name=None
):
    """Apply the rules for existing TNS reports to the submission request.

    Parameters
    ----------
    sharing_service : `~skyportal.models.SharingService`
        The sharing service to use for the submission.
    submission_request : `~skyportal.models.SharingServiceSubmission`
        The submission request.
    internal_name : str, optional
        The TNS internal name to use (possibly normalized from obj_id).
        If None, uses submission_request.obj_id.
    """
    # if the sharing service is set up to only report objects to TNS if they are not already there,
    # we check if an object is already on TNS (within 2 arcsec of the object's position)
    # and if it is, we skip the submission
    # otherwise, we submit as long as there are no reports with the same internal source name
    # (i.e. the same obj_id from the same survey)
    altdata = sharing_service.tns_altdata
    obj_id = submission_request.obj_id
    tns_internal_name = internal_name or obj_id
    tns_headers = get_tns_headers(
        sharing_service.tns_bot_id, sharing_service.tns_bot_name
    )

    # if the sharing service is in test mode, we skip the existing TNS report check
    if sharing_service.testing:
        log(f"Skipping existing TNS report check for {obj_id} in test mode.")
        return

    _, existing_tns_name = get_IAUname(
        altdata["api_key"], tns_headers, obj_id=tns_internal_name, closest=True
    )
    if existing_tns_name is not None:
        if not sharing_service.publish_existing_tns_objects:
            raise TNSWarning(f"{obj_id} already posted to TNS as {existing_tns_name}.")
        else:
            # look if the object on TNS has already been reported by the same survey (same internal name, here being the obj_id)
            internal_names = get_internal_names(
                altdata["api_key"], tns_headers, tns_name=existing_tns_name
            )
            if len(internal_names) > 0 and tns_internal_name in internal_names:
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
    tns_internal_name,
    tns_data_source_id,
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
    tns_internal_name : str
        The TNS internal name to use (possibly normalized from obj_id).
    tns_data_source_id : int
        The TNS discovery data source ID of the survey

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
    first = detections[0]
    time_first = first["mjd"]
    non_detections = sorted(
        (p for p in non_detections if p["mjd"] < time_first),
        key=lambda p: p["mjd"],
    )

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
            f"{sharing_service.name} sharing service require at least one non-detection prior to the first detection, but none were found. Select Archival mode to submit to TNS without non-detections."
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
        "discovery_data_source_id": tns_data_source_id,
        "internal_name_format": {
            "prefix": phot_first["instrument_value"],
            "year_format": "YY",
            "postfix": "",
        },
        "internal_name": tns_internal_name,
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


def spectrum_ascii(spectrum):
    """The spectrum as the two- or three-column ASCII text TNS accepts.

    TNS stores the file and the classification report references it by the name
    it was stored under, so the upload has to carry the data itself rather than
    a link to it.
    """
    errors = spectrum.errors
    rows = []
    for index, (wavelength, flux) in enumerate(
        zip(spectrum.wavelengths, spectrum.fluxes)
    ):
        if errors is not None and index < len(errors) and errors[index] is not None:
            rows.append(f"{wavelength:.4f} {flux:.6g} {errors[index]:.6g}")
        else:
            rows.append(f"{wavelength:.4f} {flux:.6g}")
    return "\n".join(rows) + "\n"


def upload_spectrum_to_tns(
    spectrum_name, spectrum_text, tns_bot_id, tns_bot_name, api_key, testing
):
    """Upload one ASCII spectrum to TNS and return the name TNS stored it under.

    A classification report names its spectrum by that stored name, so this has
    to run, and succeed, before the report is built.

    Returns
    -------
    stored_name : str or None
        The name TNS stored the file under, or None in testing mode.
    """
    if testing:
        log(f"Testing mode, not uploading spectrum {spectrum_name} to TNS.")
        return None

    headers = get_tns_headers(tns_bot_id, tns_bot_name)
    response = requests.post(
        get_tns_url("file_upload"),
        headers=headers,
        data={"api_key": api_key},
        files=[("files[]", (spectrum_name, spectrum_text, "text/plain"))],
        timeout=30,
    )
    if response.status_code != 200:
        raise ValueError(
            f"Failed to upload spectrum {spectrum_name} to TNS: "
            f"{response.status_code} {response.content}"
        )

    uploaded = (response.json().get("data") or {}).get("media_file", [])
    if isinstance(uploaded, str):
        uploaded = [uploaded]
    if not uploaded:
        raise ValueError(
            f"TNS accepted the upload of {spectrum_name} but named no stored file."
        )
    return uploaded[0]


def build_tns_classification_report(
    iau_name,
    classification,
    classifiers,
    spectrum,
    stored_spectrum_name,
    sharing_service,
    redshift=None,
    remarks=None,
    spectrum_remarks=None,
):
    """Build the classification report for a TNS submission.

    Unlike an AT report, which announces a discovery, this one classifies an
    object TNS already knows about, so it is keyed by the IAU name rather than
    an internal survey name and it must reference an already-uploaded spectrum.

    Parameters
    ----------
    iau_name : str
        The object's IAU name without its prefix (e.g. "2023abc").
    classification : str
        The classification name, as the taxonomy spells it.
    classifiers : str
        The classifier string credited on the report.
    spectrum : `~skyportal.models.Spectrum`
        The spectrum the classification rests on.
    stored_spectrum_name : str
        The name TNS stored the uploaded spectrum under.
    sharing_service : `~skyportal.models.SharingService`
        The sharing service the report is filed by.
    redshift : float, optional
        The redshift to report.
    remarks : str, optional
        Remarks on the classification.
    spectrum_remarks : str, optional
        Remarks on the spectrum.

    Returns
    -------
    dict
        The classification report to submit.
    """
    objtypeid = tns_classification_id(classification)
    if objtypeid is None:
        raise ValueError(
            f"Classification {classification!r} has no TNS object type id; "
            "add it to TNS_CLASSIFICATION_IDS to report this class."
        )

    instrument_name = str(spectrum.instrument.name or "").lower()
    instrument_id = TNS_INSTRUMENT_IDS.get(instrument_name, TNS_OTHER_INSTRUMENT_ID)
    if isinstance(instrument_id, list):
        instrument_id = instrument_id[0]

    altdata = spectrum.altdata or {}
    spectrum_entry = {
        "obsdate": spectrum.observed_at.strftime("%Y-%m-%d %H:%M:%S"),
        "instrumentid": instrument_id,
        "exptime": altdata.get("EXPTIME", altdata.get("exptime", "")),
        "observer": ", ".join(
            str(o.first_name or "") + " " + str(o.last_name or "")
            for o in (spectrum.observers or [])
        ).strip(", "),
        "reducer": ", ".join(
            str(r.first_name or "") + " " + str(r.last_name or "")
            for r in (spectrum.reducers or [])
        ).strip(", "),
        "spectypeid": tns_spectrum_type_id(spectrum.type),
        "ascii_file": stored_spectrum_name,
        "fits_file": "",
        "remarks": spectrum_remarks or "",
    }

    report = {
        "name": iau_name,
        "classifier": classifiers,
        "objtypeid": objtypeid,
        "redshift": redshift if redshift is not None else "",
        "groupid": sharing_service.tns_source_group_id,
        "remarks": remarks or "",
        "spectra": {"spectra-group": {"0": spectrum_entry}},
    }

    return {"classification_report": {"0": report}}


def strip_iau_prefix(tns_name):
    """The bare IAU name TNS reports expect, e.g. "SN 2026abc" -> "2026abc"."""
    return str(tns_name or "").replace("AT", "").replace("SN", "").strip()


def prepare_tns_classification_report(
    submission_request, sharing_service, reporters, remarks, session
):
    """Resolve what to classify, upload its spectrum, and build the report.

    A classification report names an object TNS already knows about, so the
    object needs an IAU name; it rests on one spectrum, which TNS must already
    hold. Both the classification and the spectrum are taken as the most recent
    the submitting user can read, which is what a daily classification pass
    reports and keeps the choice predictable.

    Returns
    -------
    dict
        The classification report to send.
    """
    from skyportal.models import Classification, Obj, Spectrum, User

    obj_id = submission_request.obj_id
    user = session.scalar(sa.select(User).where(User.id == submission_request.user_id))
    obj = session.scalar(sa.select(Obj).where(Obj.id == obj_id))
    if obj is None:
        raise ValueError(f"Object {obj_id} not found.")

    tns_name = obj.tns_name
    if is_null(tns_name):
        _, tns_name = get_IAUname(
            sharing_service.tns_altdata["api_key"],
            get_tns_headers(sharing_service.tns_bot_id, sharing_service.tns_bot_name),
            obj_id=obj_id,
        )
    iau_name = strip_iau_prefix(tns_name)
    if not iau_name:
        raise TNSWarning(
            f"{obj_id} has no IAU name on TNS, so there is nothing to classify; "
            "report it as a discovery first."
        )

    classification = session.scalars(
        Classification.select(user)
        .where(Classification.obj_id == obj_id)
        .order_by(Classification.created_at.desc())
    ).first()
    if classification is None:
        raise TNSWarning(f"{obj_id} has no classification to report.")

    spectrum = session.scalars(
        Spectrum.select(user)
        .where(Spectrum.obj_id == obj_id)
        .order_by(Spectrum.observed_at.desc())
    ).first()
    if spectrum is None:
        raise TNSWarning(
            f"{obj_id} has no spectrum, and TNS will not take a classification "
            "without one."
        )

    stored_name = upload_spectrum_to_tns(
        f"{obj_id}_{spectrum.id}.ascii",
        spectrum_ascii(spectrum),
        sharing_service.tns_bot_id,
        sharing_service.tns_bot_name,
        sharing_service.tns_altdata["api_key"],
        sharing_service.testing,
    )

    return build_tns_classification_report(
        iau_name=iau_name,
        classification=classification.classification,
        classifiers=reporters,
        spectrum=spectrum,
        stored_spectrum_name=stored_name or "",
        sharing_service=sharing_service,
        redshift=obj.redshift,
        remarks=remarks,
    )


def send_tns_report(
    obj_id, tns_bot_id, tns_bot_name, api_key, testing, sharing_service_id, report
):
    """Build and send an AT report to TNS.

    Takes plain values (not ORM objects) so the caller can release its DB
    connection before this slow, retrying HTTP call.

    Parameters
    ----------
    obj_id : str
        The object being reported.
    tns_bot_id, tns_bot_name, api_key : str
        TNS bot credentials from the sharing service.
    testing : bool
        Whether the sharing service is in testing mode (skip real submission).
    sharing_service_id : int
        The sharing service id, for logging.
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
    tns_headers = get_tns_headers(tns_bot_id, tns_bot_name)
    data = {
        "api_key": api_key,
        "data": json.dumps(report),
    }

    submission_id = None
    serialized_response = None

    if testing:
        log(
            f"Sharing service {sharing_service_id} is in testing mode, skipping TNS submission for {obj_id}."
        )
        return "Testing mode, not submitted", None, None

    # 24 * 10 seconds = 4 minutes of retries
    max_retries = 24
    retry_delay = 10
    r = None
    exceeded_rate_message = f"Exceeded TNS API rate limit when submitting {obj_id} with sharing service {sharing_service_id}"
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
            f"Successfully submitted {obj_id} to TNS with request ID {submission_id} for sharing service {sharing_service_id}"
        )
        status = "submitted"
    elif r.status_code == 401:
        status = f"Error: Unauthorized to submit {obj_id} to TNS with sharing service {sharing_service_id}, credentials may be invalid"
    elif r.status_code == 429:
        status = f"Error: {exceeded_rate_message}, and exceeded number of retries ({max_retries})"
    else:
        status = f"Error: Failed to submit {obj_id} to TNS with sharing service {sharing_service_id}: {r.content}"

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
    # Snapshot ids up front: the flow push below also runs on early-error paths,
    # and these ORM attrs expire once we commit before the HTTP call.
    sharing_service_id = sharing_service.id
    user_id = submission_request.user_id
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

        if submission_request.tns_report_type == "classification_report":
            # The object is already on TNS under its own name, so this skips the
            # survey-name normalization and duplicate-report rules an AT report
            # needs; it uploads the spectrum first so the report can name it.
            tns_report = prepare_tns_classification_report(
                submission_request, sharing_service, reporters, remarks, session
            )
        else:
            # Normalize the object ID to TNS-friendly format if a normalizer exists
            tns_internal_name, tns_data_source_id = (
                get_tns_object_id_and_data_source_id(obj_id, photometry)
            )
            if tns_internal_name is None or tns_data_source_id is None:
                raise ValueError(
                    f"Object ID {obj_id} does not match the expected naming convention for any of the supported Surveys {SURVEYS.keys()}."
                )

            apply_existing_tns_report_rules(
                sharing_service, submission_request, internal_name=tns_internal_name
            )

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
                tns_internal_name,
                tns_data_source_id,
            )
        submission_request.tns_payload = json.dumps(tns_report)

        # Snapshot what the HTTP call needs, then commit so the DB connection is
        # released before the slow, retrying TNS submission (no idle-in-txn).
        tns_bot_id = sharing_service.tns_bot_id
        tns_bot_name = sharing_service.tns_bot_name
        api_key = sharing_service.tns_altdata["api_key"]
        testing = sharing_service.testing
        session.commit()

        # submit the report to TNS (no DB transaction open)
        status, submission_id, serialized_response = send_tns_report(
            obj_id,
            tns_bot_id,
            tns_bot_name,
            api_key,
            testing,
            sharing_service_id,
            tns_report,
        )
        submission_request.tns_submission_id = submission_id
        submission_request.tns_response = serialized_response

        notif_text = status
        if status in ["submitted", "Testing mode, not submitted"]:
            if status == "Testing mode, not submitted":
                notif_text = f"Successfully created TNS report for {obj_id} (testing mode, not submitted)."
            else:
                notif_text = f"Successfully submitted {obj_id} to TNS."
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
            payload={"sharing_service_id": sharing_service_id},
        )
        flow.push(
            user_id=user_id,
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
