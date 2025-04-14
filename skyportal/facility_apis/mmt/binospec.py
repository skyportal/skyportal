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
    mmt_imager_schema,
)

log = make_log("facility_apis/mmt/binospec")

slit_width_to_mask_id = {
    "Longslit0_75": 113,
    "Longslit1": 111,
    "Longslit1_25": 131,
    "Longslit1_5": 114,
    "Longslit5": 112,
}


def check_request(request):
    """
    Check that the request has the required fields for a BINOSPEC request

    Parameters
    ----------
    request : FollowupRequest
        The request to check
    """
    payload = request.payload

    check_mmt_payload(payload)
    check_obj_for_mmt(request.obj)

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
        if payload.get("slit_width") not in [
            "Longslit0_75",
            "Longslit1",
            "Longslit1_25",
            "Longslit1_5",
            "Longslit5",
        ]:
            raise ValueError("A valid slit width must be provided")
        if payload.get("filters") not in ["LP3800", "LP3500"]:
            raise ValueError("A valid filter must be provided")
    else:
        if payload.get("filters") not in ["g", "r", "i", "z"]:
            raise ValueError("A valid filter must be provided")


class BINOSPECAPI(FollowUpAPI):
    """SkyPortal interface to BINOSPEC"""

    @staticmethod
    @catch_timeout_and_no_endpoint
    def submit(request, session, **kwargs):
        """
        Submit a follow-up request to the BINOSPEC instrument from MMT

        Parameters
        ----------
        request : FollowupRequest
            The request to submit
        session : DBSession
            Database session
        kwargs : dict
            Additional keyword arguments
        """
        payload = request.payload
        check_request(request)

        if payload["observation_type"] == "Spectroscopy":
            specific_payload = {
                "grating": payload.get("grating"),
                "centralwavelength": payload.get("central_wavelength"),
                "slitwidth": payload.get("slit_width"),
                "maskid": slit_width_to_mask_id[payload.get("slit_width")],
            }
        else:
            specific_payload = {
                "filters": payload.get("filters"),
                "maskid": 110
            }

        submit_mmt_request(session, request, specific_payload, 16, log, **kwargs)

    @staticmethod
    @catch_timeout_and_no_endpoint
    def delete(request, session, **kwargs):
        delete_mmt_request(session, request, log, **kwargs)

    def custom_json_schema(instrument, user, **kwargs):
        imager_schema = {
            "properties": {
                "filters": {
                    "type": "string",
                    "title": "Filter",
                    "enum": ["g", "r", "i", "z"],
                },
                **mmt_imager_schema["properties"],
            },
            "required": [
                "filters",
            ] + mmt_imager_schema["required"],
        }

        spectroscopy_schema = {
            "properties": {
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
                    "default": "Longslit0_75",
                },
                "filters": {
                    "type": "string",
                    "title": "Filter",
                    "enum": ["LP3800", "LP3500"],
                    "default": "LP3800",
                },
                "grating": {
                    "type": "integer",
                    "title": "Grating",
                    "enum": [270, 600, 1000],
                },
            },
            "required": [
                "slit_width",
                "grating",
                "central_wavelength",
                "filters",
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
            },
        }

        return {
            "type": "object",
            "properties": {
                **mmt_properties,
            },
            "required": [
                "filters",
            ]
            + mmt_required,
            "if": {
                "properties": {"observation_type": {"const": "Imaging"}},
            },
            "then": imager_schema,
            "else": spectroscopy_schema,
        }

    ui_json_schema = {}

    form_json_schema_altdata = mmt_aldata
