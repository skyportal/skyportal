import os
import numpy as np
import scipy
import gcn
import lxml
import xmlschema
from urllib.parse import urlparse

from baselayer.app.env import load_env
from baselayer.app.model_util import status
from skyportal.models import (
    init_db,
    DBSession,
    GcnEvent,
    GcnNotice,
    GcnTag,
    Localization,
)

import astropy.units as u
from astropy.time import Time
from astropy.coordinates import SkyCoord

from astropy.coordinates import ICRS
from astropy_healpix import HEALPix, nside_to_level, pixel_resolution_to_nside
import ligo.skymap.io
import ligo.skymap.postprocess
import ligo.skymap.moc

from sqlalchemy.orm.exc import NoResultFound

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
    """Simple class for GCN ingestion"""

    def __init__(self, fname, verbose=True):

        self._connect()
        self.fname = fname
        self.verbose = verbose

        with open(fname, 'rb') as fid:
            payload = fid.read()

        schema = f'{os.path.dirname(__file__)}/schema/VOEvent-v2.0.xsd'
        voevent_schema = xmlschema.XMLSchema(schema)
        if voevent_schema.is_valid(payload):
            root = lxml.etree.fromstring(payload)
        else:
            raise Exception("xml file is not valid VOEvent")

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
            return self.download(url, gcn_notice.dateobs)

        # Try Fermi GBM **subthreshold** convention. Stupid, stupid, stupid!!
        if gcn_notice.notice_type == gcn.NoticeType.FERMI_GBM_SUBTHRESH:
            url = self.root.find("./What/Param[@name='HealPix_URL']").attrib['value']
            return self.download(url, gcn_notice.dateobs)

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
            event = GcnEvent.query.filter_by(dateobs=dateobs).one()
        except NoResultFound:
            event = DBSession().merge(GcnEvent(dateobs=dateobs))
            DBSession().commit()

        tags = [GcnTag(dateobs=event.dateobs, text=_) for _ in self.get_tags()]

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

        skymap = self.get_skymap(gcn_notice)
        self.contour(skymap, dateobs)

    def _connect(self):
        env, cfg = load_env()
        with status(f"Connecting to database {cfg['database']['database']}"):
            init_db(**cfg['database'])
