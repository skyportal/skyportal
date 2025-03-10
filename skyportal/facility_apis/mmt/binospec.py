import functools

import requests

from baselayer.app.env import load_env

from .. import FollowUpAPI
from .utils import base_mmt_properties

env, cfg = load_env()


def catch_timeout_and_no_endpoint(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.Timeout:
            raise ValueError("Unable to reach the BINOSPEC server")
        except KeyError as e:
            if "endpoint" in str(e):
                raise ValueError("BINOSPEC endpoint is missing from configuration")

    return wrapper


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
                    "default": 400,
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
            }
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
                "filter": {
                    "type": "string",
                    "title": "Filter",
                    "enum": ["LP3800", "LP3500"],
                    "default": "LP3800",
                },
            },
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
