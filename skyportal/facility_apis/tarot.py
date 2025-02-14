import re
from datetime import datetime

import astropy.units as u
import numpy as np
import requests
from astroplan.moon import moon_phase_angle
from astropy.time import Time

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ..utils import http
from . import FollowUpAPI

env, cfg = load_env()

log = make_log("facility_apis/tarot")

station_dict = {
    "Tarot_Calern": {
        "url_to_request": 1,
        "endpoint": "calern_endpoint",
    },
    "Tarot_Chili": {
        "url_to_request": 2,
        "endpoint": "chili_endpoint",
    },
    "Tarot_Reunion": {
        "url_to_request": 8,
        "endpoint": "reunion_endpoint",
    },
}


def create_observation_string(request):
    """Create the observation string to send to TAROT.

    Parameters
    ----------
    request: skyportal.models.FollowupRequest
        The request information to send to TAROT.
    """

    for param in [
        "station_name",
        "date",
        "exposure_time",
        "exposure_counts",
        "observation_choices",
    ]:
        if param not in request.payload:
            raise ValueError(f"Parameter {param} required.")

    if any(
        obs_filter not in ["g", "r", "i", "NoFilter"]
        for obs_filter in request.payload["observation_choices"]
    ):
        raise ValueError(
            f"Filter configuration {request.payload['observation_choices']} unknown."
        )

    if request.payload["station_name"] not in [
        "Tarot_Calern",
        "Tarot_Chili",
        "Tarot_Reunion",
    ]:
        raise ValueError(
            "observation_type must be Tarot_Calern, Tarot_Chili, Tarot_Reunion"
        )

    if (
        request.payload["exposure_time"] < 0
        and not request.payload["exposure_time"] == -1
    ):
        raise ValueError("exposure_time must be positive or -1.")

    filters = {
        "NoFilter": 0,
        "g": 13,
        "r": 14,
        "i": 15,
    }
    tt = Time(request.payload["date"], format="isot")
    observations = []

    if request.payload["exposure_time"] == -1:
        photstats = request.obj.photstats
        if len(photstats) == 0:
            raise ValueError("No photometry to base exposure time calculation on")
        photstats = photstats[0]
        last_detected_mag = photstats.last_detected_mag

        if last_detected_mag is None:
            raise ValueError("No detections to base exposure time calculation on")

        phase_angle = np.rad2deg(moon_phase_angle(tt).value)

        sequence = {}
        if last_detected_mag <= 17.0:
            if phase_angle > 60:
                sequence = {
                    "Tarot_Calern": {
                        "r": [15, 120],
                        "g": [0, 0],
                        "i": [0, 0],
                        "NoFilter": [6, 120],
                    },
                    "Tarot_Chili": {
                        "r": [15, 120],
                        "g": [0, 0],
                        "i": [0, 0],
                        "NoFilter": [6, 120],
                    },
                    "Tarot_Reunion": {"NoFilter": [12, 120]},
                }
            else:
                sequence = {
                    "Tarot_Calern": {
                        "r": [8, 120],
                        "g": [0, 0],
                        "i": [8, 120],
                        "NoFilter": [4, 120],
                    },
                    "Tarot_Chili": {
                        "r": [8, 120],
                        "g": [0, 0],
                        "i": [8, 120],
                        "NoFilter": [4, 120],
                    },
                    "Tarot_Reunion": {"NoFilter": [8, 120]},
                }
        elif 17.0 < last_detected_mag < 19.0:
            if phase_angle > 60:
                sequence = {
                    "Tarot_Calern": {
                        "r": [22, 120],
                        "g": [0, 0],
                        "i": [0, 0],
                        "NoFilter": [15, 120],
                    },
                    "Tarot_Chili": {
                        "r": [22, 120],
                        "g": [0, 0],
                        "i": [0, 0],
                        "NoFilter": [15, 120],
                    },
                    "Tarot_Reunion": {"NoFilter": [18, 120]},
                }
            else:
                sequence = {
                    "Tarot_Calern": {
                        "r": [8, 200],
                        "g": [0, 0],
                        "i": [8, 200],
                        "NoFilter": [6, 120],
                    },
                    "Tarot_Chili": {
                        "r": [8, 200],
                        "g": [0, 0],
                        "i": [8, 200],
                        "NoFilter": [6, 120],
                    },
                    "Tarot_Reunion": {"NoFilter": [12, 200]},
                }
        elif last_detected_mag >= 19.0:
            if phase_angle > 60:
                sequence = {
                    "Tarot_Calern": {
                        "r": [0, 0],
                        "g": [0, 0],
                        "i": [0, 0],
                        "NoFilter": [15, 200],
                    },
                    "Tarot_Chili": {
                        "r": [0, 0],
                        "g": [0, 0],
                        "i": [0, 0],
                        "NoFilter": [0, 0],
                    },
                    "Tarot_Reunion": {"NoFilter": [0, 0]},
                }
            else:
                sequence = {
                    "Tarot_Calern": {
                        "r": [12, 200],
                        "g": [0, 0],
                        "i": [12, 200],
                        "NoFilter": [12, 120],
                    },
                    "Tarot_Chili": {
                        "r": [12, 200],
                        "g": [0, 0],
                        "i": [0, 0],
                        "NoFilter": [12, 120],
                    },
                    "Tarot_Reunion": {"NoFilter": [18, 200]},
                }

        seq = sequence.get(request.payload["station_name"], None)
        if seq is None:
            raise ValueError("Default sequence not available for this telescope")

        observations = []
        for default_filter in seq:
            exp_count, exposure_time = seq[default_filter]
            observations.extend(
                [f"{exposure_time} {filters[default_filter]}"] * exp_count
            )

    else:
        for obs_filter in request.payload["observation_choices"]:
            observations.append(
                f"{request.payload['exposure_time']} {filters[obs_filter]}"
            )
        observations = sum([observations] * request.payload["exposure_counts"], [])

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
            observation_string += f'"{request.obj.id}" {request.obj.ra} {request.obj.dec} {ttline.isot} 0.004180983 0.00 {" ".join(obs)} {" ".join(obs_filler)}{request.payload["priority"]} {request.payload["station_name"]}\n\r'

        if ii != number_of_strings:
            total_time += sum(45 + int(o.split(" ")[0]) for o in obs)

    return observation_string


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
        f"{cfg['app.tarot_endpoint']}/manage/manage/login.php",
        data=data,
        auth=(altdata["browser_username"], altdata["browser_password"]),
    )

    if login_response.status_code == 200 and "hashuser" in login_response.text:
        hash_user = login_response.text.split("hashuser=")[1][:20]
        if hash_user is not None and len(hash_user) == 20:
            return hash_user

    transaction = FacilityTransaction(
        request=http.serialize_requests_request(login_response.request),
        response=http.serialize_requests_response(login_response),
        followup_request=request,
        initiator_id=request.last_modified_by_id,
    )
    session.add(transaction)
    raise ValueError(f"Error trying to login to TAROT")


