import urllib

import healpy as hp
import numpy as np
import pandas as pd
import requests
from astropy.time import Time

from baselayer.app.env import load_env
from skyportal.facility_apis.ztf import inv_bands

env, cfg = load_env()


def tesselation_spiral(FOV, scale=0.80):
    """Tile the sphere using circles, returning the center of those circles.
    FOV : float
        Radius of the circle (in degrees) with which to tile the sphere
    scale : float
        Degree of overlap between the circles tiling the sphere
    """

    FOV = np.pi * FOV * FOV * scale

    area_of_sphere = 4 * np.pi * (180 / np.pi) ** 2
    n = int(np.ceil(area_of_sphere / FOV))

    golden_angle = np.pi * (3 - np.sqrt(5))
    theta = golden_angle * np.arange(n)
    z = np.linspace(1 - 1.0 / n, 1.0 / n - 1, n)
    radius = np.sqrt(1 - z * z)

    points = np.zeros((n, 3))
    points[:, 0] = radius * np.cos(theta)
    points[:, 1] = radius * np.sin(theta)
    points[:, 2] = z

    ra, dec = hp.pixelfunc.vec2ang(points, lonlat=True)

    return ra, dec


def get_conesearch_centers(skymap, radius=1.0, level=0.95):
    """Return pointings for a set of cone searches inside a localization region.
    skymap : numpy.array
        Flattened 2D healpix skymap
    radius : float
        Radius of the circle (in degrees) with which to tile the sphere
    level : float
        Cumulative probability up to which to include points
    """

    ras, decs = tesselation_spiral(radius, scale=0.80)
    coords_dict_list = [{"ra": r, "dec": d} for r, d in zip(ras, decs)]
    coords_out = select_sources_in_level(coords_dict_list, skymap, level=level)
    ra_out = np.array([c["ra"] for c in coords_out])
    dec_out = np.array([c["dec"] for c in coords_out])

    return ra_out, dec_out


def select_sources_in_level(sources, skymap, level=0.95):
    """Return sources inside a localization region.
    sources : list of dict
        Sources to test for inside skymap
    skymap : numpy.array
        Flattened 2D healpix skymap
    level : float
        Cumulative probability up to which to include points
    """

    i = np.flipud(np.argsort(skymap))
    sorted_credible_levels = np.cumsum(skymap[i])
    credible_levels = np.empty_like(sorted_credible_levels)
    credible_levels[i] = sorted_credible_levels
    npix = len(skymap)
    nside = hp.npix2nside(npix)

    sources_within = []
    for s in sources:
        ipix = hp.ang2pix(
            nside, 0.5 * np.pi - np.deg2rad(s["dec"]), np.deg2rad(s["ra"])
        )
        if credible_levels[ipix] <= level:
            sources_within.append(s)

    return sources_within


def query_fink(
    jd_trigger,
    ra_center,
    dec_center,
    radius=60.0,
    min_days=0.0,
    max_days=7.0,
    ndethist_min=2,
    within_days=7.0,
    after_trigger=True,
    verbose=True,
):
    """Query Fink and apply the selection criteria
    token : str
        Kowalski token
    jd_trigger : float
        Time of the event (in JD)
    ra_center : list of float
        Right ascensions (in degrees) to use for cone search(es)
    dec_center : list of float
        Declinations (in degrees) to use for cone search(es)
    radius : float
        Radius (in arcminutes) for the cone search. Defaults to 60.
    min_days : float
        Time in days after trigger for first detection. Defaults to 0.
    max_days : float
        Time in days after trigger for final detection. Defaults to 7.
    ndethist_min : int
        Minimum number of detections for an object. Defaults to 2.
    within_days : float
        The number of days to check for detections. Defaults to 7.
    after_trigger : bool
        Check for detections only after the trigger. Defaults to True.
    verbose : bool
        Kowalski verbosity. Defaults to False.
    """

    time_min = Time(jd_trigger + min_days, format="jd")
    time_max = Time(jd_trigger + max_days, format="jd")

    sources = []
    sources_data = []
    for ra, dec in zip(ra_center, dec_center):
        r = requests.post(
            urllib.parse.urljoin(cfg["app.fink_endpoint"], "api/v1/explorer"),
            json={
                "ra": ra,
                "dec": dec,
                "radius": 60 * radius,
                "startdate_conesearch": Time(jd_trigger + min_days, format="jd").iso,
                "window_days_conesearch": max_days,
            },
        )
        objs = pd.DataFrame(r.json())
        for index, obj in objs.iterrows():
            objectId = obj["i:objectId"]
            ra_obj, dec_obj = obj["i:ra"], obj["i:dec"]
            jdstarthist = obj["i:jdstarthist"]
            jdendhist = obj["i:jd"]
            if (jdstarthist < time_min.jd) or (jdendhist > time_max.jd):
                continue
            if objectId in sources:
                continue
            df = query_fink_photometry(objectId)
            det = np.where(
                (~np.isnan(df["mag"]))
                & (df["mjd"] >= time_min.mjd)
                & (df["mjd"] <= time_max.mjd)
            )[0]
            ndet = len(det)
            if ndet >= ndethist_min:
                sources.append(objectId)
                sources_data.append(
                    {"id": objectId, "ra": ra_obj, "dec": dec_obj, "data": df}
                )

    return sources_data


def query_fink_photometry(objectId):
    """Fetch object photometry from Fink.
    objectId: str
        Object ID

    Returns
    -------
    df : pandas.DataFrame
        A dataframe with the object photometry
    """

    desired_columns = {
        "i:jd",
        "i:ra",
        "i:dec",
        "i:magpsf",
        "i:sigmapsf",
        "i:diffmaglim",
        "i:magzpsci",
        "i:fid",
    }

    r = requests.post(
        urllib.parse.urljoin(cfg["app.fink_endpoint"], "api/v1/objects"),
        json={"objectId": objectId, "output-format": "json"},
    )
    df = pd.DataFrame.from_dict(r.json())

    if not desired_columns.issubset(set(df.columns)):
        raise ValueError("Missing expected column")

    df.rename(
        columns={
            "i:jd": "jd",
            "i:ra": "ra",
            "i:dec": "dec",
            "i:magpsf": "mag",
            "i:sigmapsf": "magerr",
            "i:diffmaglim": "limiting_mag",
            "i:magzpsci": "zp",
            "i:fid": "filter",
        },
        inplace=True,
    )
    df["filter"] = [inv_bands[int(filt)] for filt in df["filter"]]
    df["mjd"] = [Time(jd, format="jd").mjd for jd in df["jd"]]

    columns_to_keep = ["mjd", "ra", "dec", "mag", "magerr", "limiting_mag", "filter"]
    df = df[columns_to_keep]
    df["magsys"] = "ab"

    return df
