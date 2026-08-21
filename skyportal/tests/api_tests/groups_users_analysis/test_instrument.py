import os
import time
import uuid

import pandas as pd
import pytest
from regions import Regions
from skyportal_py import SkyPortalError
from skyportal_py.instruments import InstrumentPost, InstrumentPut
from skyportal_py.telescopes import TelescopePost

from skyportal.tests import api, client


def test_token_user_post_get_instrument(super_admin_token):
    sp = client(super_admin_token)
    name = str(uuid.uuid4())
    telescope_id = sp.post_telescope(
        TelescopePost(
            name=name,
            nickname=name,
            lat=0.0,
            lon=0.0,
            elevation=0.0,
            diameter=10.0,
        )
    ).id

    fielddatafile = f"{os.path.dirname(__file__)}/../../../../data/ZTF_Fields.csv"
    regionsdatafile = f"{os.path.dirname(__file__)}/../../../../data/ZTF_Region.reg"

    instrument_name = str(uuid.uuid4())
    instrument_id = sp.post_instrument(
        InstrumentPost(
            name=instrument_name,
            type="imager",
            band="NIR",
            filters=["f110w"],
            telescope_id=telescope_id,
            field_data=pd.read_csv(fielddatafile)[:5].to_dict(orient="list"),
            field_region=Regions.read(regionsdatafile).serialize(format="ds9"),
        )
    ).id

    # wait for the fields to populate
    nretries = 0
    fields_loaded = False
    while not fields_loaded and nretries < 5:
        try:
            instrument = sp.fetch_instrument(instrument_id, include_geojson=True)
            assert instrument.band == "NIR"
            assert len(instrument.fields) == 5
            fields_loaded = True
        except AssertionError:
            nretries = nretries + 1
            time.sleep(3)

    instrument_id = instrument.id
    instrument = sp.fetch_instrument(instrument_id, include_geojson=True)
    assert instrument.band == "NIR"

    assert len(instrument.fields) == 5

    assert any(
        d.field_id == 1
        and d.contour["features"][0]["geometry"]["coordinates"][0][0]
        == [110.84791974982103, -87.01522999646508]
        for d in instrument.fields
    )

    instrument_id = instrument.id
    instrument = sp.fetch_instrument(instrument_id, include_geojson_summary=True)
    assert instrument.band == "NIR"

    assert len(instrument.fields) == 5

    assert any(
        d.field_id == 1
        and d.contour_summary["features"][0]["geometry"]["coordinates"][0]
        == [1.0238351746164418, -89.93777511600825]
        for d in instrument.fields
    )


def test_fetch_instrument_by_name(super_admin_token):
    sp = client(super_admin_token)
    tel_name = str(uuid.uuid4())
    telescope_id = sp.post_telescope(
        TelescopePost(
            name=tel_name,
            nickname=tel_name,
            lat=0.0,
            lon=0.0,
            elevation=0.0,
            diameter=10.0,
        )
    ).id

    instrument_name = str(uuid.uuid4())
    instrument_id = sp.post_instrument(
        InstrumentPost(
            name=instrument_name,
            type="imager",
            band="V",
            telescope_id=telescope_id,
        )
    ).id

    matches = sp.fetch_instruments(name=instrument_name)
    assert len(matches) == 1
    assert matches[0].band == "V"
    assert matches[0].id == instrument_id
    assert matches[0].name == instrument_name


def test_token_user_update_instrument(
    super_admin_token, manage_sources_token, view_only_token
):
    sp = client(super_admin_token)
    name = str(uuid.uuid4())
    telescope_id = sp.post_telescope(
        TelescopePost(
            name=name,
            nickname=name,
            lat=0.0,
            lon=0.0,
            elevation=0.0,
            diameter=10.0,
        )
    ).id

    instrument_name = str(uuid.uuid4())
    instrument_id = sp.post_instrument(
        InstrumentPost(
            name=instrument_name,
            type="imager",
            band="NIR",
            filters=["f110w"],
            telescope_id=telescope_id,
        )
    ).id

    assert sp.fetch_instrument(instrument_id).band == "NIR"

    new_name = f"Gattini2_{uuid.uuid4()}"

    with pytest.raises(SkyPortalError) as err:
        client(manage_sources_token).update_instrument(
            instrument_id,
            InstrumentPut(
                name=new_name,
                type="imager",
                band="NIR",
                filters=["f110w"],
                telescope_id=telescope_id,
            ),
        )
    assert err.value.status_code == 401

    sp.update_instrument(
        instrument_id,
        InstrumentPut(
            name=new_name,
            type="imager",
            band="NIR",
            filters=["f110w"],
            telescope_id=telescope_id,
        ),
    )

    assert client(view_only_token).fetch_instrument(instrument_id).name == new_name


