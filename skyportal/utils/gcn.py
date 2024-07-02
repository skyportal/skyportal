# Inspired by https://github.com/growth-astro/growth-too-marshal/blob/main/growth/too/gcn.py

import base64
import os
import tempfile
import urllib
from urllib.parse import urlparse

import astropy.units as u
import gcn
import healpy as hp
import ligo.skymap.bayestar as ligo_bayestar
import ligo.skymap.distance
import ligo.skymap.io
import ligo.skymap.moc
import ligo.skymap.postprocess
import numpy as np
import requests
import scipy
from astropy.coordinates import ICRS, Angle, Latitude, Longitude, SkyCoord
from astropy.table import Table
from astropy.time import Time
from astropy_healpix import HEALPix, nside_to_level, pixel_resolution_to_nside
from mocpy import MOC

SKYMAP_MIN = 1e-300


def get_trigger(root):
    """Get the trigger ID from a GCN notice."""

    elem = None
    property_names = ["TrigID", "Burst_Id"]
    for property_name in property_names:
        path = f".//Param[@name='{property_name}']"
        elem_path = root.find(path)
        if elem_path is not None:
            elem = elem_path
            break

    if elem is None:
        return None

    value = elem.attrib.get('value', None)
    if value is not None:
        value = str(value)

    return value


def get_dateobs(root):
    """Get the UTC event time from a GCN notice, rounded to the nearest second,
    as a datetime.datetime object."""

    t0 = root.find(
        "./WhereWhen/{*}ObsDataLocation"
        "/{*}ObservationLocation"
        "/{*}AstroCoords"
        "[@coord_system_id='UTC-FK5-GEO']"
        "/Time/TimeInstant/ISOTime"
    )
    if t0 is None:
        t0 = root.find(
            "./WhereWhen/{*}ObsDataLocation"
            "/{*}ObservationLocation"
            "/{*}AstroCoords"
            "[@coord_system_id='UTC-ICRS-GEO']"
            "/Time/TimeInstant/ISOTime"
        )
    if t0 is None:
        return None

    dateobs = Time(
        t0.text,
        precision=0,
    )
    # FIXME: https://github.com/astropy/astropy/issues/7179
    dateobs = Time(dateobs.iso)

    return dateobs.datetime


def get_json_tags(payload):
    tags = []
    if "instrument" in payload:
        if payload["instrument"] == "WXT":
            tags = ["Einstein Probe"]
        elif payload["instrument"] == "BAT-GUANO":
            tags = ["GUANO"]

    return tags


