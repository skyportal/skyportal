import urllib.parse
from datetime import datetime
from io import StringIO

import numpy as np
import pandas as pd
import requests
import sqlalchemy as sa
from astropy.coordinates import AltAz, SkyCoord, get_body
from astropy.time import Time

from baselayer.log import make_log
from skyportal.models import (
    InstrumentField,
    InstrumentFieldTile,
)
from skyportal.utils.calculations import (
    dms_to_deg,
    get_airmass,
    great_circle_distance_vec,
    hms_to_deg,
    radec_to_healpix,
)

from .cache import Cache, dict_to_bytes

cache_dir = "cache/moving_object_ephemeris"
cache = Cache(
    cache_dir=cache_dir,
    max_items=100,
)

log = make_log("api/moving_object")

# next we define some constants
BASE_URL = "https://ssd.jpl.nasa.gov"
COLUMN_NAMES = [
    "time",
    "solar_presence",
    "lunar_presence",
    "ra",
    "dec",
    "airmass",
    "mag_ex",
    "mag_ap",
    "drop1",
    "drop2",
]


def find_jplhorizon_obj(obj_name: str):
    """
    Find the object with the given name in the JPL Horizons database.

    Parameters
    ----------
    obj_name : str
        The name of the object to search for.

    Returns
    -------
    int
        The object ID of the object.
    """
    url = urllib.parse.urljoin(BASE_URL, f"/api/horizons_support.api")
    response = requests.get(url, params={"sstr": obj_name})
    if response.status_code != 200:
        raise ValueError(f"Failed to query JPL Horizons API: {response.text}")

    data = response.json()
    if data.get("count") == 0:
        raise ValueError(f"Failed to find object with name '{obj_name}'")
    elif data.get("count") > 1:
        raise ValueError(f"Found multiple objects with name '{obj_name}'")
    elif data.get("data") is None:
        raise ValueError(f"Failed to find object with name '{obj_name}'")
    elif "name" not in data.get("data"):
        raise ValueError(f"Failed to find object with name '{obj_name}'")
    elif (
        obj_name.lower()
        not in str(data.get("data").get("name")).replace(" ", "").lower()
    ):
        raise ValueError(
            f"Object found with name '{data['data']['name']}' does not match query '{obj_name}'"
        )

    return int(data["data"]["id"])