class TAROTAPI(FollowUpAPI):
    """SkyPortal interface to the TAROT"""

    @staticmethod
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

        if cfg["app.tarot_endpoint"] is None:
            raise ValueError("TAROT endpoint not configured")

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError("Missing allocation information.")

        hash_user = login_to_tarot(request, session, altdata)

        observation_string = create_observation_string(request)

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
            f"{cfg['app.tarot_endpoint']}/manage/manage/depot/depot-defaultshort.res.php?hashuser={hash_user}&idreq={altdata['request_id']}",
            data=payload,
            auth=(altdata["browser_username"], altdata["browser_password"]),
        )

        if "New Scene Inserted" not in response.text:
            error_response = f"rejected: status code = {response.status_code}. "
            if response.status_code == 200:
                error_response += "Scene not Inserted" + (
                    " - Hashuser not valid" if "secu_erreur" in response.text else ""
                )
            request.status = error_response
        else:
            request.status = "submitted: please retrieve status"

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

        if cfg["app.tarot_endpoint"] is None:
            raise ValueError("TAROT endpoint not configured")

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError("Missing allocation information.")

        insert_scene_ids = re.findall(
            r"insert_id\s*=\s*(\d+)",
            request.transactions[-1].response["content"],
        )

        response = requests.get(
            f"{cfg['app.tarot_endpoint']}/rejected{station_dict[request.payload['station_name']]['url_to_request']}.txt",
            auth=(altdata["browser_username"], altdata["browser_password"]),
        )

        if response.status_code != 200:
            raise ValueError("Error trying to get the status of the request")

        # If request exposure_count * nb_filter > 6, multiple scenes are created
        # But we only check the status of the first scene
        scene_id = insert_scene_ids[0]
        manager_scene_id = f"{str(scene_id)[0]}_{str(scene_id)[1:]}"
        pattern = (
            rf"\b\d*{re.escape(manager_scene_id)}\d*\b.*?{request.obj.id}.*?\((\d+)\)"
        )
        match = re.search(pattern, response.text)

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

        new_request_status = None
        nb_observation = None
        if (
            match is not None
            and match.group(1) is not None
            and status_dict.get(match.group(1), "rejected: not planified")
            not in request.status
        ):
            new_request_status = status_dict.get(
                match.group(1), "rejected: not planified"
            )

        if "rejected" not in request.status:
            # check if the scene has been observed
            station_endpoint = cfg[
                f"app.{station_dict[request.payload['station_name']]['endpoint']}"
            ]
            response = requests.get(f"{station_endpoint}/klotz/")

            if response.status_code != 200:
                raise ValueError("Error trying to get the observation log")

            scene_id = insert_scene_ids[0]
            manager_scene_id = f"{str(scene_id)[0]}_{str(scene_id)[1:]}"
            if manager_scene_id in response.text:
                nb_observation = response.text.count(manager_scene_id)
                new_request_status = f"complete"

        if new_request_status is None:
            return

        request.status = new_request_status

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
            if "complete" in request.status and nb_observation:
                flow.push(
                    request.last_modified_by_id,
                    "baselayer/SHOW_NOTIFICATION",
                    payload={
                        "note": f"TAROT have been observed {nb_observation} times",
                        "type": "info",
                    },
                )
        except Exception as e:
            log(f"Failed to send notification: {str(e)}")

    @staticmethod
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
            if cfg["app.tarot_endpoint"] is None:
                raise ValueError("TAROT endpoint not configured")

            altdata = request.allocation.altdata
            if not altdata:
                raise ValueError("Missing allocation information.")

            hash_user = login_to_tarot(request, session, altdata)

            insert_scene_ids = re.findall(
                r"insert_id\s*=\s*(\d+)",
                request.transactions[-1].response["content"],
            )

            data = {"check[]": insert_scene_ids, "remove": "Remove Scenes"}

            response = requests.post(
                f"{cfg['app.tarot_endpoint']}/manage/manage/liste_scene.php?hashuser={hash_user}&idreq={altdata['request_id']}",
                data=data,
                auth=(altdata["browser_username"], altdata["browser_password"]),
            )

            if response.status_code != 200:
                is_error_on_delete = response.content
            else:
                for scene_id in insert_scene_ids:
                    if f"Scene '{scene_id}' removed" not in response.text:
                        is_error_on_delete = response.content
                        break

            request.status = (
                "deleted"
                if is_error_on_delete is None
                else f"rejected: deletion failed - {is_error_on_delete}"
            )

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

    form_json_schema = {
        "type": "object",
        "properties": {
            "station_name": {
                "type": "string",
                "enum": [
                    "Tarot_Calern",
                    "Tarot_Chili",
                    "Tarot_Reunion",
                ],
                "default": "Tarot_Calern",
            },
            "date": {
                "type": "string",
                "default": datetime.utcnow().isoformat(),
                "title": "Date (UT)",
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
                "default": 1,
            },
        },
        "required": [
            "station_name",
            "date",
            "exposure_time",
            "exposure_counts",
            "observation_choices",
        ],
        "dependencies": {
            "station_name": {
                "oneOf": [
                    {
                        "properties": {
                            "station_name": {
                                "enum": [
                                    "Tarot_Calern",
                                    "Tarot_Chili",
                                ],
                            },
                            "observation_choices": {
                                "type": "array",
                                "title": "Desired Observations",
                                "items": {
                                    "type": "string",
                                    "enum": ["g", "r", "i", "NoFilter"],
                                },
                                "uniqueItems": True,
                                "minItems": 1,
                            },
                        },
                    },
                    {
                        "properties": {
                            "station_name": {
                                "enum": ["Tarot_Reunion"],
                            },
                            "observation_choices": {
                                "type": "array",
                                "title": "Desired Observations",
                                "items": {
                                    "type": "string",
                                    "enum": ["NoFilter"],
                                },
                                "uniqueItems": True,
                                "minItems": 1,
                            },
                        },
                    },
                ],
            },
        },
    }

    form_json_schema_altdata = {
        "type": "object",
        "properties": {
            "request_id": {
                "type": "string",
                "title": "Request ID to add scene",
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

    ui_json_schema = {"observation_choices": {"ui:widget": "checkboxes"}}