def test_update_instrument_across_id(super_admin_token):
    # Regression: PUT-updating an instrument must not 500 with greenlet_spawn.
    # The instrument is given a region so the update exercises both async
    # lazy-load traps: the deferred `region` column and the load_instance
    # schema's sync instance fetch.
    sp = client(super_admin_token)
    name = str(uuid.uuid4())
    telescope_id = sp.post_telescope(
        TelescopePost(name=name, nickname=name, diameter=0.0, fixed_location=False)
    ).id

    instrument_id = sp.post_instrument(
        InstrumentPost(
            name=str(uuid.uuid4()),
            type="imager",
            filters=["f110w"],
            telescope_id=telescope_id,
            field_fov_type="circle",
            field_fov_attributes=3.0,
        )
    ).id

    across_id = str(uuid.uuid4())
    sp.update_instrument(instrument_id, InstrumentPut(across_id=across_id))

    assert sp.fetch_instrument(instrument_id).across_id == across_id


def test_token_user_delete_instrument(super_admin_token, view_only_token):
    sp = client(super_admin_token)
    name = str(uuid.uuid4())
    telescope_id = sp.post_telescope(
        TelescopePost(
            name=name,
            nickname=name,
            lat=0.0,
            lon=0.0,
            elevation=0.0,
            diameter=10.0,
        )
    ).id

    instrument_name = str(uuid.uuid4())
    instrument_id = sp.post_instrument(
        InstrumentPost(
            name=instrument_name,
            type="imager",
            band="NIR",
            filters=["f110w"],
            telescope_id=telescope_id,
        )
    ).id

    sp.delete_instrument(instrument_id)

    with pytest.raises(SkyPortalError) as err:
        client(view_only_token).fetch_instrument(instrument_id)
    assert err.value.status_code == 400


def test_post_instrument_fov(super_admin_token):
    sp = client(super_admin_token)
    telescope_name = str(uuid.uuid4())
    telescope_id = sp.post_telescope(
        TelescopePost(
            name=telescope_name,
            nickname=telescope_name,
            lat=0.0,
            lon=0.0,
            elevation=0.0,
            diameter=10.0,
        )
    ).id

    instrument_name = str(uuid.uuid4())
    instrument_id = sp.post_instrument(
        InstrumentPost(
            name=instrument_name,
            type="imager",
            band="NIR",
            filters=["f110w"],
            telescope_id=telescope_id,
            field_fov_type="circle",
            field_fov_attributes=3.0,
        )
    ).id

    # wait for the fields to populate
    nretries = 0
    fields_loaded = False
    while not fields_loaded and nretries < 5:
        try:
            instrument = sp.fetch_instrument(instrument_id, include_region=True)
            assert instrument.band == "NIR"
            fields_loaded = True
        except AssertionError:
            nretries = nretries + 1
            time.sleep(3)

    region_str = """# Region file format: DS9 astropy/regions
icrs
circle(0.00000000,0.00000000,3.00000000)"""

    assert instrument.region.strip() == region_str.strip()


def test_token_user_post_sensitivity_data(super_admin_token):
    sp = client(super_admin_token)
    name = str(uuid.uuid4())
    telescope_id = sp.post_telescope(
        TelescopePost(
            name=name,
            nickname=name,
            lat=0.0,
            lon=0.0,
            elevation=0.0,
            diameter=10.0,
        )
    ).id

    instrument_name = str(uuid.uuid4())
    with pytest.raises(SkyPortalError) as err:
        sp.post_instrument(
            InstrumentPost(
                name=instrument_name,
                type="imager",
                band="NIR",
                filters=["f110w"],
                sensitivity_data={
                    "wrong_filter_name": {
                        "limiting_magnitude": 20.5,
                        "magsys": "ab",
                        "exposure_time": 30,
                    }
                },
                telescope_id=telescope_id,
            )
        )
    assert err.value.status_code == 400
    assert (
        str(err.value)
        == "Sensitivity_data filters must be a subset of the instrument filters"
    )


def test_instrument_forms_api_classname_reads_telescope(super_admin_token):
    """Regression: GET /api/internal/instrument_forms?apiType=api_classname must
    not raise MissingGreenlet. ZTFAPI.custom_json_schema reads
    instrument.telescope (next_twilight_morning_nautical), which lazy-loads under
    the async handler unless the telescope relationship is eager-loaded.
    """
    sp = client(super_admin_token)
    name = str(uuid.uuid4())
    telescope_id = sp.post_telescope(
        TelescopePost(
            name=name,
            nickname=name,
            lat=0.0,
            lon=0.0,
            elevation=0.0,
            diameter=10.0,
        )
    ).id

    instrument_name = str(uuid.uuid4())
    instrument_id = sp.post_instrument(
        InstrumentPost(
            name=instrument_name,
            type="imager",
            band="optical",
            filters=["ztfg"],
            telescope_id=telescope_id,
            api_classname="ZTFAPI",
        )
    ).id

    # raw api: internal form-schema endpoint, outside skyportal-py's scope
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
