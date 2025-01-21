import json
import traceback
import urllib
from datetime import datetime, timedelta

import requests
from astropy.time import Time
from requests.auth import HTTPBasicAuth

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ..utils import http
from . import FollowUpAPI

env, cfg = load_env()


log = make_log("facility_apis/winter")

WINTER_URL = f"{cfg['app.winter.protocol']}://{cfg['app.winter.host']}"
if cfg["app.winter.port"] is not None and int(cfg["app.winter.port"]) not in [80, 443]:
    WINTER_URL += f":{cfg['app.winter.port']}"

WINTER_SUBMIT_TRIGGER = cfg.get("app.winter.submit_trigger", False)

FILTER_DEFAULTS = {
    "Y": {
        "n_dither": 8,
        "exposure_time": 960 / 8,  # 8 dithers for 960s total = 120s
    },
    "J": {
        "n_dither": 8,
        "exposure_time": 960 / 8,  # 8 dithers for 960s total = 120s
    },
    "Hs": {
        "n_dither": 15,
        "exposure_time": 900 / 15,  # 15 dithers for 900s total = 60s
    },
    "dark": {
        "n_dither": 5,
        "exposure_time": 600 / 5,  # 5 dithers for 600s total = 120s
    },
}


class WINTERRequest:
    """A dictionary structure for WINTER ToO requests."""

    def _build_payload(self, request):
        """Payload json for WINTER object queue requests.

        Parameters
        ----------

        request : skyportal.models.FollowupRequest
            The request to add to the WINTER TOO queue and the SkyPortal database.

        Returns
        ----------
        payload : json
            payload for requests.
        """

        # here an example of what a WINTER payload should look like
        filters = [request.payload["filter"]]
        target_priority = int(request.payload.get("priority", 50))
        t_exp = int(request.payload["exposure_time"]) * int(request.payload["n_dither"])
        # n_exp = int(request.payload.get("exposure_counts", 1))
        n_dither = int(request.payload["n_dither"])
        dither_distance = float(request.payload.get("dither_distance", 90))
        start_time_mjd = Time(request.payload["start_date"], format="iso").mjd
        end_time_mjd = Time(request.payload["end_date"], format="iso").mjd
        max_airmass = float(request.payload.get("maximum_airmass", 2.0))

        target = {
            "ra_deg": request.obj.ra,
            "dec_deg": request.obj.dec,
            "use_field_grid": False,
            "filters": filters,
            "target_priority": target_priority,
            "target_name": str(request.obj.id)[:30],  # 30 characters max
            "t_exp": t_exp,  # Total exposure time = exposure time (per dither) * n_dither
            "n_exp": 1,  # We force it to 1 for now
            "n_dither": n_dither,
            "dither_distance": dither_distance,
            "start_time_mjd": start_time_mjd,
            "end_time_mjd": end_time_mjd,
            "max_airmass": max_airmass,
        }

        return target

    def schedule_name(self, request):
        content = request.transactions[0].response["content"]
        content = json.loads(content)
        # the WINTERAPI POST response has a "msg" key,
        # that contains Schedule name is <schedule_name> if successful
        if "msg" in content:
            # it's in quote, so remove them and strip
            name = (
                str(content["msg"].split("Schedule name is")[1])
                .split(" ")[1]
                .split("'")[1]
                .strip()
            )
            return name
        else:
            raise ValueError(
                "Failed to delete request from WINTER, no schedule name found in POST response."
            )


