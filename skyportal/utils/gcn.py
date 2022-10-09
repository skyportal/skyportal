# Inspired by https://github.com/growth-astro/growth-too-marshal/blob/main/growth/too/gcn.py

import base64
import os
import numpy as np
import scipy
import healpy as hp
import gcn
import tempfile
from urllib.parse import urlparse

import astropy.units as u
from astropy.time import Time
from astropy.coordinates import SkyCoord

from astropy.coordinates import ICRS
from astropy_healpix import HEALPix, nside_to_level, pixel_resolution_to_nside
import ligo.skymap.io
import ligo.skymap.postprocess
import ligo.skymap.moc

from skyportal.models.gcn import GcnEvent

import sqlalchemy as sa
import datetime
import lxml


SOURCE_RADIUS_THRESHOLD = 5.0 / 60.0  # 5 arcmin


def get_trigger(root):
    """Get the trigger ID from a GCN notice."""

    property_name = "TrigID"
    path = f".//Param[@name='{property_name}']"
    elem = root.find(path)
    if elem is None:
        return None
    value = elem.attrib.get('value', None)
    if value is not None:
        value = int(value)

    return value


def get_dateobs(root):
    """Get the UTC event time from a GCN notice, rounded to the nearest second,
    as a datetime.datetime object."""
    dateobs = Time(
        root.find(
            "./WhereWhen/{*}ObsDataLocation"
            "/{*}ObservationLocation"
            "/{*}AstroCoords"
            "[@coord_system_id='UTC-FK5-GEO']"
            "/Time/TimeInstant/ISOTime"
        ).text,
        precision=0,
    )

    # FIXME: https://github.com/astropy/astropy/issues/7179
    dateobs = Time(dateobs.iso)

    return dateobs.datetime


def get_tags(root):
    """Get source classification tag strings from GCN notice."""
    # Get event stream.
    mission = urlparse(root.attrib['ivorn']).path.lstrip('/')
    yield mission

    # What type of burst is this: GRB or GW?
    try:
        value = root.find("./Why/Inference/Concept").text
    except AttributeError:
        pass
    else:
        if value == 'process.variation.burst;em.gamma':
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

    # Get Instruments, if present.
    try:
        value = root.find(".//Param[@name='Instruments']").attrib['value']
    except AttributeError:
        pass
    else:
        instruments = value.split(",")
        yield from instruments


def get_skymap(root, gcn_notice):
    mission = urlparse(root.attrib['ivorn']).path.lstrip('/')

    # Try Fermi GBM convention
    if gcn_notice.notice_type == gcn.NoticeType.FERMI_GBM_FIN_POS:
        url = root.find("./What/Param[@name='LocationMap_URL']").attrib['value']
        url = url.replace('http://', 'https://')
        url = url.replace('_locplot_', '_healpix_')
        url = url.replace('.png', '.fit')
        return from_url(url)

    # Try Fermi GBM **subthreshold** convention. Stupid, stupid, stupid!!
    if gcn_notice.notice_type == gcn.NoticeType.FERMI_GBM_SUBTHRESH:
        url = root.find("./What/Param[@name='HealPix_URL']").attrib['value']
        return from_url(url)

    # Try LVC convention
    skymap = root.find("./What/Group[@type='GW_SKYMAP']")
    if skymap is not None:
        children = skymap.getchildren()
        for child in children:
            if child.attrib['name'] == 'skymap_fits':
                url = child.attrib['value']
                break

        return from_url(url)

    retraction = root.find("./What/Param[@name='Retraction']")
    if retraction is not None:
        retraction = int(retraction.attrib['value'])
        if retraction == 1:
            return None

    # Try error cone
    loc = root.find('./WhereWhen/ObsDataLocation/ObservationLocation')
    if loc is None:
        return None

    ra = loc.find('./AstroCoords/Position2D/Value2/C1')
    dec = loc.find('./AstroCoords/Position2D/Value2/C2')
    error = loc.find('./AstroCoords/Position2D/Error2Radius')

    if None in (ra, dec, error):
        return None

    ra, dec, error = float(ra.text), float(dec.text), float(error.text)

    # Apparently, all experiments *except* AMON report a 1-sigma error radius.
    # AMON reports a 90% radius, so for AMON, we have to convert.
    if mission == 'AMON':
        error /= scipy.stats.chi(df=2).ppf(0.95)

    return from_cone(ra, dec, error)


def get_properties(root):

    property_names = [
        # Gravitational waves
        "HasNS",
        "HasRemnant",
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
    ]
    property_dict = {}
    for property_name in property_names:
        path = f".//Param[@name='{property_name}']"
        elem = root.find(path)
        if elem is None:
            continue
        value = elem.attrib.get('value', None)
        if value is not None:
            value = float(value)
            property_dict[property_name] = value

    return property_dict


