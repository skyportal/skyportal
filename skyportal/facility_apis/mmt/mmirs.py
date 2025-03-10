from baselayer.app.env import load_env

from .. import FollowUpAPI
from .utils import base_mmt_properties, catch_timeout_and_no_endpoint

env, cfg = load_env()


class MMIRSAPI(FollowUpAPI):
    """SkyPortal interface to the MMIRS"""

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
                    "default": 400,
                },
            },
            "required": ["filter"],
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
                    "enum": ["ramp_1.475"],
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
            }
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
        "required": [
            "username",
            "password",
        ],
    }
