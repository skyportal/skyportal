import json
import re

import aiohttp
import astropy.units as u
import sqlalchemy as sa
from astropy.coordinates import Angle
from sqlalchemy.orm import selectinload

from baselayer.app.env import load_env
from baselayer.log import make_log

from ..utils import http
from . import FollowUpAPI
from .interface import push_followup_refresh

env, cfg = load_env()

log = make_log("facility_apis/atca")

# Allowed central frequency range of each CABB IF (MHz) and the default pair.
BANDS = {
    "16cm": {"range": (1729, 2300), "freq1": 2100, "freq2": 2100},
    "4cm": {"range": (4928, 10928), "freq1": 5500, "freq2": 9000},
    "15mm": {"range": (16000, 24000), "freq1": 17000, "freq2": 19000},
    "7mm": {"range": (30000, 50000), "freq1": 33000, "freq2": 35000},
}

# CABB schedules cap source names at 10 characters.
MAX_SOURCE_NAME_LENGTH = 10


def hours_to_hms(hours):
    seconds = int(round(float(hours) * 3600))
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def source_name(request):
    """Name the target in the schedule: the requested name, else the tail of the obj ID."""
    name = request.payload.get("source_name")
    if name:
        name = str(name).strip()
        if len(name) > MAX_SOURCE_NAME_LENGTH:
            raise ValueError(
                f"source_name must be at most {MAX_SOURCE_NAME_LENGTH} characters."
            )
        return name
    return re.sub(r"[^A-Za-z0-9]", "", request.obj.id)[-MAX_SOURCE_NAME_LENGTH:]


def validate_request(request):
    payload = request.payload
    for param in ["bands", "exposure_time", "maximum_duration", "minimum_duration"]:
        if param not in payload:
            raise ValueError(f"Parameter {param} required.")

    if not payload["bands"]:
        raise ValueError("At least one band is required.")
    for band in payload["bands"]:
        if band not in BANDS:
            raise ValueError(f"Band {band} unknown.")
        low, high = BANDS[band]["range"]
        for key in ["freq1", "freq2"]:
            freq = payload.get(f"{key}_{band}", BANDS[band][key])
            if not low <= freq <= high:
                raise ValueError(
                    f"{key} for {band} must be within {low}-{high} MHz, got {freq}."
                )

    if payload["exposure_time"] <= 0:
        raise ValueError("exposure_time must be positive.")
    if payload["minimum_duration"] <= 0:
        raise ValueError("minimum_duration must be positive.")
    if payload["minimum_duration"] > payload["maximum_duration"]:
        raise ValueError("minimum_duration cannot exceed maximum_duration.")
    if payload.get("maximum_lag") is not None and payload["maximum_lag"] <= 0:
        raise ValueError("maximum_lag must be positive.")


def build_request_dict(request):
    """The JSON request the rapid response service turns into a CABB schedule."""
    payload = request.payload
    request_dict = {
        "source": source_name(request),
        "rightAscension": Angle(request.obj.ra, unit=u.deg).to_string(
            unit=u.hourangle, sep=":", precision=2, pad=True
        ),
        "declination": Angle(request.obj.dec, unit=u.deg).to_string(
            unit=u.deg, sep=":", precision=1, pad=True
        ),
        "project": request.allocation.altdata["project"],
        "maxExposureLength": hours_to_hms(payload["maximum_duration"]),
        "minExposureLength": hours_to_hms(payload["minimum_duration"]),
    }
    exposure = hours_to_hms(payload["exposure_time"] / 60)
    for band in payload["bands"]:
        request_dict[band] = {
            "use": True,
            "exposureLength": exposure,
            "freq1": int(payload.get(f"freq1_{band}", BANDS[band]["freq1"])),
            "freq2": int(payload.get(f"freq2_{band}", BANDS[band]["freq2"])),
        }
    return request_dict


def build_form_data(altdata, request_dict, maximum_lag=None):
    """Form fields for the service, with booleans spelled as the reference client sends them."""
    data = {
        "authToken": altdata["auth_token"],
        "email": altdata["email"],
        "request": json.dumps(request_dict),
    }
    if maximum_lag is not None:
        data["maximumLag"] = str(maximum_lag)
    if altdata.get("test"):
        data["test"] = "True"
        data["noTimeLimit"] = str(bool(altdata.get("no_time_limit")))
        data["noScoreLimit"] = str(bool(altdata.get("no_score_limit")))
        if altdata.get("email_only"):
            data["emailOnly"] = altdata["email_only"]
        if altdata.get("no_email"):
            data["noEmail"] = "True"
    return data