def get_ephemeris(
    obj_name: str,
    start_date: datetime,
    end_date: datetime,
    observer: AltAz,
    airmass_limit: float = 2,
    moon_distance_limit: float = 30,
    sun_altitude_limit: float = -18,
):
    """
    Get the ephemeris of the object with the given ID.

    Parameters
    ----------
    obj_name : str
        The object name in JPL Horizons.
    start_date : datetime
        The start date of the ephemeris.
    end_date : datetime
        The end date of the ephemeris.
    observer : AltAz
        The observer location.
    airmass_limit : float, optional
        Reject pointings below this airmass
    moon_distance_limit : float, optional
        Reject pointings closer than this distance to the moon, in degrees
    sun_altitude_limit : float, optional
        Reject pointings when the sun is above this altitude, in degrees

    Returns
    -------
    pd.DataFrame
        The ephemeris of the object.
    """
    lon, lat, alt = (
        observer.longitude.value,
        observer.latitude.value,
        observer.elevation.value,
    )

    url = urllib.parse.urljoin(BASE_URL, f"/api/horizons.api")
    start_time_str = start_date.strftime("%Y-%m-%d %H:%M")
    end_time_str = end_date.strftime("%Y-%m-%d %H:%M")

    cache_key = f"{obj_name}_{start_time_str}_{end_time_str}_{lon}_{lat}_{alt}"
    cached_data = cache[cache_key]
    if cached_data is not None:
        try:
            data = np.load(cached_data, allow_pickle=True).item()
        except Exception as e:
            log(f"Failed to load cached data: {e}")
            data = None

    if cached_data is None or data is None:
        obj_id = find_jplhorizon_obj(obj_name)
        params = {
            "COMMAND": f"'DES={obj_id}'",
            "OBJ_DATA": "'YES'",
            "MAKE_EPHEM": "'YES'",
            "EPHEM_TYPE": "'OBSERVER'",
            "CENTER": "'coord@399'",
            "SITE_COORD": f"'{float(lon)},{float(lat)},{int(alt / 1000)}'",  # Convert altitude to km
            "START_TIME": f"'{start_time_str}'",
            "STOP_TIME": f"'{end_time_str}'",
            "STEP_SIZE": "'1 MINUTES'",
            "COORD_TYPE": "GEODETIC",
            "QUANTITIES": "'1,8,9'",
            "CSV_FORMAT": "'YES'",
        }
        response = requests.get(url, params=params)
        if response.status_code != 200:
            raise ValueError(f"Failed to query JPL Horizons API: {response.text}")

        data = response.json()
        if "error" in data:
            raise ValueError(f"Failed to get ephemeris: {data['error']}")
        cache[cache_key] = dict_to_bytes(data)

    data = data["result"].split("$$SOE")[1].split("$$EOE")[0].strip()

    data = pd.read_csv(StringIO(data), header=None, sep=",", names=COLUMN_NAMES)
    data = data.drop(
        columns=[
            "solar_presence",
            "lunar_presence",
            "drop1",
            "drop2",
            "mag_ex",
            "mag_ap",
        ]
    )
    data = data.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    data = data.replace("n.a.", np.nan)

    data["time"] = pd.to_datetime(data["time"], format="%Y-%b-%d %H:%M")
    data = data[data["time"] >= np.datetime64(start_date)]
    data = data[data["time"] <= np.datetime64(end_date)]

    data["ra"] = data["ra"].apply(hms_to_deg)
    data["dec"] = data["dec"].apply(dms_to_deg)
    data = data.sort_values("time")

    # Airmass constraint (using JPL horizons airmass)
    data["airmass"] = data["airmass"].astype(float)
    data = data[data["airmass"] < airmass_limit]

    # Moon separation constraint
    times = Time(data["time"])
    moon_coords = get_body("moon", times, observer.location)
    moon_ras, moon_decs = [], []
    for i in range(len(moon_coords)):
        moon_ras.append(moon_coords[i].ra.deg)
        moon_decs.append(moon_coords[i].dec.deg)
    moon_sep = great_circle_distance_vec(data["ra"], data["dec"], moon_ras, moon_decs)
    keep_idx = np.where(np.array(moon_sep) >= moon_distance_limit)[0]
    data = data.iloc[keep_idx]

    # Sun altitude constraint
    times = Time(data["time"])
    sun = get_body("sun", times, observer.location).transform_to(
        AltAz(obstime=times, location=observer.location)
    )
    sun_alt = sun.alt.deg
    keep_idx = np.where(np.array(sun_alt) < sun_altitude_limit)[0]
    data = data.iloc[keep_idx]

    # remove gaps (non consecutive observations)
    data = data.sort_values("time")
    data["time_diff"] = data["time"].diff()
    data["group"] = (data["time_diff"] > pd.Timedelta("1 min")).cumsum()
    data = data.groupby("group").filter(lambda x: len(x) > 1)
    data = data.drop(columns=["group", "airmass"])

    return data


def get_instrument_fields(
    row: pd.Series,
    instrument_id: int,
    instrument_name: str,
    session,
    primary_only: bool = False,
    references_only: bool = False,
):
    """
    Get the fields that the object is in for the given instrument.

    Parameters
    ----------
    row : pd.Series
        The row of the ephemeris dataframe.
    instrument_id : int
        The ID of the instrument.
    instrument_name : str
        The name of the instrument.
    session
        The database session.
    primary_only : bool, optional
        Whether to only consider primary fields.

    Returns
    -------
    List[dict]
        The fields that the object is in.
    """
    # TODO: account for positional uncertainties (currently not returned by JPL Horizons API call)
    conditions = [
        InstrumentFieldTile.instrument_id == instrument_id,
        InstrumentFieldTile.instrument_field_id == InstrumentField.id,
        InstrumentFieldTile.healpix.contains(row["healpix"]),
    ]
    if references_only:
        conditions.append(InstrumentField.reference_filters != "{}")
    stmt = sa.select(InstrumentField).where(sa.and_(*conditions))
    if primary_only and instrument_name == "ZTF":
        stmt = stmt.where(InstrumentField.field_id < 880)

    fields: list[InstrumentField] = session.scalars(
        stmt.order_by(InstrumentField.field_id.asc())
    ).all()
    return [{"field_id": f.field_id, "ra": f.ra, "dec": f.dec} for f in fields]