def get_tags(root):
    """Get source classification tag strings from GCN notice."""
    # Get event stream.
    mission = urlparse(root.attrib['ivorn']).path.lstrip('/')
    if str(mission).lower().strip() == 'fsc':
        mission = 'SVOM'
    yield mission

    # What type of burst is this: GRB or GW?
    try:
        value = root.find("./Why/Inference/Concept").text
    except AttributeError:
        pass
    else:
        if value == 'process.variation.burst;em.gamma':
            # Is this a GRB at all?
            try:
                value = root.find(".//Param[@name='GRB_Identified']").attrib['value']
            except AttributeError:
                yield 'GRB'
            else:
                if value == 'false':
                    yield 'Not GRB'
                else:
                    yield 'GRB'
        elif value == 'process.variation.trans;em.gamma':
            yield 'transient'

    # LIGO/Virgo alerts don't provide the Why/Inference/Concept tag,
    # so let's just identify it as a GW event based on the notice type.
    notice_type = gcn.get_notice_type(root)
    if notice_type in {
        gcn.NoticeType.LVC_PRELIMINARY,
        gcn.NoticeType.LVC_INITIAL,
        gcn.NoticeType.LVC_UPDATE,
        gcn.NoticeType.LVC_RETRACTION,
    }:
        yield 'GW'
    elif notice_type in {
        gcn.NoticeType.ICECUBE_ASTROTRACK_GOLD,
        gcn.NoticeType.ICECUBE_ASTROTRACK_BRONZE,
    }:
        yield 'Neutrino'
        yield 'IceCube'

    if notice_type == gcn.NoticeType.ICECUBE_ASTROTRACK_GOLD:
        yield 'Gold'
    elif notice_type == gcn.NoticeType.ICECUBE_ASTROTRACK_BRONZE:
        yield 'Bronze'

    # Is this a retracted LIGO/Virgo event?
    if notice_type == gcn.NoticeType.LVC_RETRACTION:
        yield 'retracted'

    # Is this a short GRB, or a long GRB?
    try:
        value = root.find(".//Param[@name='Long_short']").attrib['value']
    except AttributeError:
        pass
    else:
        if value != 'unknown':
            yield value.lower()

    # Gaaaaaah! Alerts of type FERMI_GBM_SUBTHRESH store the
    # classification in a different property!
    try:
        value = root.find(".//Param[@name='Duration_class']").attrib['value'].title()
    except AttributeError:
        pass
    else:
        if value != 'unknown':
            yield value.lower()

    # Get LIGO/Virgo source classification, if present.
    classifications = [
        (float(elem.attrib['value']), elem.attrib['name'])
        for elem in root.iterfind("./What/Group[@type='Classification']/Param")
    ]
    if classifications:
        _, classification = max(classifications)
        yield classification

    search = root.find("./What/Param[@name='Search']")
    if search is not None:
        yield search.attrib['value']

    # Get instruments if present.
    try:
        value = root.find(".//Param[@name='Instruments']").attrib['value']
    except AttributeError:
        pass
    else:
        instruments = value.split(",")
        yield from instruments
        if len(instruments) > 1:
            yield "MultiInstrument"

    # Get instrument if present
    try:
        value = root.find(".//Param[@name='Instrument']").attrib['value']
    except AttributeError:
        pass
    else:
        yield value

    # Get pipeline if present.
    try:
        value = root.find(".//Param[@name='Pipeline']").attrib['value']
    except AttributeError:
        pass
    else:
        yield value

    # Get significant tag if present
    try:
        value = int(root.find(".//Param[@name='Significant']").attrib['value'])
    except AttributeError:
        pass
    else:
        if value == 1:
            yield "Significant"
        else:
            yield "Subthreshold"

    # Check for Swift losing tracking
    try:
        lost_lock = root.find(
            "./What/Group[@name='Solution_Status']/Param[@name='StarTrack_Lost_Lock']"
        ).attrib['value']
    except AttributeError:
        pass
    else:
        if lost_lock is not None:
            if lost_lock == "true":
                yield "StarTrack_Lost_Lock"


def get_notice_aliases(root, notice_type):
    aliases = []
    try:
        # we try to find aliases in the notice itself, which the user can update on the frontend by fetching data from TACH
        if notice_type in [
            gcn.NoticeType.FERMI_GBM_FIN_POS,
            gcn.NoticeType.FERMI_GBM_FLT_POS,
            gcn.NoticeType.FERMI_GBM_GND_POS,
        ]:
            url = root.find("./What/Param[@name='LightCurve_URL']").attrib['value']
            alias = url.split('/triggers/')[1].split('/')[1].split('/')[0]
            aliases.append(f"FERMI#{alias}")

        # we try the LVC convention
        graceid = root.find("./What/Param[@name='GraceID']")
        if graceid is not None:
            aliases.append(f"LVC#{graceid.attrib['value']}")
    except Exception as e:
        print(f"Could not find aliases in notice: {str(e)}")
        pass

    return aliases


