import requests

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ...models import FacilityTransaction, FollowupRequest
from ...utils import http
from .. import FollowUpAPI
from .utils import (
    base_mmt_aldata,
    base_mmt_properties,
    base_mmt_required,
    catch_timeout_and_no_endpoint,
    check_base_mmt_payload,
)

env, cfg = load_env()

log = make_log("facility_apis/mmt/binospec")


def check_payload(payload):
    check_base_mmt_payload(payload)

    if payload["observation_type"] == "Spectroscopy":
        valid_ranges = {
            270: range(5501, 7839),
            600: range(5146, 8784),
            1000: [
                range(4108, 4684),
                range(5181, 7274),
                range(7363, 7968),
                range(8153, 8773),
                range(8897, 9280),
            ],
        }
        if payload.get("grating") not in valid_ranges:
            raise ValueError("A valid grating must be provided")
        if payload["grating"] != 1000:
            if (
                payload.get("central_wavelength")
                not in valid_ranges[payload["grating"]]
            ):
                raise ValueError("A valid central wavelength must be provided")
        else:
            if not any(
                payload.get("central_wavelength") in r
                for r in valid_ranges[payload["grating"]]
            ):
                raise ValueError("A valid central wavelength must be provided")
        if payload.get("slitwidth") not in [
            "Longslit0_75",
            "Longslit1",
            "Longslit1_25",
            "Longslit1_5",
            "Longslit5",
        ]:
            raise ValueError("A valid slit width must be provided")
        if payload.get("filter") not in ["LP3800", "LP3500"]:
            raise ValueError("A valid filter must be provided")
    else:
        if payload.get("maskid") is None:
            raise ValueError("A valid mask id must be provided")
        if payload.get("exposure_time") is None:
            raise ValueError("A valid exposure time must be provided")
        if payload.get("filter") not in ["g", "r", "i", "z"]:
            raise ValueError("A valid filter must be provided")


def check_obj(obj):
    if not obj.id or len(obj.id) < 2:
        raise ValueError("Object ID must be more than 2 characters")
    elif len(obj.id) > 50:
        obj.id = obj.id[:50]
    else:
        obj.id = "".join(c for c in obj.id if c.isalnum())
    if not obj.ra:
        raise ValueError("Missing required field 'ra'")
    if not obj.dec:
        raise ValueError("Missing required field 'dec'")
    if not obj.mag_nearest_source:
        raise ValueError("Missing required field 'magnitude'")


