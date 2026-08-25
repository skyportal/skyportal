import json
from datetime import timedelta

import aiohttp
import sqlalchemy as sa
from sqlalchemy.orm import selectinload

from baselayer.app.env import load_env
from baselayer.app.flow import Flow

from ..utils import http
from ..utils.naive_datetime import utcnow_naive
from . import FollowUpAPI

env, cfg = load_env()


def validate_request(request, filters):
    """Validate FollowupRequest contents for the NGPS queue.

    Parameters
    ----------
    request : skyportal.models.FollowupRequest
        The request to send to the instrument.
    filters : List[string]
        Filters allowed by instrument
    """

    for param in [
        "observation_choices",
        "exposure_time",
        "binspat",
        "binspect",
        "maximum_airmass",
        "priority",
        "start_date",
        "end_date",
    ]:
        if param not in request.payload:
            raise ValueError(f"Parameter {param} required.")

    for filt in request.payload["observation_choices"]:
        if filt not in filters:
            raise ValueError(f"Filter configuration {filt} unknown.")

    exposure_time = str(request.payload["exposure_time"]).strip()
    prefix, _, value = exposure_time.partition(" ")
    if prefix not in ["SNR", "SET"]:
        raise ValueError("exposure_time must be prefixed with 'SNR' or 'SET'.")
    try:
        if float(value) <= 0:
            raise ValueError
    except ValueError:
        raise ValueError(
            "exposure_time must be of the form 'SNR <value>' or 'SET <value>', "
            "with value a positive number."
        )

    if request.payload["binspat"] < 1:
        raise ValueError("binspat must be a positive integer.")

    if request.payload["binspect"] < 1:
        raise ValueError("binspect must be a positive integer.")

    if request.payload["maximum_airmass"] < 1:
        raise ValueError("maximum_airmass must be at least 1.")

    if request.payload["priority"] < 1 or request.payload["priority"] > 5:
        raise ValueError("priority must be within 1-5.")


def prepare_payload_ngps(payload, existing_payload=None):
    """Format a payload for NGPS.

    Parameters
    ----------
    payload: dict
        The payload to format.

    Returns
    -------
    formatted_payload: dict
        The formatted payload.
    """

    payload["exposure_time"] = payload.get(
        "exposure_time",
        "SNR 7.5" if existing_payload is None else existing_payload["exposure_time"],
    )
    payload["binspat"] = payload.get(
        "binspat",
        2 if existing_payload is None else existing_payload["binspat"],
    )
    payload["binspect"] = payload.get(
        "binspect",
        3 if existing_payload is None else existing_payload["binspect"],
    )
    payload["maximum_airmass"] = payload.get(
        "maximum_airmass",
        2.5 if existing_payload is None else existing_payload["maximum_airmass"],
    )

    if "advanced" in payload:
        del payload["advanced"]

    return payload


