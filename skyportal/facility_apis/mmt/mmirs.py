import functools

import requests

from baselayer.app.env import load_env
from skyportal.facility_apis import FollowUpAPI

env, cfg = load_env()


def catch_timeout_and_no_endpoint(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.Timeout:
            raise ValueError("Unable to reach the MMIRS server")
        except KeyError as e:
            if "endpoint" in str(e):
                raise ValueError("MMIRS endpoint is missing from configuration")

    return wrapper


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
                "observation_choices": {
                    "type": "array",
                    "title": "Desired Observations",
                    "items": {
                        "type": "string",
                        "enum": instrument.to_dict()["filters"],
                    },
                    "uniqueItems": True,
                    "minItems": 1,
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
            }
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
                "observation_type": {
                    "type": "string",
                    "title": "Observation Type",
                    "enum": [
                        "Imaging",
                        "Spectroscopy",
                    ],
                    "default": "Imaging",
                },
                "exposure_counts": {
                    "type": "integer",
                    "title": "Number of Exposures",
                    "default": 1,
                },
                "visits": {
                    "type": "integer",
                    "title": "Number of Visits",
                    "default": 1,
                },
                "priority": {
                    "type": "integer",
                    "title": "Priority",
                    "default": 3,
                },
                "photometric": {
                    "type": "boolean",
                    "title": "Photometric",
                    "default": False,
                },
                "target_of_opportunity": {
                    "type": "boolean",
                    "title": "Target of Opportunity",
                    "default": False,
                },
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
