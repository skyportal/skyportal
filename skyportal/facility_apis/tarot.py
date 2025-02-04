import re
import time
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


def validate_request_to_tarot(request):
    """Validate FollowupRequest contents for TAROT queue.

    Parameters
    ----------
    request: skyportal.models.FollowupRequest
        The request to send to TAROT.
    """

    for param in [
        "observation_choices",
        "exposure_time",
        "minimum_elevation",
        "station_name",
        "date",
    ]:
        if param not in request.payload:
            raise ValueError(f"Parameter {param} required.")

    if any(
        filt not in ["B", "V", "R", "I", "g", "r", "i", "z", "NoFilter"]
        for filt in request.payload["observation_choices"]
    ):
        raise ValueError(
            f"Filter configuration {request.payload['observation_choices']} unknown."
        )

    if request.payload["station_name"] not in [
        "Tarot_Calern",
        "Tarot_Chili",
        "Zadko_Australia",
        "VIRT_STT",
        "Tarot_Reunion",
    ]:
        raise ValueError(
            "observation_type must be Tarot_Calern, Tarot_Chili, Zadko_Australia, VIRT_STT, Tarot_Reunion"
        )

    if (
        request.payload["exposure_time"] < 0
        and not request.payload["exposure_time"] == -1
    ):
        raise ValueError("exposure_time must be positive or -1.")

    if request.payload["minimum_elevation"] < 10:
        raise ValueError("minimum_elevation must be at least 10 degrees.")

    filts = {
        "NoFilter": 0,
        "C": 1,
        "B": 2,
        "V": 3,
        "R": 4,
        "I": 5,
        "VN": 6,
        "g": 13,
        "r": 14,
        "i": 15,
        "z": 16,
        "U": 19,
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
        for filt in seq:
            exp_count, exposure_time = seq[filt]
            observations.extend([f"{exposure_time} {filts[filt]}"] * exp_count)

    else:
        for filt in request.payload["observation_choices"]:
            observations.append(f"{request.payload['exposure_time']} {filts[filt]}")
        observations = sum([observations] * request.payload["exposure_counts"], [])

    observation_strings = []
    number_of_strings, remainder = np.divmod(len(observations), 6)
    for ii in range(number_of_strings + 1):
        if ii == number_of_strings:
            obs_filler = ["0 0"] * (int(6 - remainder))
        else:
            obs_filler = []

        obs = observations[ii * 6 : (ii + 1) * 6]

        total_time = 0.0
        for o in obs:
            exposure_time, filt = o.split(" ")
            total_time = 40 + int(exposure_time) + total_time

        if ii == 0:
            ttdiff = 0 * u.s
        else:
            ttdiff = total_time * u.s

        ttline = tt + ttdiff

        observation_string = f'"{request.obj.id}" {request.obj.ra} {request.obj.dec} {ttline.isot} 0.004180983 0.00 {" ".join(obs)} {" ".join(obs_filler)} {request.payload["priority"]} {request.payload["station_name"]}'
        observation_strings.append(observation_string)

    return observation_strings


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


def check_request_on_tarot_manager(altdata, station_name, obj_id, insert_scene_ids):
    """Check the request status on the TAROT manager.

    Parameters
    ----------
    altdata: dict
        The altdata dictionary with credentials and request id.
    station_name: str
        The station name. (e.g., "Tarot_Calern", "Tarot_Chili", "Tarot_Reunion")
    obj_id: str
        The source id.
    insert_scene_ids: list
        The list of scene ids to check.

    Returns
    -------
    request_status: str
        The status of the request on the TAROT manager.
    """
    url_dict = {
        "Tarot_Calern": 1,
        "Tarot_Chili": 2,
        "Tarot_Reunion": 8,
    }
    response = requests.get(
        f"{cfg['app.tarot_endpoint']}/rejected{url_dict[station_name]}.txt",
        auth=(altdata["browser_username"], altdata["browser_password"]),
    )

    if response.status_code != 200:
        raise ValueError(
            f"Error trying to check request on TAROT manager: {response.status_code}"
        )

    status_dict = {
        "0": "Not planified",
        "1": "End observation before range",
        "4": "Over quota",
        "5": "Planified",
        "6": "Planified over",
    }
    request_status = None

    for scene_id in insert_scene_ids:
        manager_scene_id = f"{str(scene_id)[0]}_{str(scene_id)[1:]}"
        pattern = rf"\b\d*{re.escape(manager_scene_id)}\d*\b.*?{obj_id}.*?\((\d+)\)"
        match = re.search(pattern, response.text)
        if match is not None:
            scene_status_index = match.group(1)
            if scene_status_index != "5" and scene_status_index != "6":
                request_status = status_dict.get(scene_status_index, "Not planified")
        else:
            raise ValueError(
                f"Scene {manager_scene_id} for {obj_id} not found on TAROT manager"
            )

    return request_status


class TAROTAPI(FollowUpAPI):
    """SkyPortal interface to the TAROT"""

    @staticmethod
    def submit(request, session, **kwargs):
        """Submit a follow-up request to TAROT.

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

        observation_strings = validate_request_to_tarot(request)

        payload = {
            "type": "defaultshort",
            "mod": "new",
            "idreq": altdata["request_id"],
            "idscene": "0",
            "hashuser": hash_user,
            "check[type]": "IM",
            "data": observation_strings,
            "Submit": "Ok for quick depot",
        }

        response = requests.post(
            f"{cfg['app.tarot_endpoint']}/manage/manage/depot/depot-defaultshort.res.php?hashuser={hash_user}&idreq={altdata['request_id']}",
            data=payload,
            auth=(altdata["browser_username"], altdata["browser_password"]),
        )

        if response.status_code != 200 or "New Scene Inserted" not in response.text:
            request.status = (
                f"rejected: status code = {response.status_code}\n\r{response.text}"
            )
        else:
            request.status = "submitted"

        transaction = FacilityTransaction(
            request=http.serialize_requests_request(response.request),
            response=http.serialize_requests_response(response),
            followup_request=request,
            initiator_id=request.last_modified_by_id,
        )

        session.add(transaction)

        if request.status == "submitted":
            insert_scene_ids = re.findall(
                r"insert_id\s*=\s*(\d+)", response.content.decode()
            )
            time.sleep(3)
            request_status = check_request_on_tarot_manager(
                altdata,
                request.payload["station_name"],
                request.obj_id,
                insert_scene_ids,
            )
            if request_status is not None:
                request.status = f"rejected: {request_status}"

        if kwargs.get("refresh_source", False):
            flow = Flow()
            flow.push(
                "*",
                "skyportal/REFRESH_SOURCE",
                payload={"obj_key": request.obj.internal_key},
            )
        if kwargs.get("refresh_requests", False):
            flow = Flow()
            flow.push(
                request.last_modified_by_id,
                "skyportal/REFRESH_FOLLOWUP_REQUESTS",
            )

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
                else f"rejected: {is_error_on_delete}"
            )

            transaction = FacilityTransaction(
                request=http.serialize_requests_request(response.request),
                response=http.serialize_requests_response(response),
                followup_request=request,
                initiator_id=request.last_modified_by_id,
            )

            session.add(transaction)

        if kwargs.get("refresh_source", False):
            flow = Flow()
            flow.push(
                "*",
                "skyportal/REFRESH_SOURCE",
                payload={"obj_key": obj_internal_key},
            )
        if kwargs.get("refresh_requests", False):
            flow = Flow()
            flow.push(
                last_modified_by_id,
                "skyportal/REFRESH_FOLLOWUP_REQUESTS",
            )

    form_json_schema = {
        "type": "object",
        "properties": {
            "station_name": {
                "type": "string",
                "enum": [
                    "Tarot_Calern",
                    "Tarot_Chili",
                    "Zadko_Australia",
                    "VIRT_STT",
                    "Tarot_Reunion",
                ],
                "default": "Tarot_Calern",
            },
            "exposure_defaults": {
                "title": "Do you want to rely on defaults?",
                "type": "boolean",
                "default": True,
            },
            "date": {
                "type": "string",
                "format": "datetime",
                "default": datetime.utcnow().date().isoformat(),
                "title": "Date (UT)",
            },
            "tolerance": {
                "type": "number",
                "title": "Tolerance [min.]",
                "default": 60,
            },
            "minimum_elevation": {
                "title": "Minimum Elevation [deg.] (0-90)",
                "type": "number",
                "default": 30.0,
                "minimum": 10,
                "maximum": 90,
            },
            "minimum_lunar_distance": {
                "title": "Minimum Lunar Distance [deg.] (0-180)",
                "type": "number",
                "default": 30.0,
                "minimum": 0,
                "maximum": 180,
            },
            "priority": {
                "title": "Priority (-5 - 5)",
                "type": "number",
                "default": 0,
                "minimum": -5,
                "maximum": 5,
            },
        },
        "required": [
            "date",
            "tolerance",
            "minimum_elevation",
            "priority",
            "station_name",
        ],
        "dependencies": {
            "exposure_defaults": {
                "oneOf": [
                    {
                        "properties": {
                            "exposure_defaults": {
                                "enum": [False],
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
                        }
                    }
                ]
            },
            "station_name": {
                "oneOf": [
                    {
                        "properties": {
                            "station_name": {
                                "enum": [
                                    "Tarot_Calern",
                                    "Tarot_Chili",
                                    "Zadko_Australia",
                                ],
                            },
                            "observation_choices": {
                                "type": "array",
                                "title": "Desired Observations",
                                "items": {
                                    "type": "string",
                                    "enum": ["g", "r", "i", "z"],
                                },
                                "uniqueItems": True,
                                "minItems": 1,
                            },
                        },
                    },
                    {
                        "properties": {
                            "station_name": {
                                "enum": ["VIRT_STT"],
                            },
                            "observation_choices": {
                                "type": "array",
                                "title": "Desired Observations",
                                "items": {
                                    "type": "string",
                                    "enum": ["U", "B", "V", "R", "I"],
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
