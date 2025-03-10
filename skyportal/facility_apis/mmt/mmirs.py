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
    catch_timeout_and_no_endpoint,
    check_base_mmt_payload,
    check_obj_for_mmt,
    get_base_mmt_json_payload,
)

env, cfg = load_env()

log = make_log("facility_apis/mmt/mmirs")


def check_request(request):
    payload = request.payload

    check_base_mmt_payload(payload)
    check_obj_for_mmt(request.obj)

    if payload["observation_type"] == "Specroscopy":
        if payload.get("grism") not in ["J", "HK", "HK3"]:
            raise ValueError("A valid grism must be provided")
        if payload.get("readtab") not in ["ramp_4.426"]:
            raise ValueError("A valid read tab must be provided")
        if payload.get("slitwidth") not in [
            "1pixel",
            "2pixel",
            "3pixel",
            "4pixel",
            "5pixel",
            "6pixel",
            "12pixel",
        ]:
            raise ValueError("A valid slit width must be provided")
        if payload.get("slitwidthproperty") not in ["long", "short"]:
            raise ValueError("A valid slit width property must be provided")
        if payload.get("nb_visits_per_night") not in (0, 1):
            raise ValueError("A valid number of visits per night must be provided")
        if payload.get("filter") not in ["HK", "zJ"]:
            raise ValueError("A valid filter must be provided")
    else:
        if payload.get("dithersize") not in (5, 7, 10, 15, 20, 30, 60, 120, 210):
            raise ValueError("A valid dither size must be provided")
        if payload.get("readtab") not in ["ramp_4.426", "ramp_1.475"]:
            raise ValueError("A valid read tab must be provided")
        if payload.get("maskid") is None:
            raise ValueError("A valid mask id must be provided")
        if payload.get("exposure_time") is None:
            raise ValueError("A valid exposure time must be provided")
        if payload.get("nb_visits_per_night") not in (0, 1):
            raise ValueError("A valid number of visits per night must be provided")
        if payload.get("filter") not in ["J", "H", "K", "Ks"]:
            raise ValueError("A valid filter must be provided")


class MMIRSAPI(FollowUpAPI):
    """SkyPortal interface to the MMIRS"""

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
        check_request(request)

        json_payload = (get_base_mmt_json_payload(obj, altdata, payload),)

        if payload["observation_type"] == "Spectroscopy":
            json_payload = {
                "grism": payload.get("grism"),
                "readtab": payload.get("readtab"),
                "slitwidth": payload.get("slitwidth"),
                "slitwidthproperty": payload.get("slitwidthproperty"),
                "filter": payload.get("filter"),
                **json_payload,
            }
        else:
            json_payload = {
                "maskid": payload.get("maskid"),
                "exposuretime": payload.get("exposure_time"),
                "filter": payload.get("filter"),
                **json_payload,
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
    def get(request, session, **kwargs):
        return

    @staticmethod
    @catch_timeout_and_no_endpoint
    def delete(request, session, **kwargs):
        return

    def custom_json_schema(instrument, user, **kwargs):
        imager_schema = {
            "properties": {
                "observation_type": {"enum": ["Imaging"]},
                "dithersize": {
                    "type": "integer",
                    "title": "Dither Size",
                    "enum": [5, 7, 10, 15, 20, 30, 60, 120, 210],
                },
                "readtab": {
                    "type": "string",
                    "title": "Read Tab",
                    "enum": ["ramp_4.426", "ramp_1.475"],
                },
                "maskid": {
                    "type": "integer",
                    "title": "Mask ID",
                    "default": 110,
                },
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
                    "enum": ["J", "H", "K", "Ks"],
                },
            },
            "required": [
                "readtab",
                "maskid",
                "exposure_time",
                "exposure_time",
                "nb_visits_per_night",
                "filter",
            ],
        }

        spectroscopy_schema = {
            "properties": {
                "observation_type": {"enum": ["Spectroscopy"]},
                "grism": {
                    "type": "string",
                    "title": "Grism",
                    "enum": ["J", "HK", "HK3"],
                },
                "readtab": {
                    "type": "string",
                    "title": "Read Tab",
                    "enum": ["ramp_4.426"],
                },
                "slitwidth": {
                    "type": "string",
                    "title": "Slit Width",
                    "enum": [
                        "1pixel",
                        "2pixel",
                        "3pixel",
                        "4pixel",
                        "5pixel",
                        "6pixel",
                        "12pixel",
                    ],
                },
                "slitwidthproperty": {
                    "type": "string",
                    "title": "Slit Width Property",
                    "enum": ["long", "short"],
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
                    "enum": ["HK", "zJ"],
                    "default": "HK",
                },
            },
            "required": [
                "grism",
                "readtab",
                "slitwidth",
                "slitwidthproperty",
                "nb_visits_per_night",
                "filter",
            ],
        }

        return {
            "type": "object",
            "properties": {
                **base_mmt_properties,
            },
            "required": ["observation_type"],
            "dependencies": {
                "observation_type": {
                    "oneOf": [imager_schema, spectroscopy_schema],
                },
            },
        }

    ui_json_schema = {}

    form_json_schema_altdata = base_mmt_aldata
