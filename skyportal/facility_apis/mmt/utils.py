import functools

import requests


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


def check_base_mmt_payload(payload):
    if payload.get("observation_type") not in [
        "Imaging",
        "Spectroscopy",
    ]:
        raise ValueError("A valid observation type must be provided")
    if payload.get("pa") is None or payload["pa"] < -360.0 or payload["pa"] > 360.0:
        raise ValueError("A valid parallactic angle must be provided")
    if payload.get("pm_ra") is None:
        raise ValueError("A valid Proper Motion RA must be provided")
    if payload.get("pm_dec") is None:
        raise ValueError("A valid Proper Motion DEC must be provided")
    if payload.get("exposure_counts") is None or payload["exposure_counts"] < 1:
        raise ValueError("A valid number of exposures must be provided")
    if payload.get("visits") is None:
        raise ValueError("A valid number of visits must be provided")
    if payload.get("priority") not in [1, 2, 3]:
        raise ValueError("A valid priority must be provided")
    if not isinstance(payload.get("photometric"), bool):
        raise ValueError("A valid photometric value must be provided")
    if not isinstance(payload.get("target_of_opportunity"), bool):
        raise ValueError("A valid target of opportunity value must be provided")


base_mmt_properties = {
    "observation_type": {
        "type": "string",
        "title": "Observation Type",
        "enum": [
            "Imaging",
            "Spectroscopy",
        ],
        "default": "Imaging",
    },
    "pa": {
        "type": "number",
        "title": "Parallactic Angle",
        "default": 0.0,
        "minimum": -360.0,
        "maximum": 360.0,
    },
    "pm_ra": {
        "type": "number",
        "title": "Proper Motion RA",
        "default": 0.0,
    },
    "pm_dec": {
        "type": "number",
        "title": "Proper Motion DEC",
        "default": 0.0,
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
        "enum": [1, 2, 3],
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
}

base_mmt_required = [
    "observation_type",
    "pa",
    "pm_ra",
    "pm_dec",
    "exposure_counts",
    "visits",
    "priority",
    "photometric",
    "target_of_opportunity",
]

base_mmt_aldata = {
    "type": "object",
    "properties": {
        "token": {
            "type": "string",
            "title": "Token",
        },
    },
    "required": ["token"],
}