def get_skymap_url(root, notice_type, timeout=10):
    url = None
    available = False

    if isinstance(root, dict):
        url = root.get('url')
    else:
        if notice_type == gcn.NoticeType.LVC_PRELIMINARY:
            # we set a longer timeout here, as by experience the LVC Preliminary skymaps can be a little slow to appear
            if timeout < 15:
                timeout = 15
        # Try Fermi GBM convention
        if notice_type == gcn.NoticeType.FERMI_GBM_FIN_POS:
            url = root.find("./What/Param[@name='LocationMap_URL']").attrib['value']
            url = url.replace('http://', 'https://')
            url = url.replace('_locplot_', '_healpix_')
            url = url.replace('.png', '.fit')

        # Try Fermi GBM **subthreshold** convention. Stupid, stupid, stupid!!
        if notice_type == gcn.NoticeType.FERMI_GBM_SUBTHRESH:
            url = root.find("./What/Param[@name='HealPix_URL']").attrib['value']

        # Try LVC convention
        skymap = root.find("./What/Group[@type='GW_SKYMAP']")
        if skymap is not None and url is None:
            children = skymap.getchildren()
            for child in children:
                if child.attrib['name'] == 'skymap_fits':
                    url = child.attrib['value']
                    break

    if url is not None:
        # we have a URL, but is it available? We don't want to download the file here,
        # so we'll just check the HTTP status code.
        try:
            response = requests.head(url, timeout=timeout, allow_redirects=True)
            if response.status_code == 200:
                available = True
        except requests.exceptions.RequestException:
            pass

    return url, available


def is_retraction(root):
    if isinstance(root, dict):
        retraction = root.get('retraction')
        if retraction:
            return True
    else:
        retraction = root.find("./What/Param[@name='Retraction']")
        if retraction is not None:
            retraction = int(retraction.attrib['value'])
            if retraction == 1:
                return True

    return False


def get_skymap_cone(root):
    ra, dec, error = None, None, None

    if isinstance(root, dict):
        if "coincident_events" in root:
            for coincident_event in root["coincident_events"]:
                if "localization" in coincident_event:
                    ra = coincident_event["localization"].get("ra")
                    dec = coincident_event["localization"].get("dec")
                    error = coincident_event["localization"].get("ra_dec_error")
                    break
        else:
            ra = root.get("ra")
            dec = root.get("dec")
            error = root.get("ra_dec_error")
    else:
        mission = urlparse(root.attrib['ivorn']).path.lstrip('/')
        # Try error cone
        loc = root.find('./WhereWhen/ObsDataLocation/ObservationLocation')
        if loc is None:
            return ra, dec, error

        ra = loc.find('./AstroCoords/Position2D/Value2/C1')
        dec = loc.find('./AstroCoords/Position2D/Value2/C2')
        error = loc.find('./AstroCoords/Position2D/Error2Radius')

        if None in (ra, dec, error):
            return ra, dec, error

        ra, dec, error = float(ra.text), float(dec.text), float(error.text)

        # Apparently, all experiments *except* AMON report a 1-sigma error radius.
        # AMON reports a 90% radius, so for AMON, we have to convert.
        if mission == 'AMON':
            error /= scipy.stats.chi(df=2).ppf(0.95)

    return ra, dec, error


def get_skymap_metadata(root, notice_type, url_timeout=10):
    """Get the skymap for a GCN notice."""

    if isinstance(root, dict):
        if 'healpix_file' in root:
            return "healpix_file", root['healpix_file']
    else:
        skymap_url, available = get_skymap_url(root, notice_type, timeout=url_timeout)
        if skymap_url is not None and available:
            return "available", {"url": skymap_url, "name": skymap_url.split("/")[-1]}
        elif skymap_url is not None and not available:
            return "unavailable", {"url": skymap_url, "name": skymap_url.split("/")[-1]}

    if is_retraction(root):
        return "retraction", None

    ra, dec, error = get_skymap_cone(root)
    if None not in (ra, dec, error):
        return "cone", {
            "ra": ra,
            "dec": dec,
            "error": error,
            "name": f"{ra:.5f}_{dec:.5f}_{error:.5f}",
        }

    return "missing", None


def has_skymap(root, notice_type, url_timeout=10):
    """Does this GCN notice have a skymap?"""
    status, _ = get_skymap_metadata(root, notice_type, url_timeout)
    return status in ("available", "cone", "unavailable", "healpix_file")


