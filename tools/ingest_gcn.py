"""

make db_clear
make db_init
PYTHONPATH=$PYTHONPATH:"." python skyportal/initial_setup.py \
      --adminuser=<google_email_address>

PYTHONPATH=$PYTHONPATH:"." python tools/ztf_upload_avro.py \
     <google_email_address> https://ztf.uw.edu/alerts/public/ztf_public_20180626.tar.gz

"""
import os
import io
import gzip
from pathlib import Path
import shutil
import numpy as np
import pandas as pd
import healpy as hp
import copy
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
import itertools
import requests
import shutil
from tqdm import tqdm
import tarfile
import gcn
import json
import pkg_resources
import lxml
from urllib.parse import urlparse

import warnings

# warnings.filterwarnings("ignore", category=RuntimeWarning)
# warnings.filterwarnings("ignore", category=UserWarning)

from urllib.request import urlretrieve
import sys

import matplotlib

matplotlib.use('Agg')
import aplpy

from baselayer.app.env import load_env
from baselayer.app.model_util import status, create_tables, drop_tables
from social_tornado.models import TornadoStorage
from skyportal.models import (
    init_db,
    Base,
    DBSession,
    ACL,
    Comment,
    Instrument,
    Group,
    GroupUser,
    Photometry,
    Role,
    Source,
    Spectrum,
    Telescope,
    Thumbnail,
    User,
    Token,
    Event,
    GcnNotice,
    Tag,
    Localization,
    Plan,
    Tele,
    Field,
    SubField,
)

import astropy.units as u
from astropy import table
from astropy import coordinates
from astropy.io import fits
from astropy.time import Time
from astropy.coordinates import SkyCoord
from astroquery.simbad import Simbad
from astroquery.vizier import Vizier

from astropy.coordinates import ICRS, SkyCoord
from astropy import units as u
from astropy_healpix import HEALPix, nside_to_level, pixel_resolution_to_nside
import ligo.skymap.io, ligo.skymap.postprocess, ligo.skymap.moc

import gwemopt.utils
import gwemopt.ztf_tiling
from skyportal.handlers.api import plan
from skyportal.handlers.api.plan import plan_args

# Only produce voice/SMS alerts for events that have these tags
DESIRABLE_TAGS = {'short', 'GW', 'AMON'}
# Ignore certain tages
UNDESIRABLE_TAGS = {'transient', 'MDC', 'retracted'}

gcn.include_notice_types(
    gcn.NoticeType.FERMI_GBM_FLT_POS,
    gcn.NoticeType.FERMI_GBM_GND_POS,
    gcn.NoticeType.FERMI_GBM_FIN_POS,
    gcn.NoticeType.FERMI_GBM_SUBTHRESH,
    gcn.NoticeType.LVC_PRELIMINARY,
    gcn.NoticeType.LVC_INITIAL,
    gcn.NoticeType.LVC_UPDATE,
    gcn.NoticeType.LVC_RETRACTION,
    gcn.NoticeType.AMON_ICECUBE_COINC,
    gcn.NoticeType.AMON_ICECUBE_HESE,
    gcn.NoticeType.ICECUBE_ASTROTRACK_GOLD,
    gcn.NoticeType.ICECUBE_ASTROTRACK_BRONZE,
)