def submission_status(response, http_status):
    """Map a rapid response service reply to a FollowupRequest status."""
    if not isinstance(response, dict):
        # The basic-auth layer answers a failed login with an HTML page.
        return f"rejected: no JSON reply from ATCA (HTTP {http_status}), check the HTTP credentials"
    if response.get("error"):
        return f"rejected: {response['error']}"
    if not (response.get("authenticationToken") or {}).get("verified"):
        return "rejected: ATCA did not verify the authentication token"
    if not response.get("success"):
        return "rejected: ATCA could not schedule the request"

    status = "submitted (test mode)" if response.get("testMode") else "submitted"
    observations = response.get("observations") or {}
    if observations.get("startDate"):
        status += f": scheduled {observations['startDate']} to {observations.get('endDate')} UT"
    return status


def scheduled_id(transactions):
    """The service ID of the most recent request ATCA accepted, if any."""
    for transaction in sorted(transactions, key=lambda t: t.created_at, reverse=True):
        try:
            content = json.loads((transaction.response or {}).get("content") or "")
        except (TypeError, ValueError):
            continue
        if isinstance(content, dict) and content.get("success") and content.get("id"):
            return content["id"]
    return None


async def post_to_atca(altdata, data):
    headers = {}
    if altdata.get("http_username"):
        headers["Authorization"] = aiohttp.encode_basic_auth(
            altdata["http_username"], altdata["http_password"]
        )
    url = cfg["app.atca_endpoint"]
    async with aiohttp.ClientSession() as http_session:
        async with http_session.post(url, data=data, headers=headers) as r:
            content = await r.text()
    try:
        response = json.loads(content)
    except ValueError:
        response = None
    # The token authorises overrides of other projects, so it is never stored.
    recorded = {**data, "authToken": "REDACTED"}
    transaction = {
        "request": http.serialize_aiohttp_request("POST", url, {}, recorded),
        "response": await http.serialize_aiohttp_response(r, content),
    }
    return response, r.status, transaction


