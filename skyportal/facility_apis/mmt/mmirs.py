from baselayer.log import make_log

from .. import FollowUpAPI
from .mmt_utils import (
    catch_timeout_and_no_endpoint,
    check_mmt_payload,
    check_obj_for_mmt,
    delete_mmt_request,
    mmt_aldata,
    mmt_properties,
    mmt_required,
    submit_mmt_request,
)

log = make_log("facility_apis/mmt/mmirs")


def check_request(request):
    """
    Check that the request has the required fields for the MMIRS instrument

    Parameters
    ----------
    request : FollowupRequest
        The request to check
    """
    payload = request.payload

    check_mmt_payload(payload)
    check_obj_for_mmt(request.obj)

    if payload["observation_type"] == "Spectroscopy":
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
        if payload.get("filters") not in ["HK", "zJ"]:
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
        if payload.get("filters") not in ["J", "H", "K", "Ks"]:
            raise ValueError("A valid filter must be provided")


class MMIRSAPI(FollowUpAPI):
    """SkyPortal interface to the MMIRS"""

    @staticmethod
    @catch_timeout_and_no_endpoint
    def submit(request, session, **kwargs):
        """
        Submit a followup request to the MMIRS instrument from MMT

        Parameters
        ----------
        request : FollowupRequest
            The request to submit
        session : DBSession
            The database session
        kwargs : dict
            Additional keyword arguments
        """
        payload = request.payload
        check_request(request)

        if payload["observation_type"] == "Spectroscopy":
            specific_payload = {
                "grism": payload.get("grism"),
                "readtab": payload.get("readtab"),
                "slitwidth": payload.get("slitwidth"),
                "slitwidthproperty": payload.get("slitwidthproperty"),
            }
        else:
            specific_payload = {
                "maskid": payload.get("maskid"),
                "exposuretime": payload.get("exposure_time"),
            }

        submit_mmt_request(session, request, specific_payload, 15, log, **kwargs)

    @staticmethod
    @catch_timeout_and_no_endpoint
    def delete(request, session, **kwargs):
        delete_mmt_request(session, request, log, **kwargs)

    def custom_json_schema(instrument, user, **kwargs):
        imager_schema = {
            "properties": {
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
                "filters": {
                    "type": "string",
                    "title": "Filter",
                    "enum": ["J", "H", "K", "Ks"],
                },
            },
            "required": [
                "dithersize",
                "readtab",
                "maskid",
                "exposure_time",
                "nb_visits_per_night",
                "filters",
            ],
        }

        spectroscopy_schema = {
            "properties": {
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
                "filters": {
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
                "filters",
            ],
        }

        return {
            "type": "object",
            "properties": {
                **mmt_properties,
            },
            "required": mmt_required,
            "if": {
                "properties": {"observation_type": {"const": "Imaging"}},
            },
            "then": imager_schema,
            "else": spectroscopy_schema,
        }

    ui_json_schema = {}

    form_json_schema_altdata = mmt_aldata
