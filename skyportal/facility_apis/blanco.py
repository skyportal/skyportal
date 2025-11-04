import json
from datetime import datetime, timedelta

import requests

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ..utils import http
from . import FollowUpAPI

env, cfg = load_env()

requestpath = f"{cfg['app.lco_protocol']}://{cfg['app.lco_host']}:{cfg['app.lco_port']}/api/requestgroups/"

log = make_log("facility_apis/newfirm")


class BLANCO_NEWFIRM_Request:
    """A JSON structure for BLANCO NEWFIRM requests."""

    def __init__(self, request):
        """Initialize BLANCO NEWFIRM request.

        Parameters
        ----------

        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        """

        self.requestgroup = self._build_payload(request)

    def _build_payload(self, request):
        """Payload json for BLANCO NEWFIRM queue requests.

        Parameters
        ----------

        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.

        Returns
        ----------
        payload: json
            payload for requests.
        """

        # Constraints used for scheduling this observation
        constraints = {
            "max_airmass": request.payload["maximum_airmass"],
            "min_lunar_distance": request.payload["minimum_lunar_distance"],
        }

        # The target of the observation
        target = {
            "name": request.obj.id,
            "type": "ICRS",
            "ra": request.obj.ra,
            "dec": request.obj.dec,
            "proper_motion_ra": 0,
            "proper_motion_dec": 0,
            "parallax": 0,
            "epoch": 2000,
        }

        exp_time = request.payload["exposure_time"]
        sequence_repeats = int(request.payload["sequence_repeats"])
        coadds = int(request.payload["coadds"])

        configurations = []
        for filt in request.payload["observation_choices"]:
            configurations.append(
                {
                    "type": "EXPOSE",
                    "instrument_type": "BLANCO_NEWFIRM",
                    "extra_params": {
                        "dither_value": 80,
                        "dither_sequence": "5-point",
                        "detector_centering": "det_1",
                        "dither_sequence_random_offset": True,
                        "coadds": coadds,
                    },
                    "constraints": constraints,
                    "target": target,
                    "acquisition_config": {"mode": "MANUAL", "extra_params": {}},
                    "guiding_config": {
                        "mode": "ON",
                        "optional": True,
                        "extra_params": {},
                    },
                    "instrument_configs": [
                        {
                            "exposure_time": exp_time,
                            "exposure_count": 1,
                            "sequence_repeats": sequence_repeats,
                            "mode": "fowler1",
                            "extra_params": {
                                "offset_ra": 0,
                                "offset_dec": 0,
                                "defocus": 0,
                                "rotator_angle": 0,
                            },
                            "optical_elements": {"filter": f"{filt}"},
                        }
                    ],
                }
            )

        tstart = request.payload["start_date"]
        tend = request.payload["end_date"]

        windows = [{"start": tstart, "end": tend}]

        # The telescope class that should be used for this observation
        location = {"telescope_class": "4m0"}

        altdata = request.allocation.altdata

        # The full RequestGroup, with additional meta-data
        requestgroup = {
            "name": f"{request.obj.id}",  # The title
            "proposal": altdata["PROPOSAL_ID"],
            "ipp_value": request.payload["priority"],
            "operator": "SINGLE",
            "observation_type": request.payload["observation_mode"],
            "requests": [
                {
                    "configurations": configurations,
                    "windows": windows,
                    "location": location,
                }
            ],
        }

        return requestgroup


class BLANCOAPI(FollowUpAPI):
    """An interface to BLANCO operations."""

    @staticmethod
    def delete(request, session, **kwargs):
        """Delete a follow-up request from BLANCO queue.

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

        if len(request.transactions) == 0:
            session.query(FollowupRequest).filter(
                FollowupRequest.id == request.id
            ).delete()
            session.commit()
        else:
            altdata = request.allocation.altdata

            if not altdata:
                raise ValueError("Missing allocation information.")

            content = request.transactions[0].response["content"]
            content = json.loads(content)

            if "id" in content:
                uid = content["id"]

                r = requests.post(
                    f"{requestpath}{uid}/cancel/",
                    headers={"Authorization": f"Token {altdata['API_TOKEN']}"},
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

            else:
                session.query(FollowupRequest).filter(
                    FollowupRequest.id == request.id
                ).delete()
                session.commit()

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

    form_json_schema_altdata = {
        "type": "object",
        "properties": {
            "API_TOKEN": {
                "type": "string",
                "title": "API Token for NEWFIRM",
            },
            "PROPOSAL_ID": {
                "type": "string",
                "title": "Proposal ID",
            },
        },
        "required": ["API_TOKEN", "PROPOSAL_ID"],
    }


class NEWFIRMAPI(BLANCOAPI):
    """An interface to BLANCO NEWFIRM operations."""

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request, session, **kwargs):
        """Submit a follow-up request to BLANCO's NEWFIRM.

        Parameters
        ----------
        request: skyportal.models.FollowupRequest
            The request to add to the queue and the SkyPortal database.
        session: sqlalchemy.Session
            Database session for this transaction
        """

        from ..models import FacilityTransaction

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError("Missing allocation information.")

        blancoreq = BLANCO_NEWFIRM_Request(request)
        requestgroup = blancoreq.requestgroup

        r = requests.post(
            requestpath,
            headers={"Authorization": f"Token {altdata['API_TOKEN']}"},
            json=requestgroup,  # Make sure you use json!
        )

        if r.status_code == 201:
            request.status = "submitted"
        else:
            request.status = r.content.decode()

        transaction = FacilityTransaction(
            request=http.serialize_requests_request(r.request),
            response=http.serialize_requests_response(r),
            followup_request=request,
            initiator_id=request.last_modified_by_id,
        )

        session.add(transaction)
        session.commit()

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
            "observation_mode": {
                "type": "string",
                "enum": ["NORMAL", "RAPID_RESPONSE", "TIME_CRITICAL"],
                "default": "NORMAL",
            },
            "observation_choices": {
                "type": "array",
                "title": "Desired Observations",
                "items": {
                    "type": "string",
                    "enum": ["JX", "HX", "KXs"],
                },
                "uniqueItems": True,
                "minItems": 1,
            },
            "exposure_time": {
                "title": "Exposure Time [s]",
                "type": "number",
                "default": 8.0,
                "maximum": 40,
            },
            "sequence_repeats": {
                "title": "Sequence Repeats",
                "type": "number",
                "default": 1,
            },
            "coadds": {
                "title": "Number of coadds",
                "type": "number",
                "default": 1,
            },
            "start_date": {
                "type": "string",
                "default": datetime.utcnow().isoformat(),
                "title": "Start Date (UT)",
            },
            "end_date": {
                "type": "string",
                "title": "End Date (UT)",
                "default": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            },
            "maximum_airmass": {
                "title": "Maximum Airmass (1-3)",
                "type": "number",
                "default": 2.0,
                "minimum": 1,
                "maximum": 3,
            },
            "minimum_lunar_distance": {
                "title": "Minimum Lunar Distance [deg.] (0-180)",
                "type": "number",
                "default": 30.0,
                "minimum": 0,
                "maximum": 180,
            },
            "priority": {
                "title": "IPP (0-2)",
                "type": "number",
                "default": 1.0,
                "minimum": 0,
                "maximum": 2,
            },
        },
        "required": [
            "observation_choices",
            "sequence_repeats",
            "coadds",
            "start_date",
            "end_date",
            "maximum_airmass",
            "minimum_lunar_distance",
            "priority",
        ],
    }

    ui_json_schema = {"observation_choices": {"ui:widget": "checkboxes"}}