class ATCAAPI(FollowUpAPI):
    """An interface to the ATCA rapid response (NAPA over-ride) service."""

    @staticmethod
    def validate_altdata(altdata, **kwargs):
        if not isinstance(altdata, dict):
            raise ValueError("Invalid altdata format")
        for key in ["auth_token", "email", "project"]:
            if not str(altdata.get(key) or "").strip():
                raise ValueError(f"{key} is required")
        if bool(altdata.get("http_username")) != bool(altdata.get("http_password")):
            raise ValueError("http_username and http_password must be given together")
        return altdata

    @staticmethod
    async def submit(request, session, **kwargs):
        """Submit a follow-up request to the ATCA rapid response service.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransaction, FollowupRequest

        request = await session.scalar(
            sa.select(FollowupRequest)
            .where(FollowupRequest.id == request.id)
            .options(
                selectinload(FollowupRequest.allocation),
                selectinload(FollowupRequest.obj),
            )
        )

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError("Missing allocation information.")

        validate_request(request)
        data = build_form_data(
            altdata, build_request_dict(request), request.payload.get("maximum_lag")
        )
        response, http_status, transaction = await post_to_atca(altdata, data)
        request.status = submission_status(response, http_status)
        if request.status.startswith("rejected"):
            log(f"ATCA rejected follow-up request {request.id}: {request.status}")

        session.add(
            FacilityTransaction(
                **transaction,
                followup_request=request,
                initiator_id=request.last_modified_by_id,
            )
        )

        push_followup_refresh(
            request.obj.internal_key, request.last_modified_by_id, **kwargs
        )

    @staticmethod
    async def delete(request, session, **kwargs):
        """Cancel a request scheduled by ATCA, or drop one it never accepted.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to delete from the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransaction, FollowupRequest

        request = await session.scalar(
            sa.select(FollowupRequest)
            .where(FollowupRequest.id == request.id)
            .options(
                selectinload(FollowupRequest.allocation),
                selectinload(FollowupRequest.obj),
                selectinload(FollowupRequest.transactions),
            )
        )

        last_modified_by_id = request.last_modified_by_id
        obj_internal_key = request.obj.internal_key

        cancel_id = scheduled_id(request.transactions)
        if cancel_id is None:
            await session.execute(
                sa.delete(FollowupRequest).where(FollowupRequest.id == request.id)
            )
            await session.commit()
        else:
            altdata = request.allocation.altdata
            if not altdata:
                raise ValueError("Missing allocation information.")

            data = build_form_data(
                altdata, {"cancel": cancel_id, "project": altdata["project"]}
            )
            response, http_status, transaction = await post_to_atca(altdata, data)
            if not isinstance(response, dict) or response.get("error"):
                error = (response or {}).get("error") or f"HTTP {http_status}"
                raise ValueError(f"ATCA could not cancel request {cancel_id}: {error}")

            request.status = "deleted"
            session.add(
                FacilityTransaction(
                    **transaction,
                    followup_request=request,
                    initiator_id=request.last_modified_by_id,
                )
            )

        push_followup_refresh(obj_internal_key, last_modified_by_id, **kwargs)

    form_json_schema = {
        "type": "object",
        "properties": {
            "bands": {
                "type": "array",
                "title": "Bands",
                "items": {"type": "string", "enum": list(BANDS)},
                "uniqueItems": True,
                "minItems": 1,
                "default": ["4cm"],
            },
            "exposure_time": {
                "type": "number",
                "title": "Time on source per band per cycle [min]",
                "default": 30.0,
                "minimum": 1.0,
            },
            "maximum_duration": {
                "type": "number",
                "title": "Maximum duration [hr]",
                "description": "ATCA cycles through the bands until this much time is used or the source sets.",
                "default": 12.0,
                "minimum": 0.1,
            },
            "minimum_duration": {
                "type": "number",
                "title": "Minimum useful duration [hr]",
                "description": "ATCA only schedules the request into a slot at least this long.",
                "default": 3.0,
                "minimum": 0.1,
            },
            "maximum_lag": {
                "type": "number",
                "title": "Latest start [hr from now] (optional)",
                "description": "Defaults to the service's 100 hour search window.",
                "minimum": 0.1,
            },
            "source_name": {
                "type": "string",
                "title": "Source name in the schedule (optional)",
                "description": f"At most {MAX_SOURCE_NAME_LENGTH} characters; defaults to the last {MAX_SOURCE_NAME_LENGTH} alphanumeric characters of the source ID.",
                "maxLength": MAX_SOURCE_NAME_LENGTH,
            },
            "advanced": {
                "type": "boolean",
                "title": "Choose frequencies",
                "default": False,
            },
        },
        "dependencies": {
            "advanced": {
                "oneOf": [
                    {
                        "properties": {
                            "advanced": {"enum": [True]},
                            **{
                                f"{key}_{band}": {
                                    "type": "integer",
                                    "title": f"{band} IF{key[-1]} [MHz]",
                                    "default": spec[key],
                                    "minimum": spec["range"][0],
                                    "maximum": spec["range"][1],
                                }
                                for band, spec in BANDS.items()
                                for key in ["freq1", "freq2"]
                            },
                        },
                    },
                    {"properties": {"advanced": {"enum": [False]}}},
                ]
            }
        },
        "required": ["bands", "exposure_time", "maximum_duration", "minimum_duration"],
    }

    form_json_schema_altdata = {
        "type": "object",
        "properties": {
            "auth_token": {
                "type": "string",
                "title": "Authentication token",
                "description": "The JWT issued by ATCA staff for this NAPA project.",
            },
            "email": {
                "type": "string",
                "title": "Email",
                "description": "An investigator email listed on the OPAL proposal.",
            },
            "project": {
                "type": "string",
                "title": "Project code",
                "description": "The ATCA project code, e.g. C3456.",
            },
            "http_username": {
                "type": "string",
                "title": "HTTP username",
                "description": "Web service credentials from ATCA staff, needed outside the CSIRO network.",
            },
            "http_password": {"type": "string", "title": "HTTP password"},
            "test": {
                "type": "boolean",
                "title": "Test mode",
                "description": "ATCA evaluates requests but allocates no telescope time.",
                "default": False,
            },
            "email_only": {
                "type": "string",
                "title": "Send all emails only to (test mode)",
            },
            "no_email": {"type": "boolean", "title": "Send no emails (test mode)"},
            "no_score_limit": {
                "type": "boolean",
                "title": "Ignore the TAC score limit (test mode)",
            },
            "no_time_limit": {
                "type": "boolean",
                "title": "Ignore the project's remaining time (test mode)",
            },
        },
        "required": ["auth_token", "email", "project"],
    }

    ui_json_schema = {"bands": {"ui:widget": "checkboxes"}}

    alias_lookup = {
        "bands": "Bands",
        "exposure_time": "Time per Band [min]",
        "maximum_duration": "Maximum Duration [hr]",
        "minimum_duration": "Minimum Duration [hr]",
        "maximum_lag": "Latest Start [hr]",
        "source_name": "Source Name",
    }
