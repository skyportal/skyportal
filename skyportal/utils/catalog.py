import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time
import healpy as hp
import pandas as pd
from penquins import Kowalski
import requests
import urllib

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
    coords_dict_list = list({"ra": r, "dec": d} for r, d in zip(ras, decs))
    coords_out = select_sources_in_level(coords_dict_list, skymap, level=level)
    ra_out = np.array(list(c["ra"] for c in coords_out))
    dec_out = np.array(list(c["dec"] for c in coords_out))

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


def query_kowalski(
    token,
    jd_trigger,
    ra_center,
    dec_center,
    radius=60.0,
    min_days=0.0,
    max_days=7.0,
    slices=10,
    ndethist_min=2,
    within_days=7.0,
    after_trigger=True,
    verbose=True,
):
    """Query kowalski and apply the selection criteria
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
    slices : int
        Number of slices for parallelizing the cone search. Defaults to 10.
    ndethist_min : int
        Minimum number of detections for an object. Defaults to 2.
    within_days : float
        The number of days to check for detections. Defaults to 7.
    after_trigger : bool
        Check for detections only after the trigger. Defaults to True.
    verbose : bool
        Kowalski verbosity. Defaults to False.
    """

    TIMEOUT = 180
    k = Kowalski(
        token=token,
        protocol=cfg['app.ztf.protocol'],
        host=cfg['app.ztf.host'],
        port=cfg['app.ztf.port'],
        verbose=verbose,
        timeout=TIMEOUT,
    )
    # Initialize a set for the results
    set_objectId_all = set()
    slices = slices + 1

    for slice_lim, i in zip(
        np.linspace(0, len(ra_center), slices)[:-1],
        np.arange(len(np.linspace(0, len(ra_center), slices)[:-1])),
    ):
        try:
            ra_center_slice = ra_center[
                int(slice_lim) : int(np.linspace(0, len(ra_center), slices)[:-1][i + 1])
            ]
            dec_center_slice = dec_center[
                int(slice_lim) : int(
                    np.linspace(0, len(dec_center), slices)[:-1][i + 1]
                )
            ]
        except IndexError:
            ra_center_slice = ra_center[int(slice_lim) :]
            dec_center_slice = dec_center[int(slice_lim) :]
        coords_arr = []
        for ra, dec in zip(ra_center_slice, dec_center_slice):
            try:
                # Remove points too far south for ZTF.
                # Say, keep only Dec>-40 deg to be conservative
                if dec < -40.0:
                    continue
                coords = SkyCoord(ra=float(ra) * u.deg, dec=float(dec) * u.deg)
                coords_arr.append((coords.ra.deg, coords.dec.deg))
            except ValueError:
                print("Problems with the galaxy coordinates?")
                continue

        # Correct the minimum number of detections
        ndethist_min_corrected = int(ndethist_min - 1)

        # Correct the jd_trigger if the user specifies to query
        # also before the trigger
        if after_trigger is False:
            jd_trigger = 0
        q = {
            "query_type": "cone_search",
            "query": {
                "object_coordinates": {
                    "radec": f"{coords_arr}",
                    "cone_search_radius": f"{radius}",
                    "cone_search_unit": "arcmin",
                },
                "catalogs": {
                    "ZTF_alerts": {
                        "filter": {
                            "candidate.jd": {'$gt': jd_trigger},
                            "candidate.drb": {'$gt': 0.8},
                            "candidate.ndethist": {'$gt': ndethist_min_corrected},
                            "candidate.jdstarthist": {
                                '$gt': jd_trigger,
                                '$lt': jd_trigger + within_days,
                            },
                        },
                        "projection": {
                            "objectId": 1,
                            "candidate.rcid": 1,
                            "candidate.ra": 1,
                            "candidate.dec": 1,
                            "candidate.jd": 1,
                            "candidate.ndethist": 1,
                            "candidate.jdstarthist": 1,
                            "candidate.jdendhist": 1,
                            "candidate.jdendhist": 1,
                            "candidate.magpsf": 1,
                            "candidate.sigmapsf": 1,
                            "candidate.fid": 1,
                            "candidate.programid": 1,
                            "candidate.isdiffpos": 1,
                            "candidate.ndethist": 1,
                            "candidate.ssdistnr": 1,
                            "candidate.rb": 1,
                            "candidate.drb": 1,
                            "candidate.distpsnr1": 1,
                            "candidate.sgscore1": 1,
                            "candidate.srmag1": 1,
                            "candidate.distpsnr2": 1,
                            "candidate.sgscore2": 1,
                            "candidate.srmag2": 1,
                            "candidate.distpsnr3": 1,
                            "candidate.sgscore3": 1,
                            "candidate.srmag3": 1,
                        },
                    }
                },
                "kwargs": {"hint": "gw01"},
            },
        }

        # Perform the query
        r = k.query(query=q)
        if not r.get("default").get("status", "error") == "success":
            raise ValueError("Query failed")

        objectId_list = []
        with_neg_sub = []
        old = []
        out_of_time_window = []
        stellar_list = []

        # Try to query kowalski up to 5 times
        i = 1
        no_candidates = False
        while i <= 5:
            try:
                if r.get("default").get("data") == []:
                    no_candidates = True
                keys_list = list(r['data']['ZTF_alerts'].keys())
                break
            except (AttributeError, KeyError, TypeError, ConnectionError):
                i += 1
        if i > 5:
            continue
        if no_candidates is True:
            continue
        for key in keys_list:
            all_info = r['data']['ZTF_alerts'][key]

            for info in all_info:
                if info['objectId'] in old:
                    continue
                if info['objectId'] in stellar_list:
                    continue
                if np.abs(info['candidate']['ssdistnr']) < 10:
                    continue
                if info['candidate']['isdiffpos'] in ['f', 0]:
                    with_neg_sub.append(info['objectId'])
                if (
                    info['candidate']['jdendhist'] - info['candidate']['jdstarthist']
                ) < min_days:
                    continue
                if (
                    info['candidate']['jdendhist'] - info['candidate']['jdstarthist']
                ) > max_days:
                    old.append(info['objectId'])
                if (info['candidate']['jdstarthist'] - jd_trigger) > within_days:
                    old.append(info['objectId'])
                # REMOVE!  Only for O3a paper
                # if (info['candidate']['jdendhist'] -
                # info['candidate']['jdstarthist']) >= 72./24. and info['candidate']['ndethist'] <= 2.:
                #    out_of_time_window.append(info['objectId'])
                if after_trigger is True:
                    if (info['candidate']['jdendhist'] - jd_trigger) > max_days:
                        out_of_time_window.append(info['objectId'])
                else:
                    if (
                        info['candidate']['jdendhist']
                        - info['candidate']['jdstarthist']
                    ) > max_days:
                        out_of_time_window.append(info['objectId'])
                try:
                    if (
                        np.abs(info['candidate']['distpsnr1']) < 1.5
                        and info['candidate']['sgscore1'] > 0.50
                    ):
                        stellar_list.append(info['objectId'])
                except (KeyError, ValueError):
                    pass
                try:
                    if (
                        np.abs(info['candidate']['distpsnr1']) < 15.0
                        and info['candidate']['srmag1'] < 15.0
                        and info['candidate']['srmag1'] > 0.0
                        and info['candidate']['sgscore1'] >= 0.5
                    ):
                        continue
                except (KeyError, ValueError):
                    pass
                try:
                    if (
                        np.abs(info['candidate']['distpsnr2']) < 15.0
                        and info['candidate']['srmag2'] < 15.0
                        and info['candidate']['srmag2'] > 0.0
                        and info['candidate']['sgscore2'] >= 0.5
                    ):
                        continue
                except (KeyError, ValueError):
                    pass
                try:
                    if (
                        np.abs(info['candidate']['distpsnr3']) < 15.0
                        and info['candidate']['srmag3'] < 15.0
                        and info['candidate']['srmag3'] > 0.0
                        and info['candidate']['sgscore3'] >= 0.5
                    ):
                        continue
                except (KeyError, ValueError):
                    pass

                objectId_list.append(info['objectId'])

        set_objectId = (
            set(objectId_list)
            - set(with_neg_sub)
            - set(stellar_list)
            - set(old)
            - set(out_of_time_window)
        )

        set_objectId_all = set_objectId_all | set_objectId

    q = {
        "query_type": "find",
        "query": {
            "catalog": "ZTF_alerts",
            "filter": {"objectId": {"$in": list(set_objectId_all)}},
            "projection": {
                "_id": 0,
                "candid": 1,
                "objectId": 1,
                "candidate.ra": 1,
                "candidate.dec": 1,
            },
        },
    }
    results_all = k.query(query=q)
    if not results_all.get("default").get("status", "error") == "success":
        raise ValueError("Query failed")
    results = results_all.get("default").get("data")
    sources = []
    for n in set_objectId_all:
        source = {}
        source["id"] = n
        source["ra"] = list(
            r["candidate"]["ra"] for r in results if r["objectId"] == n
        )[0]
        source["dec"] = list(
            r["candidate"]["dec"] for r in results if r["objectId"] == n
        )[0]
        sources.append(source)

    return sources


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

    time_min = Time(jd_trigger + min_days, format='jd')
    time_max = Time(jd_trigger + max_days, format='jd')

    sources = []
    sources_data = []
    for ra, dec in zip(ra_center, dec_center):
        r = requests.post(
            urllib.parse.urljoin(cfg['app.fink_endpoint'], 'api/v1/explorer'),
            json={
                'ra': ra,
                'dec': dec,
                'radius': 60 * radius,
                'startdate_conesearch': Time(jd_trigger + min_days, format='jd').iso,
                'window_days_conesearch': max_days,
            },
        )
        objs = pd.DataFrame(r.json())
        for index, obj in objs.iterrows():
            objectId = obj['i:objectId']
            ra_obj, dec_obj = obj['i:ra'], obj['i:dec']
            jdstarthist = obj['i:jdstarthist']
            jdendhist = obj['i:jdendhist']
            if (jdstarthist < time_min.jd) or (jdendhist > time_max.jd):
                continue
            if objectId in sources:
                continue
            df = query_fink_photometry(objectId)
            det = np.where(
                (~np.isnan(df['mag']))
                & (df['mjd'] >= time_min.mjd)
                & (df['mjd'] <= time_max.mjd)
            )[0]
            ndet = len(det)
            if ndet >= ndethist_min:
                sources.append(objectId)
                sources_data.append(
                    {'id': objectId, 'ra': ra_obj, 'dec': dec_obj, 'data': df}
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
        'i:jd',
        'i:ra',
        'i:dec',
        'i:magpsf',
        'i:sigmapsf',
        'i:diffmaglim',
        'i:magzpsci',
        'i:fid',
    }

    r = requests.post(
        urllib.parse.urljoin(cfg['app.fink_endpoint'], 'api/v1/objects'),
        json={'objectId': objectId, 'output-format': 'json'},
    )
    df = pd.DataFrame.from_dict(r.json())

    if not desired_columns.issubset(set(df.columns)):
        raise ValueError('Missing expected column')

    df.rename(
        columns={
            'i:jd': 'jd',
            'i:ra': 'ra',
            'i:dec': 'dec',
            'i:magpsf': 'mag',
            'i:sigmapsf': 'magerr',
            'i:diffmaglim': 'limiting_mag',
            'i:magzpsci': 'zp',
            'i:fid': 'filter',
        },
        inplace=True,
    )
    df['filter'] = [inv_bands[int(filt)] for filt in df['filter']]
    df['mjd'] = [Time(jd, format='jd').mjd for jd in df['jd']]

    columns_to_keep = ['mjd', 'ra', 'dec', 'mag', 'magerr', 'limiting_mag', 'filter']
    df = df[columns_to_keep]
    df['magsys'] = 'ab'

    return df
