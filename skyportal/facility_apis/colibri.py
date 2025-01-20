from datetime import datetime

import requests
from astropy import units as u
from astropy.coordinates import SkyCoord
from requests.auth import HTTPBasicAuth

from baselayer.app.env import load_env
from baselayer.app.flow import Flow

from ..utils import http
from . import FollowUpAPI

env, cfg = load_env()


if cfg.get("app.colibri.port") is None:
    COLIBRI_URL = f"{cfg['app.colibri.protocol']}://{cfg['app.colibri.host']}"
else:
    COLIBRI_URL = f"{cfg['app.colibri.protocol']}://{cfg['app.colibri.host']}:{cfg['app.colibri.port']}"


class COLIBRIRequest:
    """A dictionary structure for COLIBRI ToO requests."""

    def _build_payload(self, request):
        """Payload json for COLIBRI queue requests.

        Parameters
        ----------

        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        Returns
        ----------
        payload: json
            payload for requests.
        """

        for filt in request.payload["observation_choices"]:
            if filt not in ["U", "g", "r", "i", "z", "B", "V", "R", "I"]:
                raise ValueError(f"Improper observation_choice {filt}")

        c = SkyCoord(ra=request.obj.ra * u.degree, dec=request.obj.dec * u.degree)
        ra_str = c.ra.to_string(unit="hour", sep=":", precision=2, pad=True)
        dec_str = c.dec.to_string(unit="degree", sep=":", precision=2, pad=True)

        # The target of the observation
        target = {
            "name": request.obj.id,
            "alpha": ra_str,
            "delta": dec_str,
            "equinox": "2000",
            "uncertainty": "1.0as",
            "priority": int(request.payload["priority"]),
            "filters": "".join(request.payload["observation_choices"]),
            "type": "transient",
            "projectidentifier": str(request.allocation.id),
            "identifier": str(request.id),
            "enabled": "true",
            "eventtimestamp": request.payload["start_date"],
            "alerttimestamp": request.payload["start_date"],
        }

        return target


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

        req = COLIBRIRequest()
        requestgroup = req._build_payload(request)

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError("Missing allocation information.")

        requestpath = f"{COLIBRI_URL}/cgi-bin/internal/process_colibri_ztf_request.py"

        r = requests.post(
            requestpath,
            auth=HTTPBasicAuth(altdata["username"], altdata["password"]),
            json=requestgroup,
        )
        r.raise_for_status()

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
        from ..models import FollowupRequest

        last_modified_by_id = request.last_modified_by_id
        obj_internal_key = request.obj.internal_key

        if len(request.transactions) == 0:
            session.query(FollowupRequest).filter(
                FollowupRequest.id == request.id
            ).delete()
            session.commit()
        else:
            raise NotImplementedError(
                "Can't delete requests already submitted successfully to COLIBRI."
            )

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
            "observation_choices": {
                "type": "array",
                "title": "Desired Observations",
                "items": {
                    "type": "string",
                    "enum": ["U", "g", "r", "i", "z", "B", "V", "R", "I"],
                },
                "uniqueItems": True,
                "minItems": 1,
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
                "default": datetime.utcnow().isoformat(),
                "title": "Start Date (UT)",
            },
        },
        "required": [
            "observation_choices",
            "priority",
            "start_date",
        ],
    }

    form_json_schema_altdata = {
        "type": "object",
        "properties": {
            "username": {
                "type": "string",
                "title": "Username",
            },
            "password": {
                "type": "string",
                "title": "Password",
            },
        },
    }

    ui_json_schema = {"observation_choices": {"ui:widget": "checkboxes"}}

    alias_lookup = {
        "observation_choices": "Request",
    }