def get_skymap(root, notice_type, url_timeout=10):
    """Get the skymap for a GCN notice."""
    status, skymap_metadata = get_skymap_metadata(root, notice_type, url_timeout)

    if status == "available":
        skymap, properties, tags = from_url(skymap_metadata["url"])
        return skymap, skymap_metadata["url"], properties, tags
    elif status == "cone":
        return (
            from_cone(
                ra=skymap_metadata["ra"],
                dec=skymap_metadata["dec"],
                error=skymap_metadata["error"],
            ),
            None,
            None,
            None,
        )
    elif status == "healpix_file":
        skymap, properties, tags = from_bytes(skymap_metadata)
        skymap['localization_name'] = "healpix"
        return skymap, None, properties, tags
    else:
        return None, None, None, None


def get_properties(root):
    property_names = [
        # Gravitational waves
        "HasNS",
        "HasRemnant",
        "HasMassGap",
        "FAR",
        "BNS",
        "NSBH",
        "BBH",
        "MassGap",
        "Terrestrial",
        # GRBs
        "Burst_Signif",
        "Data_Signif",
        "Det_Signif",
        "Image_Signif",
        "Rate_Signif",
        "Trig_Signif",
        "Burst_Inten",
        "Burst_Peak",
        "Data_Timescale",
        "Data_Integ",
        "Integ_Time",
        "Trig_Timescale",
        "Trig_Dur",
        "Hardness_Ratio",
        # Neutrinos
        "signalness",
        "energy",
        # SVOM
        "SNR",
        "Mean_Flux",
        "Flux_Error",
        "Lower_Energy_Bound",
        "Upper_Energy_Bound",
    ]
    property_dict = {}
    for property_name in property_names:
        path = f".//Param[@name='{property_name}']"
        elem = root.find(path)
        if elem is None:
            continue
        value = elem.attrib.get('value', None)
        if value is not None:
            value = float(value.strip('>='))
            property_dict[property_name] = value

    tags_list = []
    if 'FAR' in property_dict:
        thresholds = [1, 100]
        for threshold in thresholds:
            if property_dict['FAR'] * (365 * 86400) <= threshold:
                if threshold == 1:
                    tags_list.append("< 1 per year")
                else:
                    tags_list.append(f"< 1 per {threshold} years")

    # Get instruments if present.
    try:
        value = root.find(".//Param[@name='Instruments']").attrib['value']
    except AttributeError:
        pass
    else:
        instruments = value.split(",")
        property_dict["num_instruments"] = len(instruments)

    return property_dict, tags_list


def from_cone(ra, dec, error, n_sigma=4):
    localization_name = f"{ra:.5f}_{dec:.5f}_{error:.5f}"

    center = SkyCoord(ra * u.deg, dec * u.deg)
    radius = error * u.deg

    # Determine resolution such that there are at least
    # 16 pixels across the error radius.
    hpx = HEALPix(
        pixel_resolution_to_nside(radius / 16, round='up'), 'nested', frame=ICRS()
    )

    # Find all pixels in the 4-sigma error circle.
    ipix = hpx.cone_search_skycoord(center, n_sigma * radius)

    # Convert to multi-resolution pixel indices and sort.
    uniq = ligo.skymap.moc.nest2uniq(nside_to_level(hpx.nside), ipix.astype(np.int64))
    i = np.argsort(uniq)
    ipix = ipix[i]
    uniq = uniq[i]

    # Evaluate Gaussian.
    distance = hpx.healpix_to_skycoord(ipix).separation(center)
    probdensity = np.exp(
        -0.5 * np.square(distance / radius).to_value(u.dimensionless_unscaled)
    )
    probdensity /= probdensity.sum() * hpx.pixel_area.to_value(u.steradian)

    skymap = {
        'localization_name': localization_name,
        'uniq': uniq.tolist(),
        'probdensity': probdensity.tolist(),
    }

    return skymap