def add_instrument_fields(
    df: pd.DataFrame,
    instrument_id: int,
    instrument_name: str,
    session,
    observer: AltAz,
    primary_only: bool = False,
    airmass_limit: float = 2,
    moon_distance_limit: float = 30,
    references_only: bool = False,
):
    """
    Add to the dataframe the instrument field IDs that each pointings is in, and split the dataframe into field-based dataframes.

    Parameters
    ----------
    df : pd.DataFrame
        The dataframe containing the ephemeris.
    instrument_id : int
        The ID of the instrument.
    instrument_name : str
        The name of the instrument.
    session
        The database session.
    observer : AltAz
        The observer location.
    primary_only : bool, optional
        Whether to only consider primary fields.
    moon_distance_limit : float, optional
        Reject pointings closer than this distance to the moon, in degrees
    airmass_limit : float, optional
        Reject pointings below this airmass

    Returns
    -------
    List[pd.DataFrame], dict
        The list of dataframes containing the ephemeris for each field, and the field ID to coordinates mapping.
    """
    df["healpix"] = df.apply(radec_to_healpix, axis=1)
    df["instrument_field_ids"] = None

    field_id_to_coords = {}
    for idx, row in df.iterrows():
        fields = get_instrument_fields(
            row,
            instrument_id,
            instrument_name,
            session,
            primary_only=primary_only,
            references_only=references_only,
        )
        if len(fields) > 0:
            df.at[idx, "instrument_field_ids"] = [f["field_id"] for f in fields]
            for f in fields:
                if f["field_id"] not in field_id_to_coords:
                    field_id_to_coords[f["field_id"]] = (f["ra"], f["dec"])

    df = df.dropna(subset=["instrument_field_ids"])

    # split the dataframe into N dataframes where N is the number of unique field ids
    dfs = []
    unique_field_ids = df["instrument_field_ids"].explode().unique()
    for field_id in unique_field_ids:
        field_ra, field_dec = field_id_to_coords[field_id]

        mask = df["instrument_field_ids"].apply(lambda x: field_id in x)
        df_temp: pd.DataFrame = df[mask].copy()
        df_temp = df_temp.drop(columns=["instrument_field_ids"])
        df_temp["instrument_field_id"] = field_id

        # moon separation constraint
        df_temp_times = Time(df_temp["time"])
        moon_coords = get_body("moon", df_temp_times, observer.location)
        moon_ras, moon_decs = [], []
        for i in range(len(moon_coords)):
            moon_ras.append(moon_coords[i].ra.deg)
            moon_decs.append(moon_coords[i].dec.deg)
        field_moon_seps = great_circle_distance_vec(
            field_ra, field_dec, moon_ras, moon_decs
        )
        keep_idx = np.where(np.array(field_moon_seps) >= moon_distance_limit)[0]
        df_temp = df_temp.iloc[keep_idx]

        # airmass constraint (we need to compute the airmass for each observation, i.e. at the ra, dec of the field)
        field_airmass = get_airmass(
            fields=[{"ra": field_ra, "dec": field_dec, "field_id": field_id}],
            time=df_temp_times,
            observer=observer,
        )[0]
        df_temp["airmass"] = field_airmass
        df_temp = df_temp[df_temp["airmass"] < airmass_limit]

        # make sure that it is ordered by time
        df_temp = df_temp.sort_values("time")

        df_temp["time_diff"] = df_temp["time"].diff()
        df_temp["group"] = (df_temp["time_diff"] > pd.Timedelta("1 min")).cumsum()
        df_temp = df_temp.groupby("group").filter(lambda x: len(x) > 1)
        df_temp = df_temp.drop(columns=["group", "healpix"])

        # reset the index
        df_temp = df_temp.reset_index(drop=True)

        if len(df_temp) > 0:
            dfs.append(df_temp)

    return dfs, field_id_to_coords


