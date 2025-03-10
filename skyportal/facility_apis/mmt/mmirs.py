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

    if payload["observation_type"] == "Specroscopy":
        if "grism" not in keys or payload["grism"] not in ["J", "HK", "HK3"]:
            raise ValueError("A valid grism must be provided")
        if "readtab" not in keys or payload["readtab"] not in ["ramp_4.426"]:
            raise ValueError("A valid read tab must be provided")
        if "slitwidth" not in keys or payload["slitwidth"] not in [
            "1pixel",
            "2pixel",
            "3pixel",
            "4pixel",
            "5pixel",
            "6pixel",
            "12pixel",
        ]:
            raise ValueError("A valid slit width must be provided")
        if "slitwidthproperty" not in keys or payload["slitwidthproperty"] not in [
            "long",
            "short",
        ]:
            raise ValueError("A valid slit width property must be provided")
        if "filter" not in keys or payload["filter"] not in ["HK", "zJ"]:
            raise ValueError("A valid filter must be provided")
    else:
        if "dithersize" in keys and payload["dithersize"] not in [
            5,
            7,
            10,
            15,
            20,
            30,
            60,
            120,
            210,
        ]:
            raise ValueError("A valid dither size must be provided")

        if "readtab" not in keys or payload["readtab"] not in ["ramp_4.426"]:
            raise ValueError("A valid read tab must be provided")
        if "maskid" not in keys or payload["maskid"] not in [110]:
            raise ValueError("A valid mask id must be provided")
        if "exposure_time" not in keys or payload["exposure_time"] not in [400]:
            raise ValueError("A valid exposure time must be provided")
        if "nb_visits_per_night" not in keys or payload["nb_visits_per_night"] not in [
            0,
            1,
        ]:
            raise ValueError("A valid number of visits per night must be provided")
        if "filter" not in keys or payload["filter"] not in ["J", "H", "K", "Ks"]:
            raise ValueError("A valid filter must be provided")


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
                "dithersize": {
                    "type": "integer",
                    "title": "Dither Size",
                    "enum": [5, 7, 10, 15, 20, 30, 60, 120, 210],
                },
                "readtab": {
                    "type": "string",
                    "title": "Read Tab",
                    "enum": ["ramp_4.426", "ramp_4.426"],
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
