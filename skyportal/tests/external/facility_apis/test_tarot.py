from datetime import datetime, timedelta

from astropy.time import Time

from skyportal.facility_apis.tarot import create_request_string
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
            "filters": ["NoFilter"],
            "priority": 0,
        },
        status="submitted",
        allocation_id=1,
    )
    followup_request.obj = public_source

    observation_strings = create_request_string(
        followup_request.obj,
        followup_request.payload,
        Time(followup_request.payload["date"], format="isot"),
        followup_request.payload["station_name"],
    )
    assert isinstance(observation_strings, str)

    assert observation_strings == (
        f'"{public_source.id}" {public_source.ra} {public_source.dec} {followup_request.payload["date"]} '
        f"0.004180983 0.00 "
        f"{followup_request.payload['exposure_time']} 0 "
        f"0 0 "
        f"0 0 "
        f"0 0 "
        f"0 0 "
        f"0 0 "
        f"{followup_request.payload['priority']} {followup_request.payload['station_name']}\n\r"
    )

    # Test with 1 exposure count by filter with 1 filter
    followup_request.payload["filters"] = ["g"]
    observation_strings = create_request_string(
        followup_request.obj,
        followup_request.payload,
        Time(followup_request.payload["date"], format="isot"),
        followup_request.payload["station_name"],
    )
    assert observation_strings == (
        f'"{public_source.id}" {public_source.ra} {public_source.dec} {followup_request.payload["date"]} '
        f"0.004180983 0.00 "
        f"{followup_request.payload['exposure_time']} {filter_value['g']} "
        f"0 0 "
        f"0 0 "
        f"0 0 "
        f"0 0 "
        f"0 0 "
        f"{followup_request.payload['priority']} {followup_request.payload['station_name']}\n\r"
    )

    # Test with 1 exposure count by filter with all filters
    followup_request.payload["filters"] = ["g", "r", "i"]
    observation_strings = create_request_string(
        followup_request.obj,
        followup_request.payload,
        Time(followup_request.payload["date"], format="isot"),
        followup_request.payload["station_name"],
    )
    assert observation_strings == (
        f'"{public_source.id}" {public_source.ra} {public_source.dec} {followup_request.payload["date"]} '
        f"0.004180983 0.00 "
        f"{followup_request.payload['exposure_time']} {filter_value['g']} "
        f"{followup_request.payload['exposure_time']} {filter_value['r']} "
        f"{followup_request.payload['exposure_time']} {filter_value['i']} "
        f"0 0 "
        f"0 0 "
        f"0 0 "
        f"{followup_request.payload['priority']} {followup_request.payload['station_name']}\n\r"
    )

    # Test with 2 exposure counts by filter with all filters
    followup_request.payload["exposure_counts"] = 2
    observation_strings = create_request_string(
        followup_request.obj,
        followup_request.payload,
        Time(followup_request.payload["date"], format="isot"),
        followup_request.payload["station_name"],
    )
    assert observation_strings == (
        f'"{public_source.id}" {public_source.ra} {public_source.dec} {followup_request.payload["date"]} '
        f"0.004180983 0.00 "
        f"{followup_request.payload['exposure_time']} {filter_value['g']} "
        f"{followup_request.payload['exposure_time']} {filter_value['r']} "
        f"{followup_request.payload['exposure_time']} {filter_value['i']} "
        f"{followup_request.payload['exposure_time']} {filter_value['g']} "
        f"{followup_request.payload['exposure_time']} {filter_value['r']} "
        f"{followup_request.payload['exposure_time']} {filter_value['i']} "
        f"{followup_request.payload['priority']} {followup_request.payload['station_name']}\n\r"
    )

    # Test with 3 exposure counts by filter with all filters
    followup_request.payload["exposure_counts"] = 3
    observation_strings = create_request_string(
        followup_request.obj,
        followup_request.payload,
        Time(followup_request.payload["date"], format="isot"),
        followup_request.payload["station_name"],
    )

    # The date of the second line should be after the exposure time of all the first exposure plus the time between
    date_first_scene = datetime.strptime(
        followup_request.payload["date"], "%Y-%m-%dT%H:%M:%S.%f"
    )
    date_second_scene = date_first_scene + timedelta(
        seconds=(followup_request.payload["exposure_time"] + 45) * 6
    )

    assert observation_strings == (
        f'"{public_source.id}" {public_source.ra} {public_source.dec} {date_first_scene.isoformat(timespec="milliseconds")} '
        f"0.004180983 0.00 "
        f"{followup_request.payload['exposure_time']} {filter_value['g']} "
        f"{followup_request.payload['exposure_time']} {filter_value['r']} "
        f"{followup_request.payload['exposure_time']} {filter_value['i']} "
        f"{followup_request.payload['exposure_time']} {filter_value['g']} "
        f"{followup_request.payload['exposure_time']} {filter_value['r']} "
        f"{followup_request.payload['exposure_time']} {filter_value['i']} "
        f"{followup_request.payload['priority']} {followup_request.payload['station_name']}\n\r"
        f'"{public_source.id}" {public_source.ra} {public_source.dec} {date_second_scene.isoformat(timespec="milliseconds")} '
        f"0.004180983 0.00 "
        f"{followup_request.payload['exposure_time']} {filter_value['g']} "
        f"{followup_request.payload['exposure_time']} {filter_value['r']} "
        f"{followup_request.payload['exposure_time']} {filter_value['i']} "
        f"0 0 "
        f"0 0 "
        f"0 0 "
        f"{followup_request.payload['priority']} {followup_request.payload['station_name']}\n\r"
    )

    # Test with 13 exposure counts by filter with 1 filter
    followup_request.payload["exposure_counts"] = 13
    followup_request.payload["filters"] = ["g"]
    observation_strings = create_request_string(
        followup_request.obj,
        followup_request.payload,
        Time(followup_request.payload["date"], format="isot"),
        followup_request.payload["station_name"],
    )

    date_first_scene = datetime.strptime(
        followup_request.payload["date"], "%Y-%m-%dT%H:%M:%S.%f"
    )
    date_second_scene = date_first_scene + timedelta(
        seconds=(followup_request.payload["exposure_time"] + 45) * 6
    )
    date_third_scene = date_second_scene + timedelta(
        seconds=(followup_request.payload["exposure_time"] + 45) * 6
    )

    assert observation_strings == (
        f'"{public_source.id}" {public_source.ra} {public_source.dec} {date_first_scene.isoformat(timespec="milliseconds")} '
        f"0.004180983 0.00 "
        f"{followup_request.payload['exposure_time']} {filter_value['g']} "
        f"{followup_request.payload['exposure_time']} {filter_value['g']} "
        f"{followup_request.payload['exposure_time']} {filter_value['g']} "
        f"{followup_request.payload['exposure_time']} {filter_value['g']} "
        f"{followup_request.payload['exposure_time']} {filter_value['g']} "
        f"{followup_request.payload['exposure_time']} {filter_value['g']} "
        f"{followup_request.payload['priority']} {followup_request.payload['station_name']}\n\r"
        f'"{public_source.id}" {public_source.ra} {public_source.dec} {date_second_scene.isoformat(timespec="milliseconds")} '
        f"0.004180983 0.00 "
        f"{followup_request.payload['exposure_time']} {filter_value['g']} "
        f"{followup_request.payload['exposure_time']} {filter_value['g']} "
        f"{followup_request.payload['exposure_time']} {filter_value['g']} "
        f"{followup_request.payload['exposure_time']} {filter_value['g']} "
        f"{followup_request.payload['exposure_time']} {filter_value['g']} "
        f"{followup_request.payload['exposure_time']} {filter_value['g']} "
        f"{followup_request.payload['priority']} {followup_request.payload['station_name']}\n\r"
        f'"{public_source.id}" {public_source.ra} {public_source.dec} {date_third_scene.isoformat(timespec="milliseconds")} '
        f"0.004180983 0.00 "
        f"{followup_request.payload['exposure_time']} {filter_value['g']} "
        f"0 0 "
        f"0 0 "
        f"0 0 "
        f"0 0 "
        f"0 0 "
        f"{followup_request.payload['priority']} {followup_request.payload['station_name']}\n\r"
    )
