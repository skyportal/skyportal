import ast
import functools
import json
from datetime import datetime

import numpy as np
import requests
from astropy.time import Time, TimeDelta
from paramiko import AutoAddPolicy, SSHClient
from requests.auth import HTTPBasicAuth
from sqlalchemy.orm import scoped_session, sessionmaker
from tornado.ioloop import IOLoop

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ..utils import http
from ..utils.instrument_log import read_logs
from . import FollowUpAPI

env, cfg = load_env()

log = make_log("facility_apis/sedmv2")


def validate_request_to_sedmv2(request):
    """Validate FollowupRequest contents for SEDMv2 queue.

    Parameters
    ----------
    request: skyportal.models.FollowupRequest
        The request to send to SEDMv2.
    """

    for param in [
        "observation_choice",
        "exposure_time",
        "maximum_airmass",
        "minimum_lunar_distance",
        "priority",
        "start_date",
        "end_date",
        "observation_type",
        "too",
    ]:
        if param not in request.payload:
            raise ValueError(f"Parameter {param} required.")

    if request.payload["observation_choice"] not in ["IFU", "g", "r", "i", "z"]:
        raise ValueError(
            f"Filter configuration {request.payload['observation_choice']} unknown."
        )

    if request.payload["observation_type"] not in ["transient", "variable"]:
        raise ValueError("observation_type must be either transient or variable")

    if request.payload["exposure_time"] < 0:
        raise ValueError("exposure_time must be positive.")

    if request.payload["maximum_airmass"] < 1:
        raise ValueError("maximum_airmass must be at least 1.")

    if (
        request.payload["minimum_lunar_distance"] < 0
        or request.payload["minimum_lunar_distance"] > 180
    ):
        raise ValueError("minimum lunar distance must be within 0-180.")

    if request.payload["priority"] < 0 or request.payload["priority"] > 5:
        raise ValueError("priority must be within 0-5.")

    if request.payload["too"] not in ["Y", "N"]:
        raise ValueError("too must be Y or N")

    if (request.payload["observation_type"] == "variable") and (
        request.payload["frame_exposure_time"] not in [1, 2, 3, 5, 10, 15, 20, 25, 30]
    ):
        raise ValueError("frame_exposure_time must be [1, 2, 3, 5, 10, 15, 20, 25, 30]")


