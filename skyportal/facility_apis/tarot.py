import functools
import re
from datetime import datetime, timedelta

import astroplan
import astropy.units as u
import numpy as np
import requests
from astroplan.moon import moon_phase_angle
from astropy.coordinates import SkyCoord
from astropy.time import Time, TimeDelta

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ..utils import http
from ..utils.calculations import get_next_valid_observing_time
from . import FollowUpAPI

env, cfg = load_env()

log = make_log("facility_apis/tarot")

station_dict = {
    "Tarot_Calern": {
        "filters": ["NoFilter", "g", "r", "i"],
        "status_url": 1,
    },
    "Tarot_Chili": {
        "filters": ["NoFilter", "g", "r", "i"],
        "status_url": 2,
    },
    "Tarot_Reunion": {
        "filters": ["NoFilter"],
        "status_url": 8,
    },
}

filters_value = {
    "NoFilter": 0,
    "g": 13,
    "r": 14,
    "i": 15,
}

tarot_proxy_endpoint = cfg.get("app.tarot_proxy_endpoint")


def get_header(altdata):
    return {
        "Authorization": f"token {altdata['proxy_token']}",
        "X-Browser-Username": altdata["browser_username"],
        "X-Browser-Password": altdata["browser_password"],
    }


def catch_timeout_and_no_endpoint(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if tarot_proxy_endpoint is None:
            raise ValueError("TAROT proxy endpoint not configured")
        try:
            return func(*args, **kwargs)
        except requests.exceptions.Timeout:
            raise ValueError("Unable to reach the TAROT server")

    return wrapper


def get_observing_time(session, request):
    """Get the next valid observing time for the request range and instrument.

    Parameters
    ----------
    session: sqlalchemy.Session
        The database session.
    request: skyportal.models.FollowupRequest
        The request to get the observing time for.

    Returns
    -------
    observing_time: `astropy.time.Time`
        The next valid observing time.
    """
    from ..models import Telescope

    telescope = session.scalar(
        Telescope.select(session.user_or_token, mode="read").where(
            Telescope.id == request.instrument.telescope_id
        )
    )
    try:
        return get_next_valid_observing_time(
            start_time=Time(request.payload["start_date"], format="iso"),
            end_time=Time(request.payload["end_date"], format="iso"),
            telescope=telescope,
            target=astroplan.FixedTarget(
                SkyCoord(ra=request.obj.ra * u.deg, dec=request.obj.dec * u.deg),
                name=request.obj.id,
            ),
            airmass=request.payload["airmass"],
            observe_at_optimal_airmass=request.payload["observation_preference"]
            == "Optimal Airmass",
        )
    except Exception as e:
        raise ValueError(f"Error trying to get the next valid observing time. {str(e)}")


def check_specific_config(request):
    """Check the specific configuration data for the instrument.

    Parameters
    ----------
    request: skyportal.models.FollowupRequest
        The request to check the specific configuration data for.

    Returns
    -------
    specific_config: dict
        The specific configuration data for the instrument.
    """
    if request.instrument.configuration_data is None:
        raise ValueError("Instrument configuration data is missing")
    specific_config = request.instrument.configuration_data.get(
        "specific_configuration"
    )
    if specific_config is None:
        raise ValueError("Instrument specific data is missing")
    if "station_name" not in specific_config:
        raise ValueError(f"Missing station_name in specific configuration data")
    if specific_config["station_name"] not in station_dict:
        raise ValueError(
            f"Invalid station name in specific configuration, must be one of {', '.join(station_dict.keys())}"
        )

    return specific_config


def check_payload(payload, station_name):
    """Check the payload for a follow-up request to TAROT.

    Parameters
    ----------
    payload: dict
        The payload coming from the request.
    """

    required_params = {
        "start_date",
        "end_date",
        "observation_preference",
        "priority",
        "exposure_time",
        "exposure_counts",
        "airmass",
        "filters",
    }

    missing_params = required_params - payload.keys()
    if missing_params:
        raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")

    if not set(payload["filters"]).issubset(set(station_dict[station_name]["filters"])):
        raise ValueError(
            f"Instrument filters not in Tarot allowed filters ({', '.join(station_dict[station_name]['filters'])})."
        )

    if payload["start_date"] > payload["end_date"]:
        raise ValueError("start_date must be before end_date.")

    if payload["end_date"] < str(datetime.utcnow()):
        raise ValueError("end_date must be in the future.")

    if payload["observation_preference"] not in [
        "Earliest possible",
        "Optimal Airmass",
    ]:
        raise ValueError(
            "observation_preference must be one of 'Earliest possible', 'Optimal Airmass'."
        )

    if payload["exposure_time"] < 0 and payload["exposure_time"] != -1:
        raise ValueError("exposure_time must be positive or -1.")


def get_filters_exposures(last_detected_mag, phase_angle, station_name):
    filters_exposures = {}

    if station_name in ["Tarot_Calern", "Tarot_Chili"]:
        if last_detected_mag <= 17.0:
            if phase_angle > 60:
                filters_exposures = {
                    "r": [15, 120],
                    "g": [0, 0],
                    "i": [0, 0],
                    "NoFilter": [6, 120],
                }
            else:
                filters_exposures = {
                    "r": [8, 120],
                    "g": [0, 0],
                    "i": [8, 120],
                    "NoFilter": [4, 120],
                }
        elif 17.0 < last_detected_mag < 19.0:
            if phase_angle > 60:
                filters_exposures = {
                    "r": [22, 120],
                    "g": [0, 0],
                    "i": [0, 0],
                    "NoFilter": [15, 120],
                }
            else:
                filters_exposures = {
                    "r": [8, 200],
                    "g": [0, 0],
                    "i": [8, 200],
                    "NoFilter": [6, 120],
                }
        else:
            if phase_angle > 60:
                filters_exposures = {
                    "r": [0, 0],
                    "g": [0, 0],
                    "i": [0, 0],
                    "NoFilter": [15, 200],
                }
            else:
                filters_exposures = {
                    "r": [12, 200],
                    "g": [0, 0],
                    "i": [12, 200] if station_name is "Tarot_Calern" else [0, 0],
                    "NoFilter": [12, 120],
                }

    elif station_name == "Tarot_Reunion":
        if last_detected_mag <= 17.0:
            filters_exposures = {
                "NoFilter": [12, 120] if phase_angle > 60 else [8, 120]
            }
        elif 17.0 < last_detected_mag < 19.0:
            filters_exposures = {
                "NoFilter": [18, 120] if phase_angle > 60 else [12, 200]
            }
        else:
            filters_exposures = {"NoFilter": [0, 0] if phase_angle > 60 else [18, 200]}

    return filters_exposures


def create_request_string(obj, payload, observation_time, station_name):
    """Create the request string to send to TAROT.

    Parameters
    ----------
    obj: skyportal.models.Obj
        The object to observe.
    payload: dict
        The payload coming from the request.
    observation_time: `astropy.time.Time`
        The observation time to send to TAROT.
    station_name: str
        The Tarot station name use for the request.
    """
    tt = observation_time

    observations = []

    if payload["exposure_time"] == -1:
        photstats = obj.photstats
        if len(photstats) == 0:
            raise ValueError("No photometry to base exposure time calculation on")
        photstats = photstats[0]
        last_detected_mag = photstats.last_detected_mag

        if last_detected_mag is None:
            raise ValueError("No detections to base exposure time calculation on")

        phase_angle = np.rad2deg(moon_phase_angle(tt).value)
        filters_exposures = get_filters_exposures(
            last_detected_mag, phase_angle, station_name
        )

        observations = []
        for filter_name, exposures in filters_exposures.items():
            exposure_count, exposure_time = exposures
            observations.extend(
                [f"{exposure_time} {filters_value[filter_name]}"] * exposure_count
            )
    else:
        for filter_name in payload["filters"]:
            observations.append(
                f"{payload['exposure_time']} {filters_value[filter_name]}"
            )
        observations = sum([observations] * payload["exposure_counts"], [])

    total_time = 0.0
    observation_string = ""
    number_of_strings, remainder = np.divmod(len(observations), 6)
    for ii in range(number_of_strings + 1):
        obs_filler = []
        if ii == number_of_strings and remainder != 0:
            obs_filler = ["0 0"] * (6 - int(remainder) - 1) + ["0 0 "]

        obs = observations[ii * 6 : (ii + 1) * 6]
        ttline = tt + (total_time * u.s)

        if obs:
            observation_string += f'"{obj.id}" {obj.ra} {obj.dec} {ttline.isot} 0.004180983 0.00 {" ".join(obs)} {" ".join(obs_filler)}{payload["priority"]} {station_name}\n\r'

        if ii != number_of_strings:
            total_time += sum(45 + int(o.split(" ")[0]) for o in obs)

    return observation_string


def check_altdata(altdata):
    required_altdata_keys = {
        "request_id",
        "proxy_token",
        "browser_username",
        "browser_password",
        "username",
        "password",
    }

    missing_keys = required_altdata_keys - set(altdata.keys() if altdata else [])
    if missing_keys:
        raise ValueError(f"Missing credentials: {', '.join(missing_keys)}.")
    return altdata


def login_to_tarot(request, session, altdata):
    """Login to TAROT and return the hash user.

    Parameters
    ----------
    request: skyportal.models.FollowupRequest
        The request to send to TAROT.
    session: sqlalchemy.Session
        The database session.
    altdata: dict
        The altdata dictionary with credentials and request id.

    Returns
    -------
    hash_user: str
        The hash user for the session.
    """
    from ..models import FacilityTransaction

    data = {
        "login": altdata["username"],
        "pass": altdata["password"],
        "Submit": "Entry",
    }

    login_response = requests.post(
        f"{tarot_proxy_endpoint}/manage/manage/login.php",
        data=data,
        headers=get_header(altdata),
        timeout=7.0,
    )

    error = None
    if login_response.status_code == 500 and "timeout" in login_response.text:
        error = "impossible to connect to TAROT, timeout error."
    if login_response.status_code == 401:
        if "Authentication required" in login_response.text:
            error = "unauthorized access to tarot. Update tarot credentials of this allocation."
        else:
            error = (
                "unauthorized access to Icare. Update Icare token of this allocation."
            )
    elif login_response.status_code == 200 and "hashuser" in login_response.text:
        hash_user = login_response.text.split("hashuser=")[1][:20]
        if hash_user is not None and len(hash_user) == 20:
            return hash_user
        else:
            error = "tarot hashuser not found in login response"

    transaction = FacilityTransaction(
        request=http.serialize_requests_request(login_response.request),
        response=http.serialize_requests_response(login_response),
        followup_request=request,
        initiator_id=request.last_modified_by_id,
    )
    session.add(transaction)
    raise ValueError(error if error else f"unexpected error trying to login to TAROT")


class TAROTAPI(FollowUpAPI):
    """SkyPortal interface to the TAROT"""

    @staticmethod
    @catch_timeout_and_no_endpoint
    def submit(request, session, **kwargs):
        """Submit a follow-up request to TAROT.
        For TAROT, this means adding a new scene to a request already created.
        One scene is created for each group of 6 or less exposure_count * filter.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to submit.
        session: sqlalchemy.Session
            Database session for this transaction
        """
        from ..models import FacilityTransaction

        altdata = check_altdata(request.allocation.altdata)
        specific_config = check_specific_config(request)
        check_payload(request.payload, specific_config["station_name"])

        hash_user = login_to_tarot(request, session, altdata)

        # Set the start date to be at least 10 minutes in the future to avoid issues with the TAROT server
        # This code is a workaround and should be removed after finding a solution
        minimum_observing_time = Time.now() + TimeDelta(600, format="sec")
        if request.payload["start_date"] < minimum_observing_time:
            request.payload["start_date"] = minimum_observing_time.iso

        observing_time = get_observing_time(session, request)
        observation_string = create_request_string(
            request.obj,
            request.payload,
            observing_time,
            specific_config["station_name"],
        )

        # Create one or more new scene in a request using an observation string
        payload = {
            "type": "defaultshort",
            "mod": "new",
            "idreq": altdata["request_id"],
            "idscene": "0",
            "hashuser": hash_user,
            "check[type]": "IM",
            "data": observation_string,
            "Submit": "Ok for quick depot",
        }

        response = requests.post(
            f"{tarot_proxy_endpoint}/manage/manage/depot/depot-defaultshort.res.php?hashuser={hash_user}&idreq={altdata['request_id']}",
            data=payload,
            headers=get_header(altdata),
            timeout=7.0,
        )

        if "New Scene Inserted" not in response.text:
            error_response = f"rejected: status code = {response.status_code}. "
            if response.status_code == 200:
                error_response += "Scene not Inserted" + (
                    " - Hashuser not valid" if "secu_erreur" in response.text else ""
                )
            request.status = error_response
        else:
            request.comment = f"observing_time:{observing_time.isot}"
            request.status = f"submitted for {observing_time.strftime('%Y-%m-%d %H:%M:%S')}: use retrieve to check status"

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

    @staticmethod
    @catch_timeout_and_no_endpoint
    def get(request, session, **kwargs):
        """Get the status of a follow-up request from TAROT.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to get the status for.
        session: sqlalchemy.Session
            Database session for this transaction
        """
        from ..models import FacilityTransaction

        altdata = check_altdata(request.allocation.altdata)
        specific_config = check_specific_config(request)

        try:
            # If request exposure_count * nb_filter > 6, multiple scenes are created
            # But we only check the status and time of the first scene
            insert_scene_id = re.findall(
                r"insert_id\s*=\s*(\d+)",
                request.transactions[-1].response["content"],
            )[0]
            manager_scene_id = f"{str(insert_scene_id)[0]}_{str(insert_scene_id)[1:]}"
            observing_time = Time(
                re.search(r"observing_time:(.*)", request.comment).group(1)
            )
        except Exception:
            raise ValueError("Error trying to get the scene id and observing time")

        nb_observation = None
        if not request.status.startswith("submitted: planified"):
            # if the request is not planified, check the status of the request
            response = requests.get(
                f"{tarot_proxy_endpoint}/rejected{station_dict[specific_config['station_name']]['status_url']}.txt",
                headers=get_header(altdata),
                timeout=7.0,
            )

            if response.status_code != 200:
                transaction = FacilityTransaction(
                    request=http.serialize_requests_request(response.request),
                    response=http.serialize_requests_response(response),
                    followup_request=request,
                    initiator_id=request.last_modified_by_id,
                )
                session.add(transaction)
                raise ValueError("Error trying to get the status of the request")

            pattern = rf"\b\d*{re.escape(manager_scene_id)}\d*\b.*?{request.obj.id}.*?\((\d+)\)"
            match_status = re.search(pattern, response.text)

            # To check the request status, an identifier is retrieved from each scene on TAROT manager,
            # Each identifier corresponds to a different status, as shown below:
            status_dict = {
                "1": "rejected: date is before the current/upcoming night.",
                "2": "submitted: planned for a future night.",
                "3": "rejected: never visible within the specified range.",
                "4": "rejected: over quota.",
                "5": "submitted: planified.",
                "6": "submitted: planified over.",
            }

            if not match_status or not match_status.groups():
                if observing_time > datetime.utcnow() + timedelta(days=1):
                    request.status = f"submitted for {observing_time.strftime('%Y-%m-%d %H:%M:%S')}: check back 24 hours before your scheduled observation time."
                elif observing_time >= datetime.utcnow():
                    # If the status is not found, it means the tarot server is not yet aware of the request
                    return
                # if observing time is in the past, we pass here and will check the observation status in a future step
            else:
                request.status = status_dict.get(
                    match_status.group(1), "rejected: not planified"
                )

        if "submitted: planified" in request.status:
            # try to retrieve the time of the planified request from the sequenced file
            response_sequenced = requests.get(
                f"{tarot_proxy_endpoint}/sequenced{station_dict[specific_config['station_name']]['status_url']}.txt",
                headers=get_header(altdata),
                timeout=7.0,
            )
            if response_sequenced.status_code != 200:
                transaction = FacilityTransaction(
                    request=http.serialize_requests_request(response_sequenced.request),
                    response=http.serialize_requests_response(response_sequenced),
                    followup_request=request,
                    initiator_id=request.last_modified_by_id,
                )
                session.add(transaction)
                raise ValueError(
                    "Error trying to get the time of the planified request"
                )

            try:
                pattern = rf".*{re.escape(manager_scene_id)}.*?{request.obj.id}"
                sequenced_info = re.search(pattern, response_sequenced.text)
                # Regex to capture date and time in the format "YYYY-MM-DDTHH:MM:SS.SSS"
                pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3}"
                # Extract the second date and time which is the real beginning of the observation
                observing_time = Time(re.findall(pattern, sequenced_info.group(0))[1])
                request.comment = f"observing_time:{observing_time.isot}"
                request.status = f"submitted: planified for {observing_time.strftime('%Y-%m-%d %H:%M:%S')}."
            except Exception:
                pass

        if (
            not request.status.startswith("rejected")
            and observing_time < datetime.utcnow()
        ):
            # check if the scene has been observed
            response_observation = requests.get(
                f"{tarot_proxy_endpoint}/{specific_config['station_name'].lower()}/",
                headers=get_header(altdata),
                timeout=7.0,
            )

            if response_observation.status_code != 200:
                transaction = FacilityTransaction(
                    request=http.serialize_requests_request(
                        response_observation.request
                    ),
                    response=http.serialize_requests_response(response_observation),
                    followup_request=request,
                    initiator_id=request.last_modified_by_id,
                )
                session.add(transaction)
                raise ValueError("Observation log currently unavailable on TAROT")

            if manager_scene_id in response_observation.text:
                nb_observation = response_observation.text.count(manager_scene_id)
                request.status = f"complete"
            elif observing_time + timedelta(hours=3) < datetime.utcnow():
                previous_status = (
                    "planified"
                    if request.status.startswith("planified")
                    else "submitted"
                )
                request.status = f"rejected: {previous_status} but observation failed due to a TAROT error"

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
            if "complete" in request.status and nb_observation:
                flow.push(
                    request.last_modified_by_id,
                    "baselayer/SHOW_NOTIFICATION",
                    payload={
                        "note": f"Target has been observed {nb_observation} times",
                        "type": "info",
                    },
                )
        except Exception as e:
            log(f"Failed to send notification: {str(e)}")

    @staticmethod
    @catch_timeout_and_no_endpoint
    def delete(request, session, **kwargs):
        """Delete a follow-up request from TAROT queue.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to delete from the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransaction, FollowupRequest

        last_modified_by_id = request.last_modified_by_id
        obj_internal_key = request.obj.internal_key

        is_error_on_delete = None

        # this happens for failed submissions, just go ahead and delete
        if len(request.transactions) == 0:
            session.query(FollowupRequest).filter(
                FollowupRequest.id == request.id
            ).delete()
            session.commit()
        else:
            insert_scene_ids = re.findall(
                r"insert_id\s*=\s*(\d+)",
                request.transactions[-1].response["content"],
            )
            if insert_scene_ids:
                altdata = check_altdata(request.allocation.altdata)
                hash_user = login_to_tarot(request, session, altdata)
                data = {"check[]": insert_scene_ids, "remove": "Remove Scenes"}

                response = requests.post(
                    f"{tarot_proxy_endpoint}/manage/manage/liste_scene.php?hashuser={hash_user}&idreq={altdata['request_id']}",
                    data=data,
                    headers=get_header(altdata),
                    timeout=7.0,
                )
                if response.status_code != 200:
                    is_error_on_delete = response.content
                else:
                    for scene_id in insert_scene_ids:
                        if f"Scene '{scene_id}' removed" not in response.text:
                            is_error_on_delete = response.content
                            break

                transaction = FacilityTransaction(
                    request=http.serialize_requests_request(response.request),
                    response=http.serialize_requests_response(response),
                    followup_request=request,
                    initiator_id=request.last_modified_by_id,
                )

                session.add(transaction)
                session.commit()

            request.status = (
                "deleted"
                if is_error_on_delete is None
                else f"rejected: deletion failed - {is_error_on_delete}"
            )

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

    def custom_json_schema(instrument, user, **kwargs):
        config = instrument.configuration_data
        return {
            "type": "object",
            "properties": {
                "filters": {
                    "type": "array",
                    "title": "Filters",
                    "uniqueItems": True,
                    "minItems": 1,
                    **(
                        {
                            "description": "⚠️ No station name selected in the instrument configuration",
                            "readonly": True,
                            "items": {
                                "type": "string",
                                "enum": [],
                            },
                        }
                        if not config
                        or not config.get("specific_configuration", {}).get(
                            "station_name"
                        )
                        in station_dict
                        else {
                            "items": {
                                "type": "string",
                                "enum": station_dict[
                                    config["specific_configuration"]["station_name"]
                                ]["filters"],
                            },
                        }
                    ),
                },
                "start_date": {
                    "type": "string",
                    "default": str(datetime.utcnow()).replace("T", ""),
                    "title": "Start Date (UT)",
                },
                "end_date": {
                    "type": "string",
                    "title": "End Date (UT)",
                    "default": str(datetime.utcnow() + timedelta(days=7)).replace(
                        "T", ""
                    ),
                },
                "observation_preference": {
                    "type": "string",
                    "title": "Observation Preference",
                    "enum": [
                        "Earliest possible",
                        "Optimal Airmass",
                    ],
                    "default": "Earliest possible",
                },
                "priority": {
                    "type": "number",
                    "default": 0,
                    "minimum": -5.0,
                    "maximum": 5.0,
                    "title": "Priority (-5 - 5)",
                },
                "exposure_time": {
                    "title": "Exposure Time [s] (use -1 if want defaults)",
                    "type": "number",
                    "default": 300.0,
                },
                "exposure_counts": {
                    "title": "Exposure Counts",
                    "type": "number",
                    "default": 5,
                },
                "airmass": {
                    "title": "Airmass limit",
                    "type": "number",
                    "default": 2.8,
                },
            },
            "required": [
                "start_date",
                "end_date",
                "observation_preference",
                "priority",
                "exposure_time",
                "exposure_counts",
                "airmass",
                "filters",
            ],
        }

    ui_json_schema = {"filters": {"ui:widget": "checkboxes"}}

    form_json_schema_altdata = {
        "type": "object",
        "properties": {
            "proxy_token": {
                "type": "string",
                "title": "Icare Token",
                "description": "This is the token used to authenticate with the TAROT proxy server.",
            },
            "request_id": {
                "type": "string",
                "title": "Request ID to add scene to (2282 for skyportal)",
            },
            "browser_username": {
                "type": "string",
                "title": "Browser Username",
            },
            "browser_password": {
                "type": "string",
                "title": "Browser Password",
            },
            "username": {
                "type": "string",
                "title": "Username",
            },
            "password": {
                "type": "string",
                "title": "Password",
            },
        },
        "required": [
            "browser_username",
            "browser_password",
            "username",
            "password",
            "request_id",
        ],
    }

    form_json_schema_config = {
        "type": "object",
        "properties": {
            "station_name": {
                "type": "string",
                "title": "Station Name use for the request",
                "enum": list(station_dict.keys()),
            },
        },
    }

    priorityOrder = "desc"