class WINTERAPI(FollowUpAPI):
    """An interface to WINTER operations."""

    @staticmethod
    def prepare_payload(payload, existing_payload=None):
        """Prepare a payload for submission to WINTER.

        Parameters
        ----------
        payload : dict
            The payload to prepare for submission to WINTER.
        existing_payload : dict, optional
            The existing payload, if any, to update with the new payload.

        Returns
        -------
        dict
            The prepared payload.
        """
        # we know that WINTER does not implement updating requests
        # so, if this method is called with an existing_payload, we just return it
        # since it has already been prepared
        if existing_payload is not None:
            return existing_payload

        filter = payload["filter"]
        if filter is None:
            raise ValueError("Filter not set in payload.")
        if filter not in FILTER_DEFAULTS:
            raise ValueError(
                f"Filter {filter} not allowed, must be one of {list(FILTER_DEFAULTS.keys())}"
            )
        payload["n_dither"] = payload.pop(
            f"n_dither_{str(payload['filter']).lower()}",
            FILTER_DEFAULTS[filter]["n_dither"],
        )
        payload["exposure_time"] = payload.pop(
            f"exposure_time_{str(payload['filter']).lower()}",
            FILTER_DEFAULTS[filter]["exposure_time"],
        )

        payload["priority"] = payload.get("priority", 50)
        payload["dither_distance"] = payload.get("dither_distance", 90)
        payload["maximum_airmass"] = payload.get("maximum_airmass", 2.0)

        if "advanced" in payload:
            del payload["advanced"]

        return payload

    @staticmethod
    def delete(request, session, **kwargs):
        """Delete a follow-up request from WINTER queue.

        Parameters
        ----------
        request : skyportal.models.FollowupRequest
            The request to delete from the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransaction, FollowupRequest

        last_modified_by_id = request.last_modified_by_id
        obj_internal_key = request.obj.internal_key

        # this happens for failed submissions
        # just go ahead and delete
        if len(request.transactions) == 0:
            session.query(FollowupRequest).filter(
                FollowupRequest.id == request.id
            ).delete()
            session.commit()
        else:
            altdata = request.allocation.altdata
            if not altdata:
                raise ValueError("Missing allocation information.")

            req = WINTERRequest()
            name = req.schedule_name(request)

            url = urllib.parse.urljoin(WINTER_URL, "too/delete")
            r = requests.delete(
                url,
                params={
                    "program_name": altdata["program_name"],
                    "program_api_key": altdata["program_api_key"],
                    "schedule_name": name,
                },
                auth=HTTPBasicAuth(altdata["username"], altdata["password"]),
            )
            if r.status_code == 404:
                raise ValueError(
                    "Failed to delete request from WINTER, could not find a request with the given schedule name. Please wait a few seconds if you just submitted the request."
                )
            r.raise_for_status()
            request.status = "deleted"

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
                payload={"obj_key": obj_internal_key},
            )
        if kwargs.get("refresh_requests", False):
            flow = Flow()
            flow.push(
                last_modified_by_id,
                "skyportal/REFRESH_FOLLOWUP_REQUESTS",
            )

    @staticmethod
    def submit(request, session, **kwargs):
        """Submit a follow-up request to WINTER.

        Parameters
        ----------
        request : skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransaction

        req = WINTERRequest()

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError("Missing allocation information.")

        missing = [
            key
            for key in ["program_name", "program_api_key", "username", "password"]
            if key not in altdata
        ]
        if missing:
            raise ValueError(f"Missing allocation information: {', '.join(missing)}")

        payload = req._build_payload(request)
        url = urllib.parse.urljoin(WINTER_URL, "too/winter")

        r = requests.post(
            url,
            params={
                "program_name": altdata["program_name"],
                "program_api_key": altdata["program_api_key"],
                "submit_trigger": WINTER_SUBMIT_TRIGGER,
            },
            json=[payload],
            auth=HTTPBasicAuth(altdata["username"], altdata["password"]),
        )

        if r.status_code == 200:
            request.status = "submitted"
        else:
            request.status = f"rejected: {r.content}"
            log(
                f"Failed to submit WINTER request for {request.id} (obj {request.obj.id}): {r.content}"
            )
            try:
                flow = Flow()
                flow.push(
                    request.last_modified_by_id,
                    "baselayer/SHOW_NOTIFICATION",
                    payload={
                        "note": f"Failed to submit WINTER request: {r.content}",
                        "type": "error",
                    },
                )
            except Exception as e:
                log(f"Failed to send notification for failed WINTER request: {e}")

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

        try:
            notification_type = request.allocation.altdata.get(
                "notification_type", "none"
            )
            if notification_type == "slack":
                from ..utils.notifications import request_notify_by_slack

                request_notify_by_slack(
                    request,
                    session,
                    is_update=False,
                )
            elif notification_type == "email":
                from ..utils.notifications import request_notify_by_email

                request_notify_by_email(
                    request,
                    session,
                    is_update=False,
                )
        except Exception as e:
            traceback.print_exc()
            log(f"Error sending notification: {e}")

    form_json_schema = {
        "type": "object",
        "properties": {
            "start_date": {
                "type": "string",
                "default": str(datetime.utcnow()).replace("T", ""),
                "title": "Start Date (UT)",
            },
            "end_date": {
                "type": "string",
                "title": "End Date (UT)",
                "default": str(datetime.utcnow() + timedelta(days=7)).replace("T", ""),
            },
            "filter": {
                "type": "string",
                "title": "Filter",
                "enum": ["Y", "J", "Hs", "dark"],
            },
            # "exposure_counts": {
            #     "type": "integer",
            #     "title": "Number of Exposures",
            #     "default": 1,
            #     "minimum": 1,
            # },
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
                            "priority": {
                                "type": "integer",
                                "title": "Priority",
                                "default": 50,
                                "minimum": 0,
                            },
                            "dither_distance": {
                                "type": "number",
                                "title": "Dither Distance (arcsec)",
                                "default": 90,
                                "minimum": 0,
                            },
                            "maximum_airmass": {
                                "type": "number",
                                "title": "Maximum Airmass",
                                "default": 2.0,
                                "minimum": 1.0,
                                "maximum": 5.0,
                            },
                        }
                    },
                    {
                        "properties": {
                            "advanced": {"enum": [False]},
                        }
                    },
                ]
            },
            "filter": {
                "oneOf": [
                    {
                        "properties": {
                            "filter": {"enum": ["Y"]},
                            "exposure_time_y": {
                                "type": "integer",
                                "title": "Exposure Time (s)",
                                "minimum": 1,
                                "default": FILTER_DEFAULTS["Y"]["exposure_time"],
                            },
                            "n_dither_y": {
                                "type": "integer",
                                "title": "Number of Dithers",
                                "minimum": 1,
                                "default": FILTER_DEFAULTS["Y"]["n_dither"],
                            },
                        },
                        "required": ["exposure_time_y", "n_dither_y"],
                    },
                    {
                        "properties": {
                            "filter": {"enum": ["J"]},
                            "exposure_time_j": {
                                "type": "integer",
                                "title": "Exposure Time (s)",
                                "minimum": 1,
                                "default": FILTER_DEFAULTS["J"]["exposure_time"],
                            },
                            "n_dither_j": {
                                "type": "integer",
                                "title": "Number of Dithers",
                                "minimum": 1,
                                "default": FILTER_DEFAULTS["J"]["n_dither"],
                            },
                        },
                        "required": ["exposure_time_j", "n_dither_j"],
                    },
                    {
                        "properties": {
                            "filter": {"enum": ["Hs"]},
                            "exposure_time_hs": {
                                "type": "integer",
                                "title": "Exposure Time (s)",
                                "minimum": 1,
                                "default": FILTER_DEFAULTS["Hs"]["exposure_time"],
                            },
                            "n_dither_hs": {
                                "type": "integer",
                                "title": "Number of Dithers",
                                "minimum": 1,
                                "default": FILTER_DEFAULTS["Hs"]["n_dither"],
                            },
                        },
                        "required": ["exposure_time_hs", "n_dither_hs"],
                    },
                    {
                        "properties": {
                            "filter": {"enum": ["dark"]},
                            "exposure_time_dark": {
                                "type": "integer",
                                "title": "Exposure Time (s)",
                                "minimum": 1,
                                "default": FILTER_DEFAULTS["dark"]["exposure_time"],
                            },
                            "n_dither_dark": {
                                "type": "integer",
                                "title": "Number of Dithers",
                                "minimum": 1,
                                "default": FILTER_DEFAULTS["dark"]["n_dither"],
                            },
                        },
                        "required": ["exposure_time_dark", "n_dither_dark"],
                    },
                ]
            },
        },
        "required": [
            "start_date",
            "end_date",
            "filter",
            # "exposure_counts",
        ],
    }

    form_json_schema_altdata = {
        "type": "object",
        "properties": {
            "program_name": {
                "type": "string",
                "title": "Program Name",
            },
            "program_api_key": {
                "type": "string",
                "title": "Program API Key",
            },
            "username": {
                "type": "string",
                "title": "Username",
            },
            "password": {
                "type": "string",
                "title": "Password",
            },
            "notification_type": {
                "type": "string",
                "title": "Notification Type",
                "enum": ["none", "slack", "email"],
            },
        },
        "dependencies": {
            "notification_type": {
                "oneOf": [
                    {
                        "properties": {
                            "notification_type": {"enum": ["none"]},
                        },
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

    ui_json_schema = {
        "ui:order": [
            "start_date",
            "end_date",
            "filter",
            "*",  # wildcard for all the filter dependent fields
            "advanced",
            "priority",
            "dither_distance",
            "maximum_airmass",
        ],
    }