class BINOSPECAPI(FollowUpAPI):
    """SkyPortal interface to BINOSPEC"""

    @staticmethod
    @catch_timeout_and_no_endpoint
    def submit(request, session, **kwargs):
        if cfg["app.mmt.endpoint"] is None:
            raise ValueError("MMT endpoint not configured")

        altdata = request.allocation.altdata
        if not altdata or "token" not in altdata:
            raise ValueError("Missing allocation information.")

        obj = request.obj
        payload = request.payload
        check_obj(obj)
        check_payload(request.payload)

        json_payload = {
            "token": altdata["token"],
            "id": obj.id,
            #     "ra", "objectid", "observationtype", "moon", "seeing", "photometric", "priority", "dec",
            # "ra_decimal", "dec_decimal", "pm_ra", "pm_dec", "magnitude", "exposuretime", "numberexposures",
            # "visits", "onevisitpernight", "filter", "grism", "grating", "centralwavelength", "readtab",
            # "gain", "dithersize", "epoch", "submitted", "modified", "notes", "pa", "maskid", "slitwidth",
            # "slitwidthproperty", "iscomplete", "disabled", "notify", "locked", "findingchartfilename",
            # "instrumentid", "targetofopportunity", "reduced", "exposuretimeremaining", "totallength",
            # "totallengthformatted", "exposuretimeremainingformatted", "exposuretimecompleted",
            # "percentcompleted", "offsetstars", "details", "mask")
            "objectid": obj.id,
            "ra": obj.ra,
            "dec": obj.dec,
            "magnitude": obj.mag_nearest_source,
            "epoch": 2000.0,
            "observationtype": payload["observation_type"],
            "exposuretime": payload["exposure_time"],
            "numberexposures": payload["numberexposures"],
            "visits": payload["visits"],
            "onevisitpernight": payload["nb_visits_per_night"],
            "filter": payload["filter"],
            "instrumentid": 1,
            "maskid": payload.get("maskid", 110),
            "pa": payload.get("pa", 0),
            "pm_ra": payload.get("pm_ra", 0),
            "pm_dec": payload.get("pm_dec", 0),
            "priority": payload.get("priority", 3),
            "slitwidth": payload.get("slitwidth", 1),
            "slitwidthproperty": payload.get("slitwidthproperty", "long"),
            "grating": payload.get("grating", 270),
            "centralwavelength": payload.get("central_wavelength", 5501),
            "readtab": payload.get("readtab", "ramp_4.426"),
        }

        response = requests.post(
            f"{cfg['app.mmt.endpoint']}/catalogTarget/{obj.id}",
            json=json_payload,
            data=None,
            files=None,
            timeout=5.0,
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
                    payload={"obj_key": request.obj.internal_key},
                )
            if kwargs.get("refresh_requests", False):
                flow.push(
                    request.last_modified_by_id, "skyportal/REFRESH_FOLLOWUP_REQUESTS"
                )
        except Exception as e:
            log(f"Failed to send notification: {str(e)}")

    @staticmethod
    @catch_timeout_and_no_endpoint
    def delete(request, session, **kwargs):
        last_modified_by_id = request.last_modified_by_id
        obj_internal_key = request.obj.internal_key

        # this happens for failed submissions, just go ahead and delete
        if len(request.transactions) == 0:
            session.query(FollowupRequest).filter(
                FollowupRequest.id == request.id
            ).delete()
            session.commit()
        else:
            if cfg["app.mmt_endpoint"] is None:
                raise ValueError("MMT endpoint not configured")

            altdata = request.allocation.altdata
            if not altdata:
                raise ValueError("Missing allocation information.")

            response = requests.post(
                f"{cfg['app.mmt_endpoint']}",
                auth=(altdata["browser_username"], altdata["browser_password"]),
                timeout=5.0,
            )

            if response.status_code != 200:
                request.status = f"rejected: deletion failed - {response.status_code}"
            else:
                request.status = "deleted"

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

    def custom_json_schema(instrument, user, **kwargs):
        imager_schema = {
            "properties": {
                "observation_type": {"enum": ["Imaging"]},
                "maskid": {"type": "integer", "title": "Mask ID", "default": 110},
                "exposure_time": {
                    "type": "number",
                    "title": "Exposure Time (s)",
                },
                "nb_visits_per_night": {
                    "type": "integer",
                    "title": "Number of Visits per Night",
                    "enum": [0, 1],
                    "default": 0,
                },
                "filter": {
                    "type": "string",
                    "title": "Filter",
                    **(
                        {"enum": instrument.to_dict().get("filters", [])}
                        if instrument.to_dict().get("filters")
                        else {
                            "readOnly": True,
                            "description": "Filters need to be added to this instrument",
                        }
                    ),
                },
            },
            "required": [
                "observation_type",
                "exposure_time",
                "nb_visits_per_night",
                "filter",
            ],
        }

        spectroscopy_schema = {
            "properties": {
                "observation_type": {"enum": ["Spectroscopy"]},
                "grating": {
                    "type": "integer",
                    "title": "Grating",
                    "enum": [270, 600, 1000],
                },
                "slit_width": {
                    "type": "string",
                    "title": "Slit Width",
                    "enum": [
                        "Longslit0_75",
                        "Longslit1",
                        "Longslit1_25",
                        "Longslit1_5",
                        "Longslit5",
                    ],
                },
                "nb_visits_per_night": {
                    "type": "integer",
                    "title": "Number of Visits per Night",
                    "enum": [0, 1],
                    "default": 1,
                },
                "filter": {
                    "type": "string",
                    "title": "Filter",
                    "enum": ["LP3800", "LP3500"],
                    "default": "LP3800",
                },
            },
            "required": [
                "observation_type",
                "slit_width",
                "grating",
                "central_wavelength",
                "nb_visits_per_night",
                "filter",
            ],
            "dependencies": {
                "grating": {
                    "oneOf": [
                        {
                            "properties": {
                                "grating": {"enum": [270]},
                                "central_wavelength": {
                                    "type": "integer",
                                    "description": "Enter a value between 5501 and 7838",
                                    "title": "Central Wavelength",
                                    "minimum": 5501,
                                    "maximum": 7838,
                                },
                            },
                        },
                        {
                            "properties": {
                                "grating": {"enum": [600]},
                                "central_wavelength": {
                                    "type": "integer",
                                    "description": "Enter a value between 5146 and 8783",
                                    "title": "Central Wavelength",
                                    "minimum": 5146,
                                    "maximum": 8783,
                                },
                            },
                        },
                        {
                            "properties": {
                                "grating": {"enum": [1000]},
                                "central_wavelength": {
                                    "type": "integer",
                                    "title": "Central Wavelength",
                                    "description": "Enter a value in one of these ranges: 4108-4683, 5181-7273, 7363-7967, 8153-8772, 8897-9279",
                                    "minimum": 4108,
                                    "maximum": 9279,
                                },
                            },
                        },
                    ]
                },
                "slit_width": {
                    "oneOf": [
                        {
                            "properties": {
                                "slit_width": {"enum": ["Longslit0_75"]},
                                "maskid": {
                                    "type": "integer",
                                    "title": "Mask ID",
                                    "default": 113,
                                },
                            },
                        },
                        {
                            "properties": {
                                "slit_width": {"enum": ["Longslit1"]},
                                "maskid": {
                                    "type": "integer",
                                    "title": "Mask ID",
                                    "default": 111,
                                },
                            },
                        },
                        {
                            "properties": {
                                "slit_width": {"enum": ["Longslit1_25"]},
                                "maskid": {
                                    "type": "integer",
                                    "title": "Mask ID",
                                    "default": 131,
                                },
                            },
                        },
                        {
                            "properties": {
                                "slit_width": {"enum": ["Longslit1_5"]},
                                "maskid": {
                                    "type": "integer",
                                    "title": "Mask ID",
                                    "default": 114,
                                },
                            },
                        },
                        {
                            "properties": {
                                "slit_width": {"enum": ["Longslit5"]},
                                "maskid": {
                                    "type": "integer",
                                    "title": "Mask ID",
                                    "default": 112,
                                },
                            },
                        },
                    ],
                },
            },
        }

        return {
            "type": "object",
            "properties": {
                **base_mmt_properties,
            },
            "required": [
                "observation_type",
                "filter",
            ]
            + base_mmt_required,
            "dependencies": {
                "observation_type": {
                    "oneOf": [imager_schema, spectroscopy_schema],
                },
            },
        }

    ui_json_schema = {}

    form_json_schema_altdata = base_mmt_aldata
