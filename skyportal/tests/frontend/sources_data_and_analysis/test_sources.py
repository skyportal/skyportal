import time
import uuid

import arrow
import numpy as np
from astropy.time import Time

from skyportal.tests import api


def test_sources_include_detection_stats(
    upload_data_token,
    super_admin_token,
    public_group,
    public_group2,
    upload_data_token_two_groups,
    view_only_token,
):
    obj_id = str(uuid.uuid4())
    status, data = api(
        "POST",
        "sources",
        data={
            "id": obj_id,
            "ra": 234.22,
            "dec": -22.33,
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["data"]["id"] == obj_id

    name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "telescope",
        data={
            "name": name,
            "nickname": name,
            "lat": 0.0,
            "lon": 0.0,
            "elevation": 0.0,
            "diameter": 10.0,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    telescope_id = data["data"]["id"]

    instrument_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "instrument",
        data={
            "name": instrument_name,
            "type": "imager",
            "band": "NIR",
            "filters": ["ztfg"],
            "telescope_id": telescope_id,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    instrument_id = data["data"]["id"]

    # Some very high mjd to make this the latest point
    # This is not a detection though
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": obj_id,
            "mjd": 99999.0,
            "instrument_id": instrument_id,
            "mag": None,
            "magerr": None,
            "limiting_mag": 22.3,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    # Another high mjd, but this time a photometry point not visible to the user
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": obj_id,
            "mjd": 99900.0,
            "instrument_id": instrument_id,
            "mag": None,
            "magerr": None,
            "limiting_mag": 22.3,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group2.id],
        },
        token=upload_data_token_two_groups,
    )
    assert status == 200
    assert data["status"] == "success"

    # let the phot_stats table update
    time.sleep(10)

    # A high mjd, but lower than the first point
    # Since this is a detection, it should be returned as "last_detected"
    status, data = api(
        "POST",
        "photometry",
        data={
            "obj_id": obj_id,
            "mjd": 90000.0,
            "instrument_id": instrument_id,
            "flux": 12.24,
            "fluxerr": 0.031,
            "zp": 25.0,
            "magsys": "ab",
            "filter": "ztfg",
            "group_ids": [public_group.id],
        },
        token=upload_data_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "PUT",
        f"sources/{obj_id}/phot_stat",
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api(
        "GET",
        "sources",
        params={"includeDetectionStats": "true"},
        token=view_only_token,
    )
    assert status == 200
    assert data["status"] == "success"

    # Note: 40_587 is the MJD of UNIX time 1970-01-01
    # Because arrow.get views dates as seconds since UNIX time,
    # s["peak_detected_at"]` is the MJD of 90000 in isodate format.

    # In summary: arrow.get("1970-01-01") - datetime.timedelta(40587) =>
    # <Arrow [1858-11-17T00:00:00+00:00]>

    assert any(
        arrow.get(Time(s["photstats"][-1]["last_detected_mjd"], format="mjd").datetime)
        == arrow.get((90000.0 - 40_587) * 86400.0)
        for s in data["data"]["sources"]
    )
    assert any(
        arrow.get(Time(s["photstats"][-1]["peak_mjd_global"], format="mjd").datetime)
        == arrow.get((90000.0 - 40_587) * 86400.0)
        for s in data["data"]["sources"]
    )

    assert any(
        np.isclose(s["photstats"][-1]["last_detected_mag"], 22.280546455476145)
        if s["photstats"][-1]["last_detected_mag"] is not None
        else False
        for s in data["data"]["sources"]
    )
    assert any(
        np.isclose(s["photstats"][-1]["peak_mag_global"], 22.280546455476145)
        if s["photstats"][-1]["peak_mag_global"] is not None
        else False
        for s in data["data"]["sources"]
    )
