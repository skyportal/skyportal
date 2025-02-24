import os
import time
import uuid

import arrow
import pandas as pd
import pytest
from regions import Regions

from skyportal.tests import api


def add_telescope_and_instrument(api_class, super_admin_token, fields_ids=[]):
    telescope_name = f"{api_class}_{str(uuid.uuid4())}"
    instrument_name = f"{api_class}_instr_{str(uuid.uuid4())}"

    status, data = api(
        "POST",
        "telescope",
        data={
            "name": telescope_name,
            "nickname": telescope_name,
            "lat": 33.3634,
            "lon": -116.8361,
            "elevation": 1870.0,
            "diameter": 1.2,
            "robotic": True,
            "fixed_location": True,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    telescope_id = data["data"]["id"]

    fielddatafile = f"{os.path.dirname(__file__)}/../../../data/ZTF_Fields.csv"
    regionsdatafile = f"{os.path.dirname(__file__)}/../../../data/ZTF_Square_Region.reg"

    field_data = pd.read_csv(fielddatafile)
    field_region = Regions.read(regionsdatafile).serialize(format="ds9")

    if isinstance(fields_ids, list):
        field_data = field_data[field_data["ID"].isin(fields_ids)]

    field_data = field_data.to_dict(orient="list")

    data = {
        "name": instrument_name,
        "type": "imager",
        "band": "Optical",
        "filters": ["ztfr"],
        "telescope_id": telescope_id,
        "api_classname": f"{api_class}API".upper(),
    }
    if api_class == "ZTF" and len(fields_ids) > 0:
        fielddatafile = f"{os.path.dirname(__file__)}/../../../data/ZTF_Fields.csv"
        regionsdatafile = (
            f"{os.path.dirname(__file__)}/../../../data/ZTF_Square_Region.reg"
        )

        field_data = pd.read_csv(fielddatafile)
        field_data = field_data[field_data["ID"].isin(fields_ids)].to_dict(
            orient="list"
        )
        field_region = Regions.read(regionsdatafile).serialize(format="ds9")

        data["api_classname_obsplan"] = "ZTFMMAAPI"
        data["field_data"] = field_data
        data["field_region"] = field_region

    status, data = api(
        "POST",
        "instrument",
        data=data,
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    instrument_id = data["data"]["id"]

    # wait for the fields to populate
    nretries = 0
    maxretries = 10
    while nretries < maxretries:
        try:
            status, data = api(
                "GET",
                f"instrument/{instrument_id}",
                token=super_admin_token,
                params={"ignoreCache": True, "includeGeoJSON": True},
            )
            assert status == 200
            assert data["status"] == "success"
            assert data["data"]["band"] == "Optical"
            if len(fields_ids) > 0:
                assert len(data["data"]["fields"]) == len(fields_ids)
            break
        except AssertionError:
            nretries = nretries + 1
            time.sleep(3)

    assert nretries < maxretries

    return telescope_id, instrument_id, telescope_name, instrument_name


# @pytest.mark.flaky(reruns=3)
def test_moving_object_followup(super_admin_token):
    moving_obj_id = "2025BS6"
    followup_start_time = arrow.get("2025-02-07 00:00:00")
    followup_end_time = arrow.get("2025-02-08 00:00:00")
    exposure_count = 3
    exposure_time = 60
    band = "ztfr"

    _, instrument_id, _, _ = add_telescope_and_instrument(
        "ZTF", super_admin_token, fields_ids=[364, 365, 366]
    )

    status, data = api(
        "POST",
        f"moving_object/{moving_obj_id}/followup",
        data={
            "instrument_id": instrument_id,
            "start_time": followup_start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": followup_end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "exposure_count": exposure_count,
            "exposure_time": exposure_time,
            "filter": band,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert "data" in data
    data = data["data"]
    assert isinstance(data, list)
    assert len(data) == exposure_count

    # verify that the field start and end times are valid
    prev_start_time = None
    for field in data:
        start_time = arrow.get(field["start_time"])
        end_time = arrow.get(field["end_time"])
        assert start_time < end_time
        if prev_start_time is not None:
            assert start_time >= prev_start_time
        else:
            assert start_time >= followup_start_time
        assert end_time <= followup_end_time
        prev_start_time = start_time

        field["band"] == band
