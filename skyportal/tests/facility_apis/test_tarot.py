from datetime import datetime, timedelta

from skyportal.facility_apis.tarot import create_observation_strings
from skyportal.models import FollowupRequest


def test_create_observation_string(public_source):
    # Observation Line format:
    # '"source_id" ra dec date drift_ra drift_dec time f1 time f2 time f3 time f1 time f2 time f3 priority station'
    filter_value = {
        "NoFilter": 0,
        "g": 13,
        "r": 14,
        "i": 15,
    }
    public_source.ra = 34.34
    public_source.dec = 16.16

    # Test with 1 exposure and no filters
    followup_request = FollowupRequest(
        requester_id=1,
        obj_id=public_source.id,
        payload={
            "station_name": "Tarot_Calern",
            "date": "2023-10-01T15:10:10.000",
            "exposure_time": 120,
            "exposure_counts": 1,
            "observation_choices": ["NoFilter"],
            "priority": 0,
        },
        status="submitted",
        allocation_id=1,
    )
    followup_request.obj = public_source

    observation_strings = create_observation_strings(followup_request)
    assert isinstance(observation_strings, list)
    assert all(
        isinstance(observation_string, str)
        for observation_string in observation_strings
    )

    assert observation_strings[0] == (
        f'"{public_source.id}" {public_source.ra} {public_source.dec} {followup_request.payload["date"]} '
        f"0.004180983 0.00 "
        f"{followup_request.payload['exposure_time']} 0 "
        f"0 0 "
        f"0 0 "
        f"0 0 "
        f"0 0 "
        f"0 0 "
        f"{followup_request.payload['priority']} {followup_request.payload['station_name']}"
    )

    # Test with 1 exposure count by filter with 1 filters
    followup_request.payload["observation_choices"] = ["g"]
    observation_strings = create_observation_strings(followup_request)
    assert observation_strings[0] == (
        f'"{public_source.id}" {public_source.ra} {public_source.dec} {followup_request.payload["date"]} '
        f"0.004180983 0.00 "
        f"{followup_request.payload['exposure_time']} {filter_value['g']} "
        f"0 0 "
        f"0 0 "
        f"0 0 "
        f"0 0 "
        f"0 0 "
        f"{followup_request.payload['priority']} {followup_request.payload['station_name']}"
    )

    # Test with 1 exposure count by filter with all filters
    followup_request.payload["observation_choices"] = ["g", "r", "i"]
    observation_strings = create_observation_strings(followup_request)
    assert observation_strings[0] == (
        f'"{public_source.id}" {public_source.ra} {public_source.dec} {followup_request.payload["date"]} '
        f"0.004180983 0.00 "
        f"{followup_request.payload['exposure_time']} {filter_value['g']} "
        f"{followup_request.payload['exposure_time']} {filter_value['r']} "
        f"{followup_request.payload['exposure_time']} {filter_value['i']} "
        f"0 0 "
        f"0 0 "
        f"0 0 "
        f"{followup_request.payload['priority']} {followup_request.payload['station_name']}"
    )

    # Test with 2 exposure counts by filter with all filters
    followup_request.payload["exposure_counts"] = 2
    observation_strings = create_observation_strings(followup_request)
    assert observation_strings[0] == (
        f'"{public_source.id}" {public_source.ra} {public_source.dec} {followup_request.payload["date"]} '
        f"0.004180983 0.00 "
        f"{followup_request.payload['exposure_time']} {filter_value['g']} "
        f"{followup_request.payload['exposure_time']} {filter_value['r']} "
        f"{followup_request.payload['exposure_time']} {filter_value['i']} "
        f"{followup_request.payload['exposure_time']} {filter_value['g']} "
        f"{followup_request.payload['exposure_time']} {filter_value['r']} "
        f"{followup_request.payload['exposure_time']} {filter_value['i']} "
        f"{followup_request.payload['priority']} {followup_request.payload['station_name']}"
    )
