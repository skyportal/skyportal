from datetime import datetime

import requests
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time, TimeDelta

from baselayer.app.env import load_env
from baselayer.app.flow import Flow

from ..utils import http
from . import FollowUpAPI

env, cfg = load_env()


def validate_request_to_colibri(request):
    """Validate FollowupRequest contents for COLIBRI queue.

    Parameters
    ----------
    request: skyportal.models.FollowupRequest
        The request to send to Colibri.
    """

    for param in [
        "observation_choice",
        "exposure_time",
        "maximum_airmass",
        "minimum_lunar_distance",
        "priority",
        "start_date",
        "end_date",
        "too",
    ]:
        if param not in request.payload:
            raise ValueError(f"Parameter {param} required.")

    if request.payload["observation_choice"] not in [
        "U",
        "g",
        "r",
        "i",
        "z",
        "B",
        "V",
        "R",
        "I",
    ]:
        raise ValueError(
            f"Filter configuration {request.payload['observation_choice']} unknown."
        )

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

    if type(request.payload["too"]) != bool:
        raise ValueError("too must be boolean")


class COLIBRIAPI(FollowUpAPI):
    """An interface to COLIBRI operations."""

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request, session, **kwargs):
        """Submit a follow-up request to COLIBRI.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransaction

        validate_request_to_colibri(request)
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
        """Delete a follow-up request from Colibri queue.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to delete from the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransaction

        last_modified_by_id = request.last_modified_by_id
        obj_internal_key = request.obj.internal_key

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
        """Update a follow-up request to COLIBRI.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransaction

        validate_request_to_colibri(request)
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

    form_json_schema = {
        "type": "object",
        "properties": {
            "observation_choice": {
                "type": "string",
                "title": "Desired Observations",
                "enum": ["U", "g", "r", "i", "z", "B", "V", "R", "I"],
                "default": "r",
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
                "minimum": 1,
                "maximum": 5,
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
                "type": "boolean",
                "default": False,
            },
        },
        "required": [
            "observation_choice",
            "priority",
            "start_date",
            "end_date",
            "exposure_time",
            "maximum_airmass",
            "minimum_lunar_distance",
            "too",
        ],
    }

    ui_json_schema = {}
    alias_lookup = {
        "observation_choice": "Request",
        "start_date": "Start Date",
        "end_date": "End Date",
        "priority": "Priority",
        "observation_type": "Mode",
    }
