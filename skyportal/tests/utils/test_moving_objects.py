import astropy.units as u

from skyportal.models import DBSession
from skyportal.tests.external.test_moving_objects import add_telescope_and_instrument
from skyportal.utils.moving_objects import *


def test_find_jplhorizon_obj():
    obj = "2025BS6"
    id = find_jplhorizon_obj(obj)
    assert id == 54517721


def test_get_ephemeris():
    obj = "2025BS6"
    start_date = datetime(2025, 2, 7, 0, 0)
    end_date = datetime(2025, 2, 8, 0, 0)
    observer = Observer(
        longitude=-116.8361 * u.deg, latitude=33.3634 * u.deg, elevation=1870.0 * u.m
    )
    data = get_ephemeris(obj, start_date, end_date, observer)
    assert isinstance(data, pd.DataFrame)
    assert len(data) == 332
    assert "time" in data.columns
    assert "ra" in data.columns
    assert "dec" in data.columns
    assert "time_diff" in data.columns


def test_get_instrument_fields(super_admin_token):
    obj = "2025BS6"
    start_date = datetime(2025, 2, 7, 0, 0)
    end_date = datetime(2025, 2, 8, 0, 0)
    observer = Observer(
        longitude=-116.8361 * u.deg, latitude=33.3634 * u.deg, elevation=1870.0 * u.m
    )
    data = get_ephemeris(obj, start_date, end_date, observer)
    assert isinstance(data, pd.DataFrame)
    assert len(data) == 332

    data["healpix"] = data.apply(radec_to_healpix, axis=1)
    data["instrument_field_ids"] = None

    _, instrument_id, _, _ = add_telescope_and_instrument(
        "ZTF", super_admin_token, fields_ids=[364, 365, 366]
    )

    with DBSession() as session:
        row = data.iloc[75]

        fields = get_instrument_fields(
            row, instrument_id, "ZTF", session, primary_only=True
        )
        assert isinstance(fields, list)
        assert len(fields) == 1

        field = fields[0]
        assert isinstance(field, dict)
        assert "field_id" in field
        assert "ra" in field
        assert "dec" in field
        assert field["field_id"] == 364
        assert field["ra"] == 139.2275
        assert field["dec"] == -9.85


def test_add_instrument_fields(super_admin_token):
    obj = "2025BS6"
    start_date = datetime(2025, 2, 7, 0, 0)
    end_date = datetime(2025, 2, 8, 0, 0)
    observer = Observer(
        longitude=-116.8361 * u.deg, latitude=33.3634 * u.deg, elevation=1870.0 * u.m
    )
    data = get_ephemeris(obj, start_date, end_date, observer)

    data["healpix"] = data.apply(radec_to_healpix, axis=1)
    data["instrument_field_ids"] = None

    _, instrument_id, _, _ = add_telescope_and_instrument(
        "ZTF", super_admin_token, fields_ids=[364, 365, 366]
    )

    with DBSession() as session:
        dfs, field2radec = add_instrument_fields(
            data, instrument_id, "ZTF", session, observer, primary_only=True
        )
        print(field2radec)
        assert isinstance(dfs, list)
        assert len(dfs) == 2
        df = dfs[0]
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 10
        assert "instrument_field_id" in df.columns
        assert len(df["instrument_field_id"].unique()) == 1
        assert df["instrument_field_id"].unique()[0] == 364
        assert "airmass" in df.columns
        assert df["airmass"].max() <= 2.0
        assert df["airmass"].min() > 0.0

        assert isinstance(field2radec, dict)
        assert len(field2radec) == 2
        assert 364 in field2radec
        assert isinstance(field2radec[364], tuple)
        assert field2radec[364][0] == 139.2275
        assert field2radec[364][1] == -9.85