def count_consecutive(df: pd.DataFrame):
    """
    Count the number of consecutive observations in the dataframe.

    Parameters
    ----------
    df : pd.DataFrame
        The dataframe containing the ephemeris.

    Returns
    -------
    pd.DataFrame
        The dataframe with the count of consecutive observations.
    """
    df["count"] = 1
    last_field_id = None
    count = 1
    for idx, row in df.iterrows():
        if row["instrument_field_id"] == last_field_id and (
            row["time_diff"] == pd.Timedelta("1 min") or pd.isna(row["time_diff"])
        ):
            count += 1
        else:
            count = 1
        last_field_id = row["instrument_field_id"]
        df.loc[idx, "count"] = count
    return df


def find_longest_sequence(df: pd.DataFrame):
    """
    Find the longest sequence of consecutive observations in the dataframe.

    Parameters
    ----------
    df : pd.DataFrame
        The dataframe containing the ephemeris.

    Returns
    -------
    datetime, datetime, int, int
        The start time, end time, field ID, and count of the longest sequence.
    """
    max_count_idx = df["count"].idxmax()
    max_count = df["count"].max()
    start_time = df.loc[max_count_idx - max_count + 1, "time"]
    end_time = df.loc[max_count_idx, "time"]
    field = df.loc[max_count_idx, "instrument_field_id"]
    return start_time, end_time, field, max_count


def find_observable_sequence(
    dfs: list[pd.DataFrame],
    field_id_to_radec: dict,
    observer: AltAz,
    nb_obs: int,
    obs_time: int,
    band: str = None,
):
    """
    Find the longest sequence of consecutive observations in the dataframes, and return the sequence of observations to be made.

    Parameters
    ----------
    dfs : List[pd.DataFrame]
        The dataframes containing the ephemeris.
    nb_obs : int
        The number of observations to make.
    obs_time : int
        The exposure time of each observation.
    band : str, optional
        The band to observe in.

    Returns
    -------
    List[dict]
        The sequence of observations to make
    """
    if len(dfs) == 0:
        return []

    start_time, end_time, field, max_count = None, None, None, 0
    for df in dfs:
        df = count_consecutive(df)
        s, e, f, c = find_longest_sequence(df)
        if c > max_count:
            start_time, end_time, field, max_count = s, e, f, c

    observations = []
    if end_time - start_time >= pd.Timedelta(seconds=obs_time * nb_obs):
        midpoint = start_time + (end_time - start_time) / 2
        start_time_sequence = midpoint - pd.Timedelta(seconds=obs_time * nb_obs / 2)
        midpoint = start_time + (end_time - start_time) / 2
        for i in range(nb_obs):
            start_time_obs = start_time_sequence + pd.Timedelta(seconds=obs_time * i)
            end_time_obs = start_time_sequence + pd.Timedelta(
                seconds=obs_time * (i + 1)
            )
            airmass_obs = get_airmass(
                fields=[
                    {
                        "ra": field_id_to_radec[field][0],
                        "dec": field_id_to_radec[field][1],
                        "field_id": field,
                    }
                ],
                time=Time([start_time_obs]),
                observer=observer,
            )[0][0]
            sun_alt = (
                get_body("sun", Time(start_time_obs), observer.location)
                .transform_to(
                    AltAz(obstime=Time(start_time_obs), location=observer.location)
                )
                .alt.deg
            )
            moon: SkyCoord = get_body("moon", Time(start_time_obs), observer.location)
            moon_sep = great_circle_distance_vec(
                field_id_to_radec[field][0],
                field_id_to_radec[field][1],
                moon.ra.deg,
                moon.dec.deg,
            )
            observations.append(
                {
                    "start_time": start_time_obs,
                    "end_time": end_time_obs,
                    "band": band,
                    "field_id": int(field),
                    "airmass": float(airmass_obs),
                    "sun_altitude": float(sun_alt),
                    "moon_distance": float(moon_sep),
                }
            )

    return observations