def from_polygon(localization_name, polygon):
    xyz = [hp.ang2vec(r, d, lonlat=True) for r, d in polygon]
    ipix = None
    nside = 1024  # order 10
    while nside < 2**30:  # until order 29
        try:
            hpx = HEALPix(nside, 'nested', frame=ICRS())
            ipix = hp.query_polygon(hpx.nside, np.array(xyz), nest=True)
        except Exception:
            nside *= 2
            continue
        if ipix is None or len(ipix) == 0:
            nside *= 2
        else:
            break

    if ipix is None or len(ipix) == 0:
        raise ValueError("No pixels found in polygon.")

    # Convert to multi-resolution pixel indices and sort.
    uniq = ligo.skymap.moc.nest2uniq(nside_to_level(hpx.nside), ipix.astype(np.int64))
    i = np.argsort(uniq)
    ipix = ipix[i]
    uniq = uniq[i]

    # Evaluate Gaussian.
    probdensity = np.ones(ipix.shape)
    probdensity /= probdensity.sum() * hpx.pixel_area.to_value(u.steradian)

    skymap = {
        'localization_name': localization_name,
        'uniq': uniq.tolist(),
        'probdensity': probdensity.tolist(),
    }

    return skymap


def from_ellipse(localization_name, ra, dec, amaj, amin, phi):
    max_depth = 10
    NSIDE = int(2**max_depth)
    hpx = HEALPix(NSIDE, 'nested', frame=ICRS())
    ipix = MOC.from_elliptical_cone(
        lon=Longitude(ra, u.deg),
        lat=Latitude(dec, u.deg),
        a=Angle(amaj, unit="deg"),
        b=Angle(amin, unit="deg"),
        pa=Angle(np.mod(phi, 180.0), unit="deg"),
        max_depth=max_depth,
    ).flatten()

    # Convert to multi-resolution pixel indices and sort.
    uniq = ligo.skymap.moc.nest2uniq(nside_to_level(NSIDE), ipix.astype(np.int64))
    i = np.argsort(uniq)
    ipix = ipix[i]
    uniq = uniq[i]

    probdensity = np.ones(ipix.shape)
    probdensity /= probdensity.sum() * hpx.pixel_area.to_value(u.steradian)

    skymap = {
        'localization_name': localization_name,
        'uniq': uniq.tolist(),
        'probdensity': probdensity.tolist(),
    }

    return skymap


def from_bytes(arr):
    def get_col(m, name):
        try:
            col = m[name]
        except KeyError:
            return None
        else:
            return col.tolist()

    with tempfile.NamedTemporaryFile(suffix=".fits.gz", mode="wb") as f:
        arrSplit = arr.split('base64,')
        filename = arrSplit[0].split("name=")[-1].replace(";", "")
        # the localization name might contain things like '%2B' for '+', or '%3A' for ':'
        # make sure that these are converted to the correct characters
        filename = urllib.parse.unquote(filename)
        f.write(base64.b64decode(arrSplit[-1]))
        f.flush()

        skymap = ligo.skymap.io.read_sky_map(f.name, moc=True)

        idx = np.where(skymap['PROBDENSITY'] < SKYMAP_MIN)[0]
        skymap['PROBDENSITY'][idx] = 0

        properties_dict, tags_list = properties_tags_from_meta(skymap.meta)

        nside = 128
        occulted = get_occulted(f.name, nside=nside)
        if occulted is not None:
            order = hp.nside2order(nside)
            skymap_flat = ligo_bayestar.rasterize(skymap, order)['PROB']
            skymap_flat = hp.reorder(skymap_flat, 'NESTED', 'RING')
            skymap_flat[occulted] = 0.0
            skymap_flat = skymap_flat / skymap_flat.sum()
            skymap_flat = hp.reorder(skymap_flat, 'RING', 'NESTED')
            skymap = ligo_bayestar.derasterize(Table([skymap_flat], names=['PROB']))

        skymap = {
            'localization_name': filename,
            'uniq': get_col(skymap, 'UNIQ'),
            'probdensity': get_col(skymap, 'PROBDENSITY'),
            'distmu': get_col(skymap, 'DISTMU'),
            'distsigma': get_col(skymap, 'DISTSIGMA'),
            'distnorm': get_col(skymap, 'DISTNORM'),
        }

    return skymap, properties_dict, tags_list


def get_occulted(url, nside=64):
    m = Table.read(url, format='fits')
    ra = m.meta.get('GEO_RA', None)
    dec = m.meta.get('GEO_DEC', None)
    error = m.meta.get('GEO_RAD', 67.5)

    if (ra is None) or (dec is None) or (error is None):
        return None

    center = SkyCoord(ra * u.deg, dec * u.deg)
    radius = error * u.deg

    hpx = HEALPix(nside, 'ring', frame=ICRS())

    # Find all pixels in the circle.
    ipix = hpx.cone_search_skycoord(center, radius)

    return ipix


