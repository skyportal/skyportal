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