class NGPSAPI(FollowUpAPI):
    """SkyPortal interface for P200 NGPS follow-up"""

    @staticmethod
    async def submit(request, session, **kwargs):
        """Submit a follow-up request to an instrument.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to submit.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import Allocation, FacilityTransaction, FollowupRequest

        if (
            getattr(request, "allocation", None) is None
            and getattr(request, "allocation_id", None) is None
        ):
            raise ValueError("No allocation associated with this request.")
        elif (
            getattr(request, "allocation", None) is None
            and getattr(request, "allocation_id", None) is not None
        ):
            allocation = (
                await session.scalars(
                    Allocation.select(session.user_or_token).where(
                        Allocation.id == request.allocation_id
                    )
                )
            ).first()
            request.allocation = allocation

        # Reload with the lazy chains this method walks eager-loaded, since
        # async sessions raise on implicit lazy loads. Returns the same
        # identity-mapped object, so later request.status mutations persist.
        request = await session.scalar(
            sa.select(FollowupRequest)
            .where(FollowupRequest.id == request.id)
            .options(
                selectinload(FollowupRequest.allocation).selectinload(
                    Allocation.instrument
                ),
                selectinload(FollowupRequest.obj),
            )
        )

        validate_request(request, request.allocation.instrument.to_dict()["filters"])

        altdata = (
            request.allocation.altdata
            if getattr(request.allocation, "altdata", None) not in [None, {}]
            else None
        )

        transaction = None
        if altdata is not None:
            if altdata.get("notification_type") == "API":
                if altdata.get("endpoint") is None or altdata.get("api_token") is None:
                    raise ValueError(
                        "API endpoint and API token required for API notification type."
                    )
                payload = {
                    "obj_id": request.obj_id,
                    "allocation_id": request.allocation.id,
                    "payload": request.payload,
                }
                url = altdata["endpoint"]
                headers = {"Authorization": f"token {altdata['api_token']}"}

                async with aiohttp.ClientSession() as http_session:
                    async with http_session.post(
                        url, json=payload, headers=headers
                    ) as r:
                        content = await r.text()
                        status = r.status

                if status == 200:
                    request.status = "submitted"
                else:
                    request.status = f"rejected: {content}"

                transaction = FacilityTransaction(
                    request=http.serialize_aiohttp_request(
                        "POST", url, headers, payload
                    ),
                    response=await http.serialize_aiohttp_response(r, content),
                    followup_request=request,
                    initiator_id=request.last_modified_by_id,
                )

            elif altdata.get("notification_type") == "slack":
                from ..utils.notifications import request_notify_by_slack

                await request_notify_by_slack(request, session)

                request.status = "submitted"

                transaction = FacilityTransaction(
                    request=None,
                    response=None,
                    followup_request=request,
                    initiator_id=request.last_modified_by_id,
                )

            elif altdata.get("notification_type") == "email":
                from ..utils.notifications import request_notify_by_email

                await request_notify_by_email(request, session)

                request.status = "submitted"

                transaction = FacilityTransaction(
                    request=None,
                    response=None,
                    followup_request=request,
                    initiator_id=request.last_modified_by_id,
                )

            else:
                request.status = "rejected: no valid altdata configuration found."
        else:
            request.status = "submitted"

            transaction = FacilityTransaction(
                request=None,
                response=None,
                followup_request=request,
                initiator_id=request.last_modified_by_id,
            )

        if transaction is not None:
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
    async def delete(request, session, **kwargs):
        """Delete a follow-up request from the instrument queue.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to delete from the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import Allocation, FacilityTransaction, FollowupRequest

        # Reload with the lazy chains this method walks eager-loaded, since
        # async sessions raise on implicit lazy loads. Returns the same
        # identity-mapped object, so later request.status mutations persist.
        request = await session.scalar(
            sa.select(FollowupRequest)
            .where(FollowupRequest.id == request.id)
            .options(
                selectinload(FollowupRequest.allocation).selectinload(
                    Allocation.instrument
                ),
                selectinload(FollowupRequest.obj),
                selectinload(FollowupRequest.transactions),
            )
        )

        last_modified_by_id = request.last_modified_by_id
        obj_internal_key = request.obj.internal_key

        altdata = request.allocation.altdata
        has_valid_transaction = False
        if altdata:
            if (
                getattr(request, "transactions", None) is not None
                and getattr(request, "transactions", None) != []
                and getattr(request.transactions[0], "response", None) is not None
            ):
                content = request.transactions[0].response["content"]
                content = json.loads(content)

                uid = content["data"]["id"]

                url = f"{altdata['endpoint']}/{uid}"
                headers = {"Authorization": f"token {altdata['api_token']}"}

                async with aiohttp.ClientSession() as http_session:
                    async with http_session.delete(url, headers=headers) as r:
                        content = await r.text()
                        status = r.status

                if status >= 400:
                    raise ValueError(f"Error deleting request: status {status}")
                request.status = "deleted"

                transaction = FacilityTransaction(
                    request=http.serialize_aiohttp_request("DELETE", url, headers),
                    response=await http.serialize_aiohttp_response(r, content),
                    followup_request=request,
                    initiator_id=request.last_modified_by_id,
                )
                has_valid_transaction = True

        if not has_valid_transaction:
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
    async def update(request, session, **kwargs):
        """Update a request in the instrument queue.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The updated request.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import Allocation, FacilityTransaction, FollowupRequest

        # Reload with the lazy chains this method walks eager-loaded, since
        # async sessions raise on implicit lazy loads. Returns the same
        # identity-mapped object, so later request.status mutations persist.
        request = await session.scalar(
            sa.select(FollowupRequest)
            .where(FollowupRequest.id == request.id)
            .options(
                selectinload(FollowupRequest.allocation).selectinload(
                    Allocation.instrument
                ),
                selectinload(FollowupRequest.obj),
            )
        )

        validate_request(request, request.allocation.instrument.to_dict()["filters"])

        altdata = request.allocation.altdata

        if altdata:
            payload = {
                "obj_id": request.obj_id,
                "allocation_id": request.allocation.id,
                "payload": request.payload,
            }
            url = altdata["endpoint"]
            headers = {"Authorization": f"token {altdata['api_token']}"}

            async with aiohttp.ClientSession() as http_session:
                async with http_session.post(url, json=payload, headers=headers) as r:
                    content = await r.text()
                    status = r.status

            if status == 200:
                request.status = "submitted"
            else:
                request.status = f"rejected: {content}"

            transaction = FacilityTransaction(
                request=http.serialize_aiohttp_request("POST", url, headers, payload),
                response=await http.serialize_aiohttp_response(r, content),
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
    def prepare_payload(payload, existing_payload=None):
        return prepare_payload_ngps(payload, existing_payload)

    def custom_json_schema(instrument, user, **kwargs):
        form_json_schema = {
            "type": "object",
            "properties": {
                "observation_choices": {
                    "type": "array",
                    "title": "Desired Observations",
                    "items": {
                        "type": "string",
                        "enum": instrument.to_dict()["filters"],
                    },
                    "uniqueItems": True,
                    "minItems": 1,
                },
                "priority": {
                    "type": "number",
                    "default": 1.0,
                    "minimum": 1.0,
                    "maximum": 5.0,
                    "title": "Priority",
                },
                "start_date": {
                    "type": "string",
                    "format": "date",
                    "default": utcnow_naive().date().isoformat(),
                    "title": "Start Date (UT)",
                },
                "end_date": {
                    "type": "string",
                    "format": "date",
                    "title": "End Date (UT)",
                    "default": (utcnow_naive().date() + timedelta(days=7)).isoformat(),
                },
                "advanced": {
                    "type": "boolean",
                    "title": "Show Advanced Options",
                    "default": False,
                },
            },
            "dependencies": {
                "advanced": {
                    "oneOf": [
                        {
                            "properties": {
                                "advanced": {"enum": [True]},
                                "exposure_time": {
                                    "title": "Exposure Time",
                                    "type": "string",
                                    "default": "SNR 7.5",
                                    "pattern": r"^(SNR|SET) [0-9]*\.?[0-9]+$",
                                    "description": (
                                        "Either 'SNR <value>' to target a signal-to-noise "
                                        "ratio, or 'SET <value>' for a fixed exposure "
                                        "length in seconds."
                                    ),
                                },
                                "binspat": {
                                    "title": "Spatial Binning",
                                    "type": "integer",
                                    "default": 2,
                                    "minimum": 1,
                                },
                                "binspect": {
                                    "title": "Spectral Binning",
                                    "type": "integer",
                                    "default": 3,
                                    "minimum": 1,
                                },
                                "maximum_airmass": {
                                    "title": "Maximum Airmass (1-3)",
                                    "type": "number",
                                    "default": 2.5,
                                    "minimum": 1.0,
                                    "maximum": 3.0,
                                },
                            },
                            "required": [
                                "exposure_time",
                                "binspat",
                                "binspect",
                                "maximum_airmass",
                            ],
                        },
                        {
                            "properties": {
                                "advanced": {"enum": [False]},
                            }
                        },
                    ]
                },
            },
            "required": [
                "observation_choices",
                "priority",
                "start_date",
                "end_date",
            ],
        }

        return form_json_schema

    ui_json_schema = {"observation_choices": {"ui:widget": "checkboxes"}}

    alias_lookup = {
        "observation_choices": "Request",
        "start_date": "Start Date",
        "end_date": "End Date",
        "priority": "Priority",
        "exposure_time": "Exposure Time",
        "binspat": "Binspat",
        "binspect": "Binspect",
    }

    form_json_schema_altdata = {
        "type": "object",
        "properties": {
            "notification_type": {
                "type": "string",
                "title": "Notification Type",
                "enum": ["API", "slack", "email"],
            },
        },
        "required": ["notification_type"],
        "dependencies": {
            "notification_type": {
                "oneOf": [
                    {
                        "properties": {
                            "notification_type": {"enum": ["API"]},
                            "endpoint": {
                                "type": "string",
                                "title": "Endpoint",
                            },
                            "api_token": {
                                "type": "string",
                                "title": "API Token (Authorization header)",
                            },
                            "include_comments": {
                                "type": "boolean",
                                "title": "Include Comments",
                                "default": False,
                            },
                        },
                        "required": [
                            "endpoint",
                            "api_token",
                        ],
                    },
                    {
                        "properties": {
                            "notification_type": {"enum": ["slack"]},
                            "slack_workspace": {
                                "type": "string",
                                "title": "Slack Workspace",
                            },
                            "slack_channel": {
                                "type": "string",
                                "title": "Slack Channel",
                            },
                            "slack_token": {
                                "type": "string",
                                "title": "Slack Token",
                            },
                            "include_comments": {
                                "type": "boolean",
                                "title": "Include Comments",
                                "default": False,
                            },
                        },
                        "required": [
                            "slack_workspace",
                            "slack_channel",
                            "slack_token",
                        ],
                    },
                    {
                        "properties": {
                            "notification_type": {"enum": ["email"]},
                            "email": {
                                "type": "string",
                                "title": "Email",
                            },
                            "include_comments": {
                                "type": "boolean",
                                "title": "Include Comments",
                                "default": False,
                            },
                        },
                        "required": [
                            "email",
                        ],
                    },
                ]
            },
        },
    }