class SEDMV2API(FollowUpAPI):
    """SkyPortal interface to the Spectral Energy Distribution machine (SEDMv2)."""

    @staticmethod
    def submit(request, session, **kwargs):
        """Submit a follow-up request to SEDMv2.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to submit.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransaction

        validate_request_to_sedmv2(request)

        if cfg["app.sedmv2_endpoint"] is not None:
            altdata = request.allocation.altdata

            if not altdata:
                raise ValueError("Missing allocation information.")

            payload = {
                "obj_id": request.obj_id,
                "allocation_id": request.allocation.id,
                "payload": request.payload,
            }

            r = requests.post(
                cfg["app.sedmv2_endpoint"],
                json=payload,
                headers={"Authorization": f"token {altdata['api_token']}"},
            )

            if r.status_code == 200:
                request.status = "submitted"
            else:
                request.status = f"rejected: {r.content}"

            transaction = FacilityTransaction(
                request=http.serialize_requests_request(r.request),
                response=http.serialize_requests_response(r),
                followup_request=request,
                initiator_id=request.last_modified_by_id,
            )
        else:
            request.status = "submitted"

            transaction = FacilityTransaction(
                request=None,
                response=None,
                followup_request=request,
                initiator_id=request.last_modified_by_id,
            )

        session.add(transaction)

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
        """Delete a follow-up request from SEDMv2 queue.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to delete from the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import DBSession, FacilityTransaction, FollowupRequest

        last_modified_by_id = request.last_modified_by_id
        obj_internal_key = request.obj.internal_key

        if cfg["app.sedmv2_endpoint"] is not None:
            altdata = request.allocation.altdata

            req = (
                DBSession()
                .query(FollowupRequest)
                .filter(FollowupRequest.id == request.id)
                .one()
            )

            altdata = request.allocation.altdata

            if not altdata:
                raise ValueError("Missing allocation information.")

            content = req.transactions[0].response["content"]
            content = json.loads(content)

            uid = content["data"]["id"]

            r = requests.delete(
                f"{cfg['app.sedmv2_endpoint']}/{uid}",
                headers={"Authorization": f"token {altdata['api_token']}"},
            )
            r.raise_for_status()
            request.status = "deleted"

            transaction = FacilityTransaction(
                request=http.serialize_requests_request(r.request),
                response=http.serialize_requests_response(r),
                followup_request=request,
                initiator_id=request.last_modified_by_id,
            )
        else:
            request.status = "deleted"

            transaction = FacilityTransaction(
                request=None,
                response=None,
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

    @staticmethod
    def update(request, session, **kwargs):
        """Update a request in the SEDMv2 queue.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The updated request.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransaction

        validate_request_to_sedmv2(request)

        if cfg["app.sedmv2_endpoint"] is not None:
            altdata = request.allocation.altdata

            if not altdata:
                raise ValueError("Missing allocation information.")

            payload = {
                "obj_id": request.obj_id,
                "allocation_id": request.allocation.id,
                "payload": request.payload,
            }

            r = requests.post(
                cfg["app.sedmv2_endpoint"],
                json=payload,
                headers={"Authorization": f"token {altdata['api_token']}"},
            )

            if r.status_code == 200:
                request.status = "submitted"
            else:
                request.status = f"rejected: {r.content}"

            transaction = FacilityTransaction(
                request=http.serialize_requests_request(r.request),
                response=http.serialize_requests_response(r),
                followup_request=request,
                initiator_id=request.last_modified_by_id,
            )
        else:
            request.status = "submitted"

            transaction = FacilityTransaction(
                request=None,
                response=None,
                followup_request=request,
                initiator_id=request.last_modified_by_id,
            )

        session.add(transaction)

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
    def retrieve_log(allocation, start_date, end_date):
        """Retrieve SEDMv2 logs.

        Parameters
        ----------
        allocation : skyportal.models.Allocation
            The allocation with queue information.
        start_date : datetime.datetime
            Minimum time for logs
        end_date : datetime.datetime
            Maximum time for logs
        """

        altdata = allocation.altdata
        if not altdata:
            raise ValueError("Missing allocation information.")

        request_start = Time(start_date, format="datetime")
        request_end = Time(end_date, format="datetime")

        fetch_logs = functools.partial(
            fetch_nightly_logs,
            allocation.instrument.id,
            altdata,
            request_start,
            request_end,
        )
        IOLoop.current().run_in_executor(None, fetch_logs)

    @staticmethod
    def update_status(allocation, session):
        """Update the status of SEDMv2 instruments."""

        instrument = allocation.instrument

        altdata = allocation.altdata

        if altdata.get("ssh_host") is None:
            log(f"Host not specified for instrument with ID {instrument.id}")
            return
        if altdata.get("ssh_port", 22) is None:
            log(f"Port not specified for instrument with ID {instrument.id}")
            return
        if altdata.get("ssh_username") is None:
            log(f"Username not specified for instrument with ID {instrument.id}")
            return
        if altdata.get("ssh_password") is None:
            log(f"Password not specified for instrument with ID {instrument.id}")
            return

        try:
            ssh = SSHClient()
            ssh.load_system_host_keys()
            ssh.set_missing_host_key_policy(AutoAddPolicy())
            ssh.connect(
                hostname=altdata["ssh_host"],
                port=altdata["ssh_port"],
                username=altdata["ssh_username"],
                password=altdata["ssh_password"],
            )
            stdin, stdout, stderr = ssh.exec_command(
                "cd /home/sedm/Queue/sedmv2; python read_config"
            )

            status = stdout.read().decode("utf-8")
            status = ast.literal_eval(status)
            status = {k: v for k, v in status.items() if v not in [None, "", {}, []]}

            instrument.status = status
            instrument.last_status_update = datetime.utcnow()
            session.commit()

        except Exception as e:
            log(f"Unable to commit status for instrument with ID {instrument.id}: {e}")
            session.rollback()
            raise e

    form_json_schema = {
        "type": "object",
        "properties": {
            "observation_choice": {
                "type": "string",
                "title": "Desired Observations",
                "enum": ["g", "r", "i", "z", "IFU"],
                "default": "IFU",
            },
            "exposure_time": {
                "title": "Exposure Time [s]",
                "type": "number",
                "default": 300.0,
            },
            "maximum_airmass": {
                "title": "Maximum Airmass (1-3)",
                "type": "number",
                "default": 2.0,
                "minimum": 1,
                "maximum": 3,
            },
            "minimum_lunar_distance": {
                "title": "Minimum Lunar Distance [deg] (0-180)",
                "type": "number",
                "default": 30.0,
                "minimum": 0,
                "maximum": 180,
            },
            "priority": {
                "type": "number",
                "default": 1.0,
                "minimum": 0.0,
                "maximum": 5.0,
                "title": "Priority",
            },
            "start_date": {
                "type": "string",
                "default": Time.now().isot,
                "title": "Start Date (UT)",
            },
            "end_date": {
                "type": "string",
                "title": "End Date (UT)",
                "default": (Time.now() + TimeDelta(7, format="jd")).isot,
            },
            "too": {
                "title": "Is this a Target of Opportunity observation?",
                "type": "string",
                "enum": [
                    "N",
                    "Y",
                ],
                "default": "N",
            },
            "observation_type": {
                "title": "What type of observation is this?",
                "type": "string",
                "enum": [
                    "transient",
                    "variable",
                ],
                "default": "transient",
            },
        },
        "required": [
            "observation_choice",
            "observation_type",
            "priority",
            "start_date",
            "end_date",
            "exposure_time",
            "maximum_airmass",
            "minimum_lunar_distance",
            "too",
        ],
        "dependencies": {
            "observation_type": {
                "oneOf": [
                    {
                        "properties": {
                            "observation_type": {
                                "enum": ["variable"],
                            },
                            "frame_exposure_time": {
                                "title": "Exposure time per frame (s)",
                                "enum": [1, 2, 3, 5, 10, 15, 20, 25, 30],
                                "default": 10,
                            },
                        },
                    },
                    {
                        "properties": {
                            "observation_type": {
                                "enum": ["transient"],
                            },
                        }
                    },
                ],
            },
        },
    }
    form_json_schema_altdata = {
        "type": "object",
        "properties": {
            "ssh_host": {
                "type": "string",
                "title": "SSH Host",
                "description": "Host to retrieve the instrument current status",
            },
            "ssh_port": {
                "type": "number",
                "title": "SSH Port",
                "description": "Port to retrieve the instrument current status",
            },
            "ssh_username": {
                "type": "string",
                "title": "SSH Username",
                "description": "Username to retrieve the instrument current status",
            },
            "ssh_password": {
                "type": "string",
                "title": "SSH Password",
                "description": "Password to retrieve the instrument current status",
            },
            "api_token": {
                "type": "string",
                "title": "API Token",
                "description": "API Token to submit/edit/delete observation requests",
            },
            "user": {
                "type": "string",
                "title": "User",
                "description": "User to retrieve the instrument logs",
            },
            "password": {
                "type": "string",
                "title": "Password",
                "description": "Password to retrieve the instrument logs",
            },
            "url": {
                "type": "string",
                "title": "URL",
                "description": "URL to retrieve the instrument logs",
            },
        },
    }

    ui_json_schema = {}
    alias_lookup = {
        "observation_choice": "Request",
        "start_date": "Start Date",
        "end_date": "End Date",
        "priority": "Priority",
        "observation_type": "Mode",
    }


def fetch_nightly_logs(instrument_id, altdata, request_start, request_end):
    """Fetch nightly logs.
    instrument_id : int
        ID of the instrument
    altdata: dict
        Contains SEDMv2 login for the user
    request_start : astropy.time.Time
        Start time for the request.
    request_end : astropy.time.Time
        End time for the request.
    """

    from ..models import DBSession, InstrumentLog

    Session = scoped_session(sessionmaker())
    if Session.registry.has():
        session = Session()
    else:
        session = Session(bind=DBSession.session_factory.kw["bind"])

    try:
        days = np.arange(np.floor(request_start.mjd), np.ceil(request_end.mjd) + 1)
        for day in days:
            day = Time(day, format="mjd").strftime("%Y%m%d")
            r = requests.get(
                f"{altdata['url']}/Archive/{day}/robo_test.{day}.log",
                auth=HTTPBasicAuth(altdata["user"], altdata["password"]),
            )
            logs = read_logs(r.text)

            if not logs["logs"]:
                log(f"Log for {day} unavailable for instrument with ID {instrument_id}")
                continue

            start_date = None
            end_date = None

            for log_dict in logs["logs"]:
                if start_date is None:
                    start_date = log_dict["mjd"]
                else:
                    start_date = np.min([start_date, log_dict["mjd"]])

                if end_date is None:
                    end_date = log_dict["mjd"]
                else:
                    end_date = np.max([end_date, log_dict["mjd"]])

            start_date = Time(start_date, format="mjd").datetime
            end_date = Time(end_date, format="mjd").datetime

            instrument_log = InstrumentLog(
                log=logs,
                start_date=start_date,
                end_date=end_date,
                instrument_id=instrument_id,
            )

            session.add(instrument_log)
            session.commit()

    except Exception as e:
        log(f"Unable to commit logs for instrument with ID {instrument_id}: {e}")
    finally:
        session.close()
        Session.remove()