def test_count_consecutive(super_admin_token):
    obj = "2025BS6"
    start_date = datetime(2025, 2, 7, 0, 0)
    end_date = datetime(2025, 2, 8, 0, 0)
    observer = Observer(
        longitude=-116.8361 * u.deg, latitude=33.3634 * u.deg, elevation=1870.0 * u.m
    )
    data = get_ephemeris(obj, start_date, end_date, observer)

    data["healpix"] = data.apply(radec_to_healpix, axis=1)
    data["instrument_field_ids"] = None

    _, instrument_id, _, _ = add_telescope_and_instrument(
        "ZTF", super_admin_token, fields_ids=[364, 365, 366]
    )

    with DBSession() as session:
        dfs, _ = add_instrument_fields(
            data, instrument_id, "ZTF", session, observer, primary_only=True
        )
        df = dfs[0]

        df = count_consecutive(df)
        assert isinstance(df, pd.DataFrame)
        assert "count" in df.columns
        assert df["count"].min() == 1
        assert df["count"].max() == 6


def test_find_longest_sequence(super_admin_token):
    obj = "2025BS6"
    start_date = datetime(2025, 2, 7, 0, 0)
    end_date = datetime(2025, 2, 8, 0, 0)
    observer = Observer(
        longitude=-116.8361 * u.deg, latitude=33.3634 * u.deg, elevation=1870.0 * u.m
    )
    data = get_ephemeris(obj, start_date, end_date, observer)

    data["healpix"] = data.apply(radec_to_healpix, axis=1)
    data["instrument_field_ids"] = None

    _, instrument_id, _, _ = add_telescope_and_instrument(
        "ZTF", super_admin_token, fields_ids=[364, 365, 366]
    )

    with DBSession() as session:
        dfs, _ = add_instrument_fields(
            data, instrument_id, "ZTF", session, observer, primary_only=True
        )
        df = dfs[0]

        df = count_consecutive(df)
        start, end, field_id, count = find_longest_sequence(df)
        assert start == datetime(2025, 2, 7, 8, 54)
        assert end == datetime(2025, 2, 7, 8, 59)
        assert field_id == 364
        assert count == 6


def test_find_observable_sequence(super_admin_token):
    obj = "2025BS6"
    start_date = datetime(2025, 2, 7, 0, 0)
    end_date = datetime(2025, 2, 8, 0, 0)
    observer = Observer(
        longitude=-116.8361 * u.deg, latitude=33.3634 * u.deg, elevation=1870.0 * u.m
    )
    data = get_ephemeris(obj, start_date, end_date, observer)

    data["healpix"] = data.apply(radec_to_healpix, axis=1)
    data["instrument_field_ids"] = None

    _, instrument_id, _, _ = add_telescope_and_instrument(
        "ZTF", super_admin_token, fields_ids=[364, 365, 366]
    )

    with DBSession() as session:
        dfs, field_id_to_radec = add_instrument_fields(
            data, instrument_id, "ZTF", session, observer, primary_only=True
        )

        nb_obs = 3
        obs_time = 60
        band = "ztfr"
        observations = find_observable_sequence(
            dfs, field_id_to_radec, observer, nb_obs, obs_time, band=band
        )
        assert isinstance(observations, list)
        assert len(observations) == 3

        valid_obs = [
            {
                "start_time": datetime(2025, 2, 7, 8, 55),
                "end_time": datetime(2025, 2, 7, 8, 56),
                "band": "ztfr",
                "field_id": 364,
                "airmass": 1.43,
                "sun_altitude": -68.17,
                "moon_distance": 74.93,
            },
            {
                "start_time": datetime(2025, 2, 7, 8, 56),
                "end_time": datetime(2025, 2, 7, 8, 57),
                "band": "ztfr",
                "field_id": 364,
                "airmass": 1.43,
                "sun_altitude": -68.04,
                "moon_distance": 74.92,
            },
            {
                "start_time": datetime(2025, 2, 7, 8, 57),
                "end_time": datetime(2025, 2, 7, 8, 58),
                "band": "ztfr",
                "field_id": 364,
                "airmass": 1.43,
                "sun_altitude": -67.91,
                "moon_distance": 74.91,
            },
        ]

        for i, obs in enumerate(observations):
            for key, value in valid_obs[i].items():
                if isinstance(value, float):
                    assert np.isclose(obs[key], value, rtol=1e-2)
                else:
                    assert obs[key] == value
