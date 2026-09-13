import os
import time
import uuid

import astropy.units as u
import pandas as pd
from astropy.coordinates import SkyCoord
from regions import RectangleSkyRegion, Regions

from skyportal.tests import api


def test_token_user_post_get_instrument(super_admin_token):
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

    fielddatafile = f"{os.path.dirname(__file__)}/../../../../data/ZTF_Fields.csv"
    regionsdatafile = f"{os.path.dirname(__file__)}/../../../../data/ZTF_Region.reg"

    instrument_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "instrument",
        data={
            "name": instrument_name,
            "type": "imager",
            "band": "NIR",
            "filters": ["f110w"],
            "telescope_id": telescope_id,
            "field_data": pd.read_csv(fielddatafile)[:5].to_dict(orient="list"),
            "field_region": Regions.read(regionsdatafile).serialize(format="ds9"),
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    instrument_id = data["data"]["id"]

    params = {"includeGeoJSON": True}

    # wait for the fields to populate
    nretries = 0
    fields_loaded = False
    while not fields_loaded and nretries < 5:
        try:
            status, data = api(
                "GET",
                f"instrument/{instrument_id}",
                params=params,
                token=super_admin_token,
            )
            assert status == 200
            assert data["status"] == "success"
            assert data["data"]["band"] == "NIR"
            assert len(data["data"]["fields"]) == 5
            fields_loaded = True
        except AssertionError:
            nretries = nretries + 1
            time.sleep(3)

    params = {"includeGeoJSON": True}

    instrument_id = data["data"]["id"]
    status, data = api(
        "GET", f"instrument/{instrument_id}", params=params, token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["band"] == "NIR"

    assert len(data["data"]["fields"]) == 5

    assert any(
        d["field_id"] == 1
        and d["contour"]["features"][0]["geometry"]["coordinates"][0][0]
        == [110.84791974982103, -87.01522999646508]
        for d in data["data"]["fields"]
    )

    params = {"includeGeoJSONSummary": True}

    instrument_id = data["data"]["id"]
    status, data = api(
        "GET", f"instrument/{instrument_id}", params=params, token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["band"] == "NIR"

    assert len(data["data"]["fields"]) == 5

    assert any(
        d["field_id"] == 1
        and d["contour_summary"]["features"][0]["geometry"]["coordinates"][0]
        == [1.0238351746164418, -89.93777511600825]
        for d in data["data"]["fields"]
    )


def test_fetch_instrument_by_name(super_admin_token):
    tel_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "telescope",
        data={
            "name": tel_name,
            "nickname": tel_name,
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
            "band": "V",
            "telescope_id": telescope_id,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    instrument_id = data["data"]["id"]
    status, data = api(
        "GET", f"instrument?name={instrument_name}", token=super_admin_token
    )
    assert status == 200
    assert data["status"] == "success"
    assert len(data["data"]) == 1
    assert data["data"][0]["band"] == "V"
    assert data["data"][0]["id"] == instrument_id
    assert data["data"][0]["name"] == instrument_name


def test_token_user_update_instrument(
    super_admin_token, manage_sources_token, view_only_token
):
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
            "filters": ["f110w"],
            "telescope_id": telescope_id,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    instrument_id = data["data"]["id"]
    status, data = api("GET", f"instrument/{instrument_id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["band"] == "NIR"

    new_name = f"Gattini2_{uuid.uuid4()}"

    status, data = api(
        "PUT",
        f"instrument/{instrument_id}",
        data={
            "name": new_name,
            "type": "imager",
            "band": "NIR",
            "filters": ["f110w"],
            "telescope_id": telescope_id,
        },
        token=manage_sources_token,
    )
    assert status == 403
    assert data["status"] == "error"

    status, data = api(
        "PUT",
        f"instrument/{instrument_id}",
        data={
            "name": new_name,
            "type": "imager",
            "band": "NIR",
            "filters": ["f110w"],
            "telescope_id": telescope_id,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"instrument/{instrument_id}", token=view_only_token)
    assert status == 200
    assert data["status"] == "success"
    assert data["data"]["name"] == new_name


def test_update_instrument_across_id(super_admin_token):
    # Regression: PUT-updating an instrument must not 500 with greenlet_spawn.
    # The instrument is given a region so the update exercises both async
    # lazy-load traps: the deferred `region` column and the load_instance
    # schema's sync instance fetch.
    name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "telescope",
        data={"name": name, "nickname": name, "diameter": 0.0, "fixed_location": False},
        token=super_admin_token,
    )
    assert status == 200
    telescope_id = data["data"]["id"]

    status, data = api(
        "POST",
        "instrument",
        data={
            "name": str(uuid.uuid4()),
            "type": "imager",
            "filters": ["f110w"],
            "telescope_id": telescope_id,
            "field_fov_type": "circle",
            "field_fov_attributes": 3.0,
        },
        token=super_admin_token,
    )
    assert status == 200
    instrument_id = data["data"]["id"]

    across_id = str(uuid.uuid4())
    status, data = api(
        "PUT",
        f"instrument/{instrument_id}",
        data={"across_id": across_id},
        token=super_admin_token,
    )
    assert status == 200, data
    assert data["status"] == "success"

    status, data = api("GET", f"instrument/{instrument_id}", token=super_admin_token)
    assert status == 200
    assert data["data"]["across_id"] == across_id


def test_token_user_delete_instrument(super_admin_token, view_only_token):
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
            "filters": ["f110w"],
            "telescope_id": telescope_id,
        },
        token=super_admin_token,
    )

    assert status == 200
    assert data["status"] == "success"
    instrument_id = data["data"]["id"]

    status, data = api("DELETE", f"instrument/{instrument_id}", token=super_admin_token)
    assert status == 200
    assert data["status"] == "success"

    status, data = api("GET", f"instrument/{instrument_id}", token=view_only_token)
    assert status == 400


def test_post_instrument_fov(super_admin_token):
    telescope_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "telescope",
        data={
            "name": telescope_name,
            "nickname": telescope_name,
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
            "filters": ["f110w"],
            "telescope_id": telescope_id,
            "field_fov_type": "circle",
            "field_fov_attributes": 3.0,
        },
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    instrument_id = data["data"]["id"]

    params = {"includeRegion": True}

    # wait for the fields to populate
    nretries = 0
    fields_loaded = False
    while not fields_loaded and nretries < 5:
        try:
            status, data = api(
                "GET",
                f"instrument/{instrument_id}",
                token=super_admin_token,
                params=params,
            )
            assert status == 200
            assert data["status"] == "success"
            assert data["data"]["band"] == "NIR"
            fields_loaded = True
        except AssertionError:
            nretries = nretries + 1
            time.sleep(3)

    assert status == 200
    assert data["status"] == "success"

    region_str = """# Region file format: DS9 astropy/regions
icrs
circle(0.00000000,0.00000000,3.00000000)"""

    assert data["data"]["region"].strip() == region_str.strip()


def test_token_user_post_sensitivity_data(super_admin_token):
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
            "filters": ["f110w"],
            "sensitivity_data": {
                "wrong_filter_name": {
                    "limiting_magnitude": 20.5,
                    "magsys": "ab",
                    "exposure_time": 30,
                }
            },
            "telescope_id": telescope_id,
        },
        token=super_admin_token,
    )
    assert status == 400
    assert data["status"] == "error"
    assert (
        "Sensitivity_data filters must be a subset of the instrument filters"
        in data["message"]
    )


def test_instrument_forms_api_classname_reads_telescope(super_admin_token):
    """Regression: GET /api/internal/instrument_forms?apiType=api_classname must
    not raise MissingGreenlet. ZTFAPI.custom_json_schema reads
    instrument.telescope (next_twilight_morning_nautical), which lazy-loads under
    the async handler unless the telescope relationship is eager-loaded.
    """
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
    telescope_id = data["data"]["id"]

    instrument_name = str(uuid.uuid4())
    status, data = api(
        "POST",
        "instrument",
        data={
            "name": instrument_name,
            "type": "imager",
            "band": "optical",
            "filters": ["ztfg"],
            "telescope_id": telescope_id,
            "api_classname": "ZTFAPI",
        },
        token=super_admin_token,
    )
    assert status == 200
    instrument_id = data["data"]["id"]

    status, data = api(
        "GET",
        "internal/instrument_forms",
        params={"apiType": "api_classname"},
        token=super_admin_token,
    )
    assert status == 200
    assert data["status"] == "success"
    # The ZTFAPI instrument's form schema is built (via custom_json_schema, which
    # reads instrument.telescope) rather than crashing with MissingGreenlet.
    assert str(instrument_id) in data["data"]
    assert data["data"][str(instrument_id)]["formSchema"] is not None


def _span(field):
    """RA and Dec extent of a field's contour, in degrees."""
    coords = field["contour"]["features"][0]["geometry"]["coordinates"][0]
    ras = [c[0] for c in coords]
    decs = [c[1] for c in coords]
    return max(ras) - min(ras), max(decs) - min(decs)


def test_field_rotation_rolls_the_footprint(super_admin_token):
    """A survey that rolls between pointings turns its footprint, not just moves it.

    TESS is the case that needs this: its cameras roll every sector, so one
    shared orientation cannot describe them.
    """
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
    assert status == 200, data
    telescope_id = data["data"]["id"]

    # An oblong footprint, so a quarter turn is unmistakable.
    region = RectangleSkyRegion(
        center=SkyCoord(0 * u.deg, 0 * u.deg), width=4 * u.deg, height=1 * u.deg
    )

    status, data = api(
        "POST",
        "instrument",
        data={
            "name": str(uuid.uuid4()),
            "type": "imager",
            "band": "Optical",
            "filters": ["ztfg"],
            "telescope_id": telescope_id,
            "field_data": {
                "ID": [1, 2],
                "RA": [100.0, 100.0],
                "Dec": [0.0, 0.0],
                "rotation": [0.0, 90.0],
            },
            "field_region": Regions([region]).serialize(format="ds9"),
        },
        token=super_admin_token,
    )
    assert status == 200, data
    instrument_id = data["data"]["id"]

    fields = []
    for _ in range(5):
        status, data = api(
            "GET",
            f"instrument/{instrument_id}",
            params={"includeGeoJSON": True},
            token=super_admin_token,
        )
        assert status == 200, data
        fields = data["data"]["fields"]
        if len(fields) == 2:
            break
        time.sleep(3)
    assert len(fields) == 2, fields

    by_id = {field["field_id"]: field for field in fields}
    unrolled_ra, unrolled_dec = _span(by_id[1])
    rolled_ra, rolled_dec = _span(by_id[2])

    # Unrolled the box is wide in RA; a quarter turn makes it tall in Dec.
    assert unrolled_ra > 3.5 and unrolled_dec < 1.5
    assert rolled_dec > 3.5 and rolled_ra < 1.5