class GCNHandler:
    def __init__(self, fname, verbose=True):

        self._connect()
        self.fname = fname
        self.verbose = verbose

        payload = pkg_resources.resource_string(__name__, 'data/%s' % fname)
        root = lxml.etree.fromstring(payload)

        self.payload = payload
        self.root = root
        self.handler()

    def download(self, url, dateobs):
        def get_col(m, name):
            try:
                col = m[name]
            except KeyError:
                return None
            else:
                return col.tolist()

        filename = os.path.basename(urlparse(url).path)

        skymap = ligo.skymap.io.read_sky_map(url, moc=True)
        localization = Localization.query.filter_by(
            dateobs=dateobs, localization_name=filename
        ).all()
        if len(localization) == 0:
            DBSession().merge(
                Localization(
                    localization_name=filename,
                    dateobs=dateobs,
                    uniq=get_col(skymap, 'UNIQ'),
                    probdensity=get_col(skymap, 'PROBDENSITY'),
                    distmu=get_col(skymap, 'DISTMU'),
                    distsigma=get_col(skymap, 'DISTSIGMA'),
                    distnorm=get_col(skymap, 'DISTNORM'),
                )
            )
            DBSession().commit()
        return filename

    def from_cone(self, ra, dec, error, dateobs):
        localization_name = "%.5f_%.5f_%.5f" % (ra, dec, error)

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
        uniq = ligo.skymap.moc.nest2uniq(
            nside_to_level(hpx.nside), ipix.astype(np.uint64)
        )
        i = np.argsort(uniq)
        ipix = ipix[i]
        uniq = uniq[i]

        # Evaluate Gaussian.
        distance = hpx.healpix_to_skycoord(ipix).separation(center)
        probdensity = np.exp(
            -0.5 * np.square(distance / radius).to_value(u.dimensionless_unscaled)
        )
        probdensity /= probdensity.sum() * hpx.pixel_area.to_value(u.steradian)

        DBSession().merge(
            Localization(
                localization_name=localization_name,
                dateobs=dateobs,
                uniq=uniq.tolist(),
                probdensity=probdensity.tolist(),
            )
        )
        DBSession().commit()

        return localization_name

    def contour(self, localization_name, dateobs):
        localization = Localization.query.filter_by(
            dateobs=dateobs, localization_name=localization_name
        ).all()[0]

        # Calculate credible levels.
        prob = localization.flat_2d
        cls = 100 * ligo.skymap.postprocess.find_greedy_credible_levels(prob)

        # Construct contours and return as a GeoJSON feature collection.
        levels = [50, 90]
        paths = ligo.skymap.postprocess.contour(
            cls, levels, degrees=True, simplify=True
        )
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
        DBSession().merge(localization)
        DBSession().commit()

    def get_dateobs(self):
        """Get the UTC event time from a GCN notice, rounded to the nearest second,
        as a datetime.datetime object."""
        dateobs = Time(
            self.root.find(
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

    def get_tags(self):
        """Get source classification tag strings from GCN notice."""
        # Get event stream.
        mission = urlparse(self.root.attrib['ivorn']).path.lstrip('/')
        yield mission

        # What type of burst is this: GRB or GW?
        try:
            value = self.root.find("./Why/Inference/Concept").text
        except AttributeError:
            pass
        else:
            if value == 'process.variation.burst;em.gamma':
                yield 'GRB'
            elif value == 'process.variation.trans;em.gamma':
                yield 'transient'

        # LIGO/Virgo alerts don't provide the Why/Inference/Concept tag,
        # so let's just identify it as a GW event based on the notice type.
        notice_type = gcn.get_notice_type(self.root)
        if notice_type in {
            gcn.NoticeType.LVC_PRELIMINARY,
            gcn.NoticeType.LVC_INITIAL,
            gcn.NoticeType.LVC_UPDATE,
            gcn.NoticeType.LVC_RETRACTION,
        }:
            yield 'GW'

        # Is this a retracted LIGO/Virgo event?
        if notice_type == gcn.NoticeType.LVC_RETRACTION:
            yield 'retracted'

        # Is this a short GRB, or a long GRB?
        try:
            value = self.root.find(".//Param[@name='Long_short']").attrib['value']
        except AttributeError:
            pass
        else:
            if value != 'unknown':
                yield value.lower()

        # Gaaaaaah! Alerts of type FERMI_GBM_SUBTHRESH store the
        # classification in a different property!
        try:
            value = (
                self.root.find(".//Param[@name='Duration_class']")
                .attrib['value']
                .title()
            )
        except AttributeError:
            pass
        else:
            if value != 'unknown':
                yield value.lower()

        # Get LIGO/Virgo source classification, if present.
        classifications = [
            (float(elem.attrib['value']), elem.attrib['name'])
            for elem in self.root.iterfind("./What/Group[@type='Classification']/Param")
        ]
        if classifications:
            _, classification = max(classifications)
            yield classification

        search = self.root.find("./What/Param[@name='Search']")
        if search is not None:
            yield search.attrib['value']

    def get_skymap(self, gcn_notice):
        mission = urlparse(self.root.attrib['ivorn']).path.lstrip('/')

        # Try Fermi GBM convention
        if gcn_notice.notice_type == gcn.NoticeType.FERMI_GBM_FIN_POS:
            url = self.root.find("./What/Param[@name='LocationMap_URL']").attrib[
                'value'
            ]
            url = url.replace('http://', 'https://')
            url = url.replace('_locplot_', '_healpix_')
            url = url.replace('.png', '.fit')
            return tasks.skymaps.download.s(url, gcn_notice.dateobs)

        # Try Fermi GBM **subthreshold** convention. Stupid, stupid, stupid!!
        if gcn_notice.notice_type == gcn.NoticeType.FERMI_GBM_SUBTHRESH:
            url = self.root.find("./What/Param[@name='HealPix_URL']").attrib['value']
            return tasks.skymaps.download.s(url, gcn_notice.dateobs)

        # Try LVC convention
        skymap = self.root.find("./What/Group[@type='GW_SKYMAP']")
        if skymap is not None:
            children = skymap.getchildren()
            for child in children:
                if child.attrib['name'] == 'skymap_fits':
                    url = child.attrib['value']
                    break

            return self.download(url, gcn_notice.dateobs)

        retraction = self.root.find("./What/Param[@name='Retraction']")
        if retraction is not None:
            retraction = int(retraction.attrib['value'])
            if retraction == 1:
                return None

        # Try error cone
        loc = self.root.find('./WhereWhen/ObsDataLocation/ObservationLocation')
        if loc is None:
            return None

        ra = loc.find('./AstroCoords/Position2D/Value2/C1')
        dec = loc.find('./AstroCoords/Position2D/Value2/C2')
        error = loc.find('./AstroCoords/Position2D/Error2Radius')

        if None in (ra, dec, error):
            return None

        ra = float(ra.text)
        dec = float(dec.text)
        error = float(error.text)

        # Apparently, all experiments *except* AMON report a 1-sigma error radius.
        # AMON reports a 90% radius, so for AMON, we have to convert.
        if mission != 'AMON':
            error /= scipy.stats.chi(df=2).ppf(0.95)

        return self.from_cone(ra, dec, error, gcn_notice.dateobs)

    def handler(self):
        dateobs = self.get_dateobs()

        try:
            event = Event.query.filter_by(dateobs=dateobs).one()
        except:
            event = DBSession().merge(Event(dateobs=dateobs))
            DBSession().commit()

        old_tags = set(event.tags)
        tags = [Tag(dateobs=event.dateobs, text=_) for _ in self.get_tags()]

        gcn_notice = GcnNotice(
            content=self.payload,
            ivorn=self.root.attrib['ivorn'],
            notice_type=gcn.get_notice_type(self.root),
            stream=urlparse(self.root.attrib['ivorn']).path.lstrip('/'),
            date=self.root.find('./Who/Date').text,
            dateobs=event.dateobs,
        )

        for tag in tags:
            DBSession().merge(tag)
        DBSession().merge(gcn_notice)
        DBSession().commit()
        new_tags = set(event.tags)

        skymap = self.get_skymap(gcn_notice)
        self.contour(skymap, dateobs)
        dateobs = Time(dateobs, format='datetime', scale='utc').isot
        tele = 'ZTF'
        plan.tile(skymap, dateobs, tele, **plan_args[tele])

    def _connect(self):
        env, cfg = load_env()
        with status(f"Connecting to database {cfg['database']['database']}"):
            init_db(**cfg['database'])


def create_fields():
    # telescopes = ["ZTF", "Gattini", "DECam", "KPED", "GROWTH-India"]
    telescopes = ["ZTF"]
    available_filters = {
        "ZTF": ["g", "r", "i"],
        "Gattini": ["J"],
        "DECam": ["g", "r", "i", "z"],
        "KPED": ["U", "g", "r", "i"],
        "GROWTH-India": ["g", "r", "i", "z"],
    }

    with tqdm(telescopes) as telescope_progress:
        for tele in telescope_progress:
            telescope_progress.set_description('populating {}'.format(tele))

            filename = 'skyportal/too/input/%s.ref' % tele
            if os.path.isfile(filename):
                refstable = table.Table.read(
                    filename, format='ascii', data_start=2, data_end=-1
                )
                refs = table.unique(refstable, keys=['field', 'fid'])
                if "maglimcat" not in refs.columns:
                    refs["maglimcat"] = np.nan

                reference_images = {
                    group[0]['field']: group['fid'].astype(int).tolist()
                    for group in refs.group_by('field').groups
                }
                reference_mags = {
                    group[0]['field']: group['maglimcat'].tolist()
                    for group in refs.group_by('field').groups
                }

            else:
                reference_images = {}
                reference_mags = {}

            tessfilename = 'skyportal/too/input/%s.tess' % tele
            fields = np.recfromtxt(
                tessfilename, usecols=range(3), names=['field_id', 'ra', 'dec']
            )

            with open('skyportal/too/config/%s.config' % tele, 'r') as g:
                config_struct = {}
                for line in g.readlines():
                    line_without_return = line.split("\n")
                    line_split = line_without_return[0].split(" ")
                    line_split = list(filter(None, line_split))
                    if line_split:
                        try:
                            config_struct[line_split[0]] = float(line_split[1])
                        except ValueError:
                            config_struct[line_split[0]] = line_split[1]

            DBSession().merge(
                Tele(
                    telescope=tele,
                    lat=config_struct["latitude"],
                    lon=config_struct["longitude"],
                    elevation=config_struct["elevation"],
                    timezone=config_struct["timezone"],
                    filters=available_filters[tele],
                    default_plan_args=plan_args[tele],
                )
            )

            for field_id, ra, dec in tqdm(fields, 'populating fields'):
                ref_filter_ids = reference_images.get(field_id, [])
                ref_filter_mags = []
                for val in reference_mags.get(field_id, []):
                    ref_filter_mags.append(val)
                bands = {1: 'g', 2: 'r', 3: 'i', 4: 'z', 5: 'J'}
                ref_filter_bands = [bands.get(n, n) for n in ref_filter_ids]

                if config_struct["FOV_type"] == "square":
                    ipix, radecs, patch, area = gwemopt.utils.getSquarePixels(
                        ra, dec, config_struct["FOV"], Localization.nside
                    )
                elif config_struct["FOV_type"] == "circle":
                    ipix, radecs, patch, area = gwemopt.utils.getCirclePixels(
                        ra, dec, config_struct["FOV"], Localization.nside
                    )
                if len(radecs) == 0:
                    continue
                corners = np.vstack((radecs, radecs[0, :]))
                if corners.size == 10:
                    corners_copy = copy.deepcopy(corners)
                    corners[2] = corners_copy[3]
                    corners[3] = corners_copy[2]
                contour = {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'MultiLineString',
                        'coordinates': [corners.tolist()],
                    },
                    'properties': {
                        'telescope': tele,
                        'field_id': int(field_id),
                        'ra': ra,
                        'dec': dec,
                        'depth': dict(zip(ref_filter_bands, ref_filter_mags)),
                    },
                }
                DBSession().merge(
                    Field(
                        telescope=tele,
                        field_id=int(field_id),
                        ra=ra,
                        dec=dec,
                        contour=contour,
                        reference_filter_ids=ref_filter_ids,
                        reference_filter_mags=ref_filter_mags,
                        ipix=ipix.tolist(),
                    )
                )

            if tele == "ZTF":
                quadrant_coords = get_ztf_quadrants()

                skyoffset_frames = coordinates.SkyCoord(
                    fields['ra'], fields['dec'], unit=u.deg
                ).skyoffset_frame()

                quadrant_coords_icrs = coordinates.SkyCoord(
                    *np.tile(quadrant_coords[:, np.newaxis, ...], (len(fields), 1, 1)),
                    unit=u.deg,
                    frame=skyoffset_frames[:, np.newaxis, np.newaxis],
                ).transform_to(coordinates.ICRS)

                quadrant_xyz = np.moveaxis(
                    quadrant_coords_icrs.cartesian.xyz.value, 0, -1
                )

                for field_id, xyz in zip(
                    tqdm(fields['field_id'], 'populating subfields'), quadrant_xyz
                ):
                    for ii, xyz in enumerate(xyz):
                        ipix = hp.query_polygon(Localization.nside, xyz)
                        DBSession().merge(
                            SubField(
                                telescope=tele,
                                field_id=int(field_id),
                                subfield_id=int(ii),
                                ipix=ipix.tolist(),
                            )
                        )


def get_ztf_quadrants():
    """Calculate ZTF quadrant footprints as offsets from the telescope
    boresight."""
    quad_prob = gwemopt.ztf_tiling.QuadProb(0, 0)
    ztf_tile = gwemopt.ztf_tiling.ZTFtile(0, 0)
    quad_cents_ra, quad_cents_dec = ztf_tile.quadrant_centers()
    offsets = np.asarray(
        [
            quad_prob.getWCS(
                quad_cents_ra[quadrant_id], quad_cents_dec[quadrant_id]
            ).calc_footprint(axes=quad_prob.quadrant_size)
            for quadrant_id in range(64)
        ]
    )
    return np.transpose(offsets, (2, 0, 1))


if __name__ == "__main__":

    from argparse import ArgumentParser

    parser = ArgumentParser()

    parser.add_argument('-f', '--popfields', action='store_true', default=False)
    parser.add_argument('--datafile', default='GW190425_initial.xml')

    args = parser.parse_args()

    env, cfg = load_env()
    basedir = Path(os.path.dirname(__file__)) / ".."

    with status(f"Connecting to database {cfg['database']['database']}"):
        init_db(**cfg["database"])

    if args.popfields:
        with status("Populating fields"):
            create_fields()
    gcnhandler = GCNHandler(args.datafile)

    # events = Event.query.all()
    # localizations = Localization.query.all()
    # plans = Plan.query.all()
    # print(events)
    # print(localizations)
    # print(plans[0].planned_observations)
