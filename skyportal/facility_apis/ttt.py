import base64
import json
import os
import urllib
from datetime import datetime, timedelta
from urllib.parse import urlparse

import astropy.units as u
import requests
import sqlalchemy as sa
from astropy.coordinates import SkyCoord
from astropy.time import Time, TimeDelta

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ..utils import http
from . import FollowUpAPI

env, cfg = load_env()

log = make_log("facility_apis/ttt")


def validate_request_to_ttt(request, proposal_id):
    """Validate FollowupRequest contents for TTT queue.

    Parameters
    ----------
    request: skyportal.models.FollowupRequest
        The request to send to TTT.
    """

    for param in [
        "observation_choices",
        "snr",
        "start_date",
        "end_date",
    ]:
        if param not in request.payload:
            raise ValueError(f"Parameter {param} required.")

    if request.payload["station_name"] not in ["TTT-80", "TTT-200"]:
        raise ValueError("station_name must be TTT-80 or TTT-200")

    if request.payload["station_name"] == "TTT-80":
        camera_model = "QHY411M"
    elif request.payload["station_name"] == "TTT-200":
        camera_model = "QHY600M Pro"

    if any(
        filt not in ["sdssu", "sdssg", "sdssr", "sdssi", "sdssz"]
        for filt in request.payload["observation_choices"]
    ):
        raise ValueError(
            f"Filter configuration {request.payload['observation_choices']} unknown."
        )

    if request.payload["snr"] < 0:
        raise ValueError("snr must be positive.")

    tstart = Time(request.payload["start_date"] + "T00:00:00", format="isot")
    tend = Time(request.payload["end_date"] + "T00:00:00", format="isot")
    expired = tend + TimeDelta(1 * u.day)

    requestgroup = {
        "proposal": proposal_id,
        "target_name": request.obj.id,
        "ra": request.obj.ra,
        "dec": request.obj.dec,
        "moving_target": "false",
        "telescope_model": request.payload["station_name"],
        "camera_model": camera_model,
        "n_rep_block": request.payload["exposure_counts"],
        "t_rep_block": None,
        "min_cadence": 0,  # FIXME
        "mag": 19,  # FIXME
        "min_time": tstart.iso,
        "max_time": tend.iso,
        "full_interval": "false",
        "locked_dtos": 0,
        "estimated_dtos": 0,
        "locked_dtos_virtual": 0,
        "lines": [
            {"filter": filt, "snr": str(request.payload["snr"])}
            for filt in request.payload["observation_choices"]
        ],
    }

    return requestgroup


