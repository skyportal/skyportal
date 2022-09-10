import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
import healpy as hp

from penquins import Kowalski

from baselayer.app.env import load_env

env, cfg = load_env()


def tesselation_spiral(FOV, scale=0.80):
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

    ras, decs = tesselation_spiral(radius, scale=0.80)
    coords_dict_list = list({"ra": r, "dec": d} for r, d in zip(ras, decs))
    coords_out = select_sources_in_level(coords_dict_list, skymap, level=level)
    ra_out = np.array(list(c["ra"] for c in coords_out))
    dec_out = np.array(list(c["dec"] for c in coords_out))

    return ra_out, dec_out


def select_sources_in_level(sources, skymap, level=0.95):

    i = np.flipud(np.argsort(skymap))
    sorted_credible_levels = np.cumsum(skymap[i])
    credible_levels = np.empty_like(sorted_credible_levels)
    credible_levels[i] = sorted_credible_levels
    npix = len(skymap)
    nside = hp.npix2nside(npix)
    sources_within = list(
        s
        for s in sources
        if (
            credible_levels[
                hp.ang2pix(
                    nside, 0.5 * np.pi - np.deg2rad(s["dec"]), np.deg2rad(s["ra"])
                )
            ]
            <= level
        )
    )

    return sources_within


def select_sources_in_contour(sources, skymap, level=90):
    """Check that the selected sources lie within a given integrated
    probability of the skymap usinng the pixels directly"""

    skymap_prob = skymap.flat_2d
    sort_idx = np.argsort(skymap_prob)[::-1]
    csm = np.empty(len(skymap_prob))
    csm[sort_idx] = np.cumsum(skymap_prob[sort_idx])
    ipix_keep = sort_idx[np.where(csm <= level / 100.0)[0]]
    nside = hp.pixelfunc.get_nside(skymap_prob)
    sources_contour = list(
        s
        for s in sources
        if ("ra" in s)
        and (
            hp.ang2pix(
                nside,
                0.5 * np.pi - np.deg2rad(s["dec"].value),
                np.deg2rad(s["ra"].value),
            )
            in ipix_keep
        )
    )

    return sources_contour


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
    '''Query kowalski and apply the selection criteria'''

    TIMEOUT = 180
    k = Kowalski(
        token=token,
        protocol=cfg['app.ztf.protocol'],
        host=cfg['app.ztf.host'],
        port=cfg['app.ztf.port'],
        verbose=False,
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
                if r['data'] == []:
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

        set_objectId = set(objectId_list)

        # Remove those objects with negative subtraction
        for n in set(with_neg_sub):
            try:
                set_objectId.remove(n)
            except (ValueError, KeyError):
                pass

        # Remove stellar objects
        for n in set(stellar_list):
            try:
                set_objectId.remove(n)
            except (ValueError, KeyError):
                pass

        # Remove those objects considered old
        for n in set(old):
            try:
                set_objectId.remove(n)
            except (ValueError, KeyError):
                pass

        # Remove those objects whole alerts go bejond jd_trigger+max_days
        for n in set(out_of_time_window):
            try:
                set_objectId.remove(n)
            except (ValueError, KeyError):
                pass
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
    results = results_all['data']
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
