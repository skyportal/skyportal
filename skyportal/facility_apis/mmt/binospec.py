from baselayer.app.env import load_env

from .. import FollowUpAPI
from .utils import base_mmt_properties, catch_timeout_and_no_endpoint

env, cfg = load_env()


def check_payload(payload):
    keys = payload.keys()

    if "observation_type" not in keys or payload["observation_type"] not in [
        "Imaging",
        "Spectroscopy",
    ]:
        raise ValueError("A valid observation type must be provided")

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
        if "grating" not in keys or payload["grating"] not in valid_ranges:
            raise ValueError("A valid grating must be provided")
        if payload["grating"] != 1000:
            if (
                "central_wavelength" not in keys
                or payload["central_wavelength"] not in valid_ranges[payload["grating"]]
            ):
                raise ValueError("A valid central wavelength must be provided")
        else:
            if "central_wavelength" not in keys or not any(
                payload["central_wavelength"] in r
                for r in valid_ranges[payload["grating"]]
            ):
                raise ValueError("A valid central wavelength must be provided")
        if "slit_width" not in keys or payload["slit_width"] not in [
            "Longslit0_75",
            "Longslit1",
            "Longslit1_25",
            "Longslit1_5",
            "Longslit5",
        ]:
            raise ValueError("A valid slit width must be provided")
        if "filter" not in keys or payload["filter"] not in ["LP3800", "LP3500"]:
            raise ValueError("A valid filter must be provided")
    else:
        if "maskid" not in keys or payload["maskid"] not in [110]:
            raise ValueError("A valid mask id must be provided")
        if "exposure_time" not in keys or payload["exposure_time"] not in [400]:
            raise ValueError("A valid exposure time must be provided")
        if "filter" not in keys or payload["filter"] not in ["g", "r", "i", "z"]:
            raise ValueError("A valid filter must be provided")


class BINOSPECAPI(FollowUpAPI):
    """SkyPortal interface to BINOSPEC"""

    @staticmethod
    @catch_timeout_and_no_endpoint
    def submit(request, session, **kwargs):
        return

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
            ],
            "dependencies": {
                "observation_type": {
                    "oneOf": [imager_schema, spectroscopy_schema],
                },
            },
        }

    ui_json_schema = {}

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
        "required": [],
    }