class TTTAPI(FollowUpAPI):
    """SkyPortal interface to the Two-meter Twin Telescope"""

    @staticmethod
    def submit(request, session, **kwargs):
        """Submit a follow-up request to TTT.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to submit.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransaction

        if cfg["app.ttt_endpoint"] is not None:
            altdata = request.allocation.altdata

            if not altdata:
                raise ValueError("Missing allocation information.")

            payload = validate_request_to_ttt(request, altdata.proposal_id)

            headers = {
                "Authorization": f"Bearer {altdata.token}",
            }
            url = f"{cfg['app.trt_endpoint']}/observing-runs/"

            r = requests.request(
                "POST",
                url,
                json=payload,
                headers=headers,
            )

            if r.status_code == 200:
                request.status = "submitted"
            else:
                request.status = f"rejected: {r.text}"

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
                    request.last_modified_by_id,
                    "skyportal/REFRESH_FOLLOWUP_REQUESTS",
                )
            if str(request.status) != "submitted":
                flow.push(
                    request.last_modified_by_id,
                    "baselayer/SHOW_NOTIFICATION",
                    payload={
                        "note": f'Failed to submit TRT request: "{request.status}"',
                        "type": "error",
                    },
                )
        except Exception as e:
            log(f"Failed to send notification: {e}")

    @staticmethod
    def get(request, session, **kwargs):
        """Get a follow-up request from TTT queue (all instruments).

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to update from the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransaction, FollowupRequest
        from ..utils.asynchronous import run_async

        if cfg["app.ttt_endpoint"] is not None:
            altdata = request.allocation.altdata

            if not altdata:
                raise ValueError("Missing allocation information.")

            req = session.scalar(
                sa.select(FollowupRequest).where(FollowupRequest.id == request.id)
            )

            content = str(req.transactions[-1].response["content"])

            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                raise ValueError(
                    f"Unable to parse submission response from TRT: {content}"
                )

            uid = content[0]
            if not uid:
                raise ValueError("Unable to find observation ID in response from TTT.")

            headers = {
                "Authorization": f"Bearer {altdata.token}",
            }
            url = f"{cfg['app.trt_endpoint']}/observing-runs/{uid}"

            r = requests.request("GET", url, headers=headers)

            r.raise_for_status()

            if r.status_code == 200:
                try:
                    data = r.json()
                except json.JSONDecodeError:
                    raise ValueError(
                        f"Unable to parse retrieval response from TTT: {r.content}"
                    )

                request.status = data["status"]
            else:
                request.status = f"failed to retrieve: {r.content.decode()}"

        transaction = FacilityTransaction(
            request=http.serialize_requests_request(r.request),
            response=http.serialize_requests_response(r),
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
                    request.last_modified_by_id,
                    "skyportal/REFRESH_FOLLOWUP_REQUESTS",
                )
            if str(request.status) == "pending":
                flow.push(
                    request.last_modified_by_id,
                    "baselayer/SHOW_NOTIFICATION",
                    payload={
                        "note": "TTT request is still pending.",
                        "type": "warning",
                    },
                )
            elif str(request.status).startswith("complete"):
                flow.push(
                    request.last_modified_by_id,
                    "baselayer/SHOW_NOTIFICATION",
                    payload={
                        "note": "TTT request is complete, observations will be downloaded shortly.",
                        "type": "info",
                    },
                )
            else:
                flow.push(
                    request.last_modified_by_id,
                    "baselayer/SHOW_NOTIFICATION",
                    payload={
                        "note": f'Failed to retrieve TRT request: "{request.status}"',
                        "type": "error",
                    },
                )
        except Exception as e:
            log(f"Failed to send notification: {e}")

    @staticmethod
    def delete(request, session, **kwargs):
        """Delete a follow-up request from TTT queue.

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

        if cfg["app.ttt_endpoint"] is not None:
            altdata = request.allocation.altdata

            if not altdata:
                raise ValueError("Missing allocation information.")

            req = session.scalar(
                sa.select(FollowupRequest).where(FollowupRequest.id == request.id)
            )

            content = str(req.transactions[-1].response["content"])
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                raise ValueError(
                    f"Unable to parse submission response from TRT: {content}"
                )

            uid = content[0]
            if not uid:
                raise ValueError("Unable to find observation ID in response from TRT.")

            headers = {
                "Authorization": f"Bearer {altdata.token}",
            }
            url = f"{cfg['app.ttt_endpoint']}/observing-runs/{uid}"

            r = requests.request("DELETE", url, headers=headers)

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

    form_json_schema = {
        "type": "object",
        "properties": {
            "station_name": {
                "type": "string",
                "enum": ["TTT-80", "TTT-200"],
                "default": "TTT-80",
            },
            "snr": {
                "title": "SNR",
                "type": "number",
                "default": 5.0,
            },
            "exposure_counts": {
                "title": "Exposure Counts",
                "type": "number",
                "default": 1,
            },
            "start_date": {
                "type": "string",
                "format": "date",
                "default": datetime.utcnow().date().isoformat(),
                "title": "Start Date (UT)",
            },
            "end_date": {
                "type": "string",
                "format": "date",
                "title": "End Date (UT)",
                "default": (datetime.utcnow().date() + timedelta(days=7)).isoformat(),
            },
        },
        "required": [
            "start_date",
            "end_date",
            "snr",
            "station_name",
        ],
        "dependencies": {
            "station_name": {
                "oneOf": [
                    {
                        "properties": {
                            "station_name": {
                                "enum": ["TTT-80"],
                            },
                            "observation_choices": {
                                "type": "array",
                                "title": "Desired Observations",
                                "items": {
                                    "type": "string",
                                    "enum": ["sdssg", "sdssr", "sdssi"],
                                },
                                "uniqueItems": True,
                                "minItems": 1,
                            },
                        },
                    },
                    {
                        "properties": {
                            "station_name": {
                                "enum": ["TTT-200"],
                            },
                            "observation_choices": {
                                "type": "array",
                                "title": "Desired Observations",
                                "items": {
                                    "type": "string",
                                    "enum": [
                                        "sdssu",
                                        "sdssg",
                                        "sdssr",
                                        "sdssi",
                                        "sdssz",
                                    ],
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
            "token": {
                "type": "string",
                "title": "Token",
            },
            "proposal_id": {
                "type": "string",
                "title": "proposal_id",
            },
        },
    }

    ui_json_schema = {"observation_choices": {"ui:widget": "checkboxes"}}
