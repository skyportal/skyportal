from datetime import timedelta

from baselayer.app.env import load_env

from ..utils.naive_datetime import utcnow_naive
from .generic import GENERICAPI

env, cfg = load_env()


def validate_request(request, filters):
    """Validate FollowupRequest contents for the NGPS queue.

    Parameters
    ----------
    request : skyportal.models.FollowupRequest
        The request to send to the instrument.
    filters : List[string]
        Filters allowed by instrument
    """

    for param in [
        "observation_choices",
        "exposure_time",
        "binspat",
        "binspect",
        "maximum_airmass",
        "priority",
        "start_date",
        "end_date",
    ]:
        if param not in request.payload:
            raise ValueError(f"Parameter {param} required.")

    for filt in request.payload["observation_choices"]:
        if filt not in filters:
            raise ValueError(f"Filter configuration {filt} unknown.")

    exposure_time = str(request.payload["exposure_time"]).strip()
    prefix, _, value = exposure_time.partition(" ")
    if prefix not in ["SNR", "SET"]:
        raise ValueError("exposure_time must be prefixed with 'SNR' or 'SET'.")
    try:
        if float(value) <= 0:
            raise ValueError
    except ValueError:
        raise ValueError(
            "exposure_time must be of the form 'SNR <value>' or 'SET <value>', "
            "with value a positive number."
        )

    if request.payload["binspat"] < 1:
        raise ValueError("binspat must be a positive integer.")

    if request.payload["binspect"] < 1:
        raise ValueError("binspect must be a positive integer.")

    if request.payload["maximum_airmass"] < 1:
        raise ValueError("maximum_airmass must be at least 1.")

    if request.payload["priority"] < 1 or request.payload["priority"] > 5:
        raise ValueError("priority must be within 1-5.")


def prepare_payload_ngps(payload, existing_payload=None):
    """Format a payload for NGPS.

    Parameters
    ----------
    payload: dict
        The payload to format.

    Returns
    -------
    formatted_payload: dict
        The formatted payload.
    """

    payload["exposure_time"] = payload.get(
        "exposure_time",
        "SNR 7.5" if existing_payload is None else existing_payload["exposure_time"],
    )
    payload["binspat"] = payload.get(
        "binspat",
        2 if existing_payload is None else existing_payload["binspat"],
    )
    payload["binspect"] = payload.get(
        "binspect",
        3 if existing_payload is None else existing_payload["binspect"],
    )
    payload["maximum_airmass"] = payload.get(
        "maximum_airmass",
        2.5 if existing_payload is None else existing_payload["maximum_airmass"],
    )

    if "advanced" in payload:
        del payload["advanced"]

    return payload


class NGPSAPI(GENERICAPI):
    """SkyPortal interface for P200 NGPS follow-up"""

    _validate_request = staticmethod(validate_request)

    @staticmethod
    def prepare_payload(payload, existing_payload=None):
        return prepare_payload_ngps(payload, existing_payload)

    def custom_json_schema(instrument, user, **kwargs):
        form_json_schema = {
            "type": "object",
            "properties": {
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
                "priority": {
                    "type": "number",
                    "default": 1.0,
                    "minimum": 1.0,
                    "maximum": 5.0,
                    "title": "Priority",
                },
                "start_date": {
                    "type": "string",
                    "format": "date",
                    "default": utcnow_naive().date().isoformat(),
                    "title": "Start Date (UT)",
                },
                "end_date": {
                    "type": "string",
                    "format": "date",
                    "title": "End Date (UT)",
                    "default": (utcnow_naive().date() + timedelta(days=7)).isoformat(),
                },
                "advanced": {
                    "type": "boolean",
                    "title": "Show Advanced Options",
                    "default": False,
                },
            },
            "dependencies": {
                "advanced": {
                    "oneOf": [
                        {
                            "properties": {
                                "advanced": {"enum": [True]},
                                "exposure_time": {
                                    "title": "Exposure Time",
                                    "type": "string",
                                    "default": "SNR 7.5",
                                    "pattern": r"^(SNR|SET) [0-9]*\.?[0-9]+$",
                                    "description": (
                                        "Either 'SNR <value>' to target a signal-to-noise "
                                        "ratio, or 'SET <value>' for a fixed exposure "
                                        "length in seconds."
                                    ),
                                },
                                "binspat": {
                                    "title": "Spatial Binning",
                                    "type": "integer",
                                    "default": 2,
                                    "minimum": 1,
                                },
                                "binspect": {
                                    "title": "Spectral Binning",
                                    "type": "integer",
                                    "default": 3,
                                    "minimum": 1,
                                },
                                "maximum_airmass": {
                                    "title": "Maximum Airmass (1-3)",
                                    "type": "number",
                                    "default": 2.5,
                                    "minimum": 1.0,
                                    "maximum": 3.0,
                                },
                            },
                            "required": [
                                "exposure_time",
                                "binspat",
                                "binspect",
                                "maximum_airmass",
                            ],
                        },
                        {
                            "properties": {
                                "advanced": {"enum": [False]},
                            }
                        },
                    ]
                },
            },
            "required": [
                "observation_choices",
                "priority",
                "start_date",
                "end_date",
            ],
        }

        return form_json_schema

    alias_lookup = {
        "observation_choices": "Request",
        "start_date": "Start Date",
        "end_date": "End Date",
        "priority": "Priority",
        "exposure_time": "Exposure Time",
        "binspat": "Binspat",
        "binspect": "Binspect",
    }