def properties_tags_from_meta(meta):
    property_names = [
        # Gravitational waves
        "log_bci",
        "log_bsn",
        "distmean",
        "diststd",
    ]

    properties_dict = {}
    tags_list = []
    for property_name in property_names:
        if property_name in meta:
            properties_dict[property_name] = meta[property_name]

    # Distance stats
    if 'distmean' in properties_dict:
        thresholds = [150, 250]
        for threshold in thresholds:
            if properties_dict["distmean"] <= threshold:
                tags_list.append(f"< {threshold} Mpc")

    return properties_dict, tags_list


def from_url(url):
    def get_col(m, name):
        try:
            col = m[name]
        except KeyError:
            return None
        else:
            return col.tolist()

    filename = os.path.basename(urlparse(url).path)

    skymap = ligo.skymap.io.read_sky_map(url, moc=True)
    properties_dict, tags_list = properties_tags_from_meta(skymap.meta)

    idx = np.where(skymap['PROBDENSITY'] < SKYMAP_MIN)[0]
    skymap['PROBDENSITY'][idx] = 0

    nside = 128
    occulted = get_occulted(url, nside=nside)
    if occulted is not None:
        order = hp.nside2order(nside)
        skymap_flat = ligo_bayestar.rasterize(skymap, order)['PROB']
        skymap_flat = hp.reorder(skymap_flat, 'NESTED', 'RING')
        skymap_flat[occulted] = 0.0
        skymap_flat = skymap_flat / skymap_flat.sum()
        skymap_flat = hp.reorder(skymap_flat, 'RING', 'NESTED')
        skymap = ligo_bayestar.derasterize(Table([skymap_flat], names=['PROB']))

    skymap = {
        'localization_name': filename,
        'uniq': get_col(skymap, 'UNIQ'),
        'probdensity': get_col(skymap, 'PROBDENSITY'),
        'distmu': get_col(skymap, 'DISTMU'),
        'distsigma': get_col(skymap, 'DISTSIGMA'),
        'distnorm': get_col(skymap, 'DISTNORM'),
    }

    return skymap, properties_dict, tags_list


def get_contour(localization):
    # Calculate credible levels.
    prob = localization.flat_2d
    cls = 100 * ligo.skymap.postprocess.find_greedy_credible_levels(prob)

    # Construct contours and return as a GeoJSON feature collection.
    levels = [50, 90]
    paths = ligo.skymap.postprocess.contour(cls, levels, degrees=True, simplify=True)
    center = ligo.skymap.postprocess.posterior_max(prob)
    localization.contour = {
        'type': 'FeatureCollection',
        'features': [
            {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [center.ra.deg, center.dec.deg],
                },
                'properties': {'credible_level': 0},
            }
        ]
        + [
            {
                'type': 'Feature',
                'properties': {'credible_level': level},
                'geometry': {'type': 'MultiLineString', 'coordinates': path},
            }
            for level, path in zip(levels, paths)
        ],
    }

    return localization


def get_skymap_properties(localization):
    sky_map = localization.table

    properties_dict = {}
    tags_list = []
    try:
        result = ligo.skymap.postprocess.crossmatch(
            sky_map, contours=(0.9,), areas=(500,)
        )
    except Exception:
        return properties_dict, tags_list
    area = result.contour_areas[0]
    prob = result.area_probs[0]

    if not np.isnan(area):
        properties_dict["area_90"] = area
        thresholds = [200, 500, 1000]
        for threshold in thresholds:
            if properties_dict["area_90"] < threshold:
                tags_list.append(f"< {threshold} sq. deg.")
    if not np.isnan(prob):
        properties_dict["probability_500"] = prob
        if properties_dict["probability_500"] >= 0.9:
            tags_list.append("> 0.9 in 500 sq. deg.")

    return properties_dict, tags_list