def from_cone(ra, dec, error):
    localization_name = f"{ra:.5f}_{dec:.5f}_{error:.5f}"

    center = SkyCoord(ra * u.deg, dec * u.deg)
    radius = error * u.deg

    # Determine resolution such that there are at least
    # 16 pixels across the error radius.
    hpx = HEALPix(
        pixel_resolution_to_nside(radius / 16, round='up'), 'nested', frame=ICRS()
    )

    # Find all pixels in the 4-sigma error circle.
    ipix = hpx.cone_search_skycoord(center, 4 * radius)

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
    hpx = HEALPix(1024, 'nested', frame=ICRS())
    ipix = hp.query_polygon(hpx.nside, np.array(xyz), nest=True)

    # Convert to multi-resolution pixel indices and sort.
    uniq = ligo.skymap.moc.nest2uniq(nside_to_level(hpx.nside), ipix.astype(np.int64))
    i = np.argsort(uniq)
    ipix = ipix[i]
    uniq = uniq[i]

    # Evaluate Gaussian.
    probdensity = 1.0 * np.ones(ipix.shape)
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
        f.write(base64.b64decode(arrSplit[-1]))
        f.flush()

        skymap = ligo.skymap.io.read_sky_map(f.name, moc=True)

        skymap = {
            'localization_name': filename,
            'uniq': get_col(skymap, 'UNIQ'),
            'probdensity': get_col(skymap, 'PROBDENSITY'),
            'distmu': get_col(skymap, 'DISTMU'),
            'distsigma': get_col(skymap, 'DISTSIGMA'),
            'distnorm': get_col(skymap, 'DISTNORM'),
        }

    return skymap


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

    skymap = {
        'localization_name': filename,
        'uniq': get_col(skymap, 'UNIQ'),
        'probdensity': get_col(skymap, 'PROBDENSITY'),
        'distmu': get_col(skymap, 'DISTMU'),
        'distsigma': get_col(skymap, 'DISTSIGMA'),
        'distnorm': get_col(skymap, 'DISTNORM'),
    }

    return skymap


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


def gcn_slack_notification(session, target, app_url):
    # the target is a UserNotification. It contains a text, and an url
    # the url contains the dateobs
    # the text contains either "New notice for GCN Event" or "New GCN Event", telling us if it's a new event or a new notice for an existing event

    # get the event dateobs
    dateobs = target.url.split("gcn_events/")[-1].split("/")[0]
    dateobs_txt = Time(dateobs).isot
    source_name = dateobs_txt.replace(":", "-")
    notice_type = target.text.split(" Notice Type *")[-1].split("*")[0]
    print(f"Dateobs: {dateobs}")
    new_event = True if "New GCN Event" in target.text else False

    # Now, we will create json that describes the message we want to send to slack (and how to display it)
    # We will use the slack blocks API, which is a bit more complicated than the simple message API, but allows for more flexibility
    # https://api.slack.com/reference/block-kit/blocks

    stmt = sa.select(GcnEvent).where(GcnEvent.dateobs == dateobs)
    gcn_event = session.execute(stmt).scalars().first()

    tags = gcn_event.tags

    if 'GRB' in tags:
        # we want the name to be like GRB YYMMDD
        display_source_name = (
            f"GRB{dateobs_txt[2:4]}{dateobs_txt[5:7]}{dateobs_txt[8:10]}"
        )
    elif 'GW' in tags:
        display_source_name = (
            f"GW{dateobs_txt[2:4]}{dateobs_txt[5:7]}{dateobs_txt[8:10]}"
        )
    else:
        display_source_name = source_name

    # get the most recent notice for this event
    last_gcn_notice = gcn_event.gcn_notices[-1]

    if new_event:
        header_text = (
            f"New Event: <{app_url}{target.url}|*{dateobs_txt}*> ({notice_type})"
        )
    else:
        header_text = f"New notice for Event: <{app_url}{target.url}|*{dateobs_txt}*> ({notice_type})"

    print(dateobs_txt)

    time_since_dateobs = datetime.datetime.utcnow() - gcn_event.dateobs
    # remove the microseconds from the timedelta
    time_since_dateobs = time_since_dateobs - datetime.timedelta(
        microseconds=time_since_dateobs.microseconds
    )
    time_text = f"*Time*:\n *-* Trigger Time (T0): {dateobs}\n *-* Time since T0: {time_since_dateobs}"
    notice_type_text = f"*Notice Type*: {notice_type}"

    # now we figure out if the localization is a skymap or a point source
    print(last_gcn_notice.content)
    notice_content = lxml.etree.fromstring(last_gcn_notice.content)

    loc = notice_content.find('./WhereWhen/ObsDataLocation/ObservationLocation')
    ra = loc.find('./AstroCoords/Position2D/Value2/C1')
    dec = loc.find('./AstroCoords/Position2D/Value2/C2')
    error = loc.find('./AstroCoords/Position2D/Error2Radius')

    print(f"ra: {ra}, dec: {dec}, error: {error}")

    if ra is not None and dec is not None and error is not None:
        # the event has an associated source
        ra = float(ra.text)
        dec = float(dec.text)
        error = float(error.text)
        # for the error, keep only the first 2 digits after the decimal point
        error = float(f"{error:.2f}")
        localization_text = f"*Localization*:\n *-* Localization Type: Point\n *-* Coordinates: ra={ra}, dec={dec}, error radius={error}"
        if error < SOURCE_RADIUS_THRESHOLD:
            localization_text += f"\n *-* Source Link: <{app_url}/source/{source_name}|*{display_source_name}*>"

    else:
        # the event has an associated skymap
        localization_text = f"*Localization*:\n *-* Localization Type: Skymap\n *-* Link: <{app_url}{target.url}|*{gcn_event.dateobs}*>"

    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": header_text}},
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": time_text}},
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": notice_type_text}},
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": localization_text}},
    ]

    return blocks
