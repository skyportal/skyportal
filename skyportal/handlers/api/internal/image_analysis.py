from baselayer.app.access import permissions
from baselayer.app.env import load_env
from baselayer.log import make_log
import os
import arrow
from astropy.io import fits
from astropy.wcs import WCS
from astropy.table import vstack
from astropy.coordinates import SkyCoord
from astropy.coordinates import search_around_sky
from astropy.time import Time
import astropy.units as u

import astroscrappy
from stdpipe import (
    astrometry,
    photometry,
    catalogs,
    cutouts,
    templates,
    plots,
    pipeline,
    psf,
    utils,
)

import base64
import numpy as np
import sqlalchemy as sa
import tempfile
from tqdm.auto import tqdm
from tornado.ioloop import IOLoop
import shutil

from ..photometry import add_external_photometry
from ...base import BaseHandler
from ....models import Instrument, User, DBSession

_, cfg = load_env()

log = make_log('image_analysis')

for dir in os.listdir('/tmp'):
    if dir.startswith('sex') or dir.startswith('psfex'):
        shutil.rmtree(os.path.join('/tmp', dir))

catalogs_enum = [
    "ps1",
    "gaiadr2",
    "gaiaedr3",
    "skymapper",
    "vsx",
    "apass",
    "sdss",
    "atlas",
    "usnob1",
    "gsc",
]

templates_enum = ["PanSTARRS/DR1/g", "PanSTARRS/DR1/r", "PanSTARRS/DR1/i"]

methods_enum = ["scamp", "astropy", "astrometrynet"]


def spherical_match(ra1, dec1, ra2, dec2, sr=1 / 3600):
    """
    Positional match on the sphere for two lists of coordinates.

    Aimed to be a direct replacement for :func:`esutil.htm.HTM.match` method with :code:`maxmatch=0`.

    Parameters
    ----------
    ra1: float
        First set of points RA
    dec1: float
        First set of points Dec
    ra2: float
        Second set of points RA
    dec2: float
        Second set of points Dec
    sr:
        Maximal acceptable pair distance to be considered a match, in degrees

    Returns
    -------
    tuple
        Two parallel sets of indices corresponding to matches from first and second lists, along with the pairwise distances in degrees

    """

    idx1, idx2, dist, _ = search_around_sky(
        SkyCoord(ra1, dec1, unit='deg'), SkyCoord(ra2, dec2, unit='deg'), sr * u.deg
    )

    dist = dist.deg  # convert to degrees

    return idx1, idx2, dist


def spherical_distance(ra1, dec1, ra2, dec2):
    """
    Compute the distance between two points on the sphere.

    Parameters
    ----------
    ra1: float
        First point RA
    dec1: float
        First point Dec
    ra2: float
        Second point RA
    dec2: float
        Second point Dec

    Returns
    -------
    float
        Distance in degrees

    """

    x = np.sin(np.deg2rad((ra1 - ra2) / 2))
    x *= x
    y = np.sin(np.deg2rad((dec1 - dec2) / 2))
    y *= y

    z = np.cos(np.deg2rad((dec1 + dec2) / 2))
    z *= z

    return np.rad2deg(2 * np.arcsin(np.sqrt(x * (z - y) + y)))


def reduce_image(
    image,
    header,
    obj_id,
    instrument_id,
    user_id,
    gain,
    matching_radius,
    catalog_name_refinement,
    catalog_name_crossmatch,
    template_name,
    method,
    s_n_detection,
    s_n_blind_match,
    detect_cosmics=False,
):
    """
    Reduce an image: Perform astrometric and photometric calibration,
    and extract photometry to add it to the database.

    Parameters
    ----------
    image: numpy.ndarray
        Image data
    header: astropy.io.fits.Header
        Image header
    obj_id: str
        Object ID
    instrument_id: int
        Instrument ID
    user_id: int
        User ID
    gain: float
        Gain of the telescope
    matching_radius: float
        Matching radius in arcseconds
    catalog_name_refinement: str
        Name of the catalog used for astrometric refinement
    catalog_name_crossmatch: str
        Name of the catalog used for cross-matching
    template_name: str
        Name of the template used for photometric calibration
    method: str
        Astrometric calibration method
    s_n_detection: int
        Detection S/N threshold
    s_n_blind_match: int
        Number used to simulate N stars
    detect_cosmics: bool
        Run LACosmic on the image

    Returns
    -------
    None

    """

    try:
        workdir_sextractor_obj = tempfile.mkdtemp(prefix='sex')
        workdir_sextractor_obj1 = tempfile.mkdtemp(prefix='sex1')
        workdir_psfex = tempfile.mkdtemp(prefix='psfex')

        with DBSession() as session:
            instrument = session.scalars(
                sa.select(Instrument).where(Instrument.id == instrument_id)
            ).first()
            user = session.scalars(sa.select(User).where(User.id == user_id)).first()

            time = utils.get_obs_time(header, verbose=False)
            filt = header.get('FILTER')

            wcs = WCS(header)

            # Masking saturated stars and cosmic rays
            # The mask is a binary frame with the same size as the image where True means that this pixel should not be used for the analysis
            mask = image > 0.9 * np.max(image)

            # TODO: we want to use 'dilate' to expand the mask before applying it to the image, to get the edges that are not saturated

            if detect_cosmics:
                cmask, _ = astroscrappy.detect_cosmics(image, mask, verbose=False)
                mask |= cmask

            # ## Detect and measure the objects
            # The detection is based on building the noise model through (grid-based) background and background rms estimation, and then extracting the groups of connected pixels above some pre-defined threshold
            # Detecting objects using SExtractor and getting their measurements in apertures with 3 pixels radius
            # edge argument : control the rejection of objects detected too close to frame edge

            # Astropy Table, ordered by the object brightness
            obj = photometry.get_objects_sextractor(
                image, gain=gain, aper=3.0, edge=10, _workdir=workdir_sextractor_obj
            )

            if obj is None:
                raise ValueError(
                    'No objects detected. If this is unexpected, check source extractor installation.'
                )

            # First rough estimation of average FWHM of detected objects, taking into account only unflagged ones
            fwhm = np.median(obj['fwhm'][obj['flags'] == 0])

            # We will pass this FWHM to measurement function so that aperture and background radii will be relative to it.
            # We will also reject all objects with measured S/N < 5
            obj = photometry.measure_objects(
                obj,
                image,
                mask=mask,
                fwhm=fwhm,
                gain=gain,
                aper=1.0,
                bkgann=[5, 7],
                sn=s_n_detection,
                verbose=True,
            )

            # ## Astrometric calibration
            # Getting the center position, size and pixel scale for the image
            center_ra, center_dec, center_sr = astrometry.get_frame_center(
                header=header, width=image.shape[1], height=image.shape[0]
            )
            pixscale = astrometry.get_pixscale(header=header)

            # ## Reference catalogue
            # Catalog name may be any Vizier identifier (ps1, gaiadr2, gaiaedr3, usnob1, gsc, skymapper, apass, sdss, atlas, vsx).
            cat_refinement = catalogs.get_cat_vizier(
                center_ra,
                center_dec,
                center_sr,
                catalog_name_refinement,
                filters={'rmag': '<21'},
            )

            cat_crossmatch = catalogs.get_cat_vizier(
                center_ra,
                center_dec,
                center_sr,
                catalog_name_crossmatch,
                filters={'rmag': '<21'},
            )

            # ## Astrometric refinement
            # Refining the astrometric solution based on the positions of detected objects and catalogue stars with scamp
            wcs = pipeline.refine_astrometry(
                obj,
                cat_refinement,
                sr=matching_radius,
                wcs=wcs,
                method=method,
                cat_col_mag='rmag',
                verbose=True,
            )

            if wcs is not None:
                # Update WCS info in the header
                astrometry.clear_wcs(
                    header,
                    remove_comments=True,
                    remove_underscored=True,
                    remove_history=True,
                )
                header.update(wcs.to_header(relax=True))

            # ## Photometric calibration

            # Positionally matching detected objects with catalogue stars
            # Then building the photometric model for their instrumental magnitudes

            # Photometric calibration using 2 arcsec matching radius, r magnitude, g-r color and second order spatial variations
            m = pipeline.calibrate_photometry(
                obj,
                cat_refinement,
                sr=matching_radius,
                cat_col_mag='rmag',
                cat_col_mag1='gmag',
                cat_col_mag2='rmag',
                max_intrinsic_rms=0.02,
                order=2,
                verbose=True,
            )

            # ## Simple catalogue-based transient detection
            # Some transients may already be detected by comparing the detected objects with catalogue BUT limited approach

            # Filtering of transient candidates
            candidates = pipeline.filter_transient_candidates(
                obj, cat=cat_crossmatch, sr=matching_radius, verbose=True
            )

            # Creating cutouts for these candidates and vizualizing them
            filtered = []

            for i, cand in enumerate(candidates):
                dist = spherical_distance(
                    candidates[i]['ra'], candidates[i]['dec'], obj['ra'], obj['dec']
                )

                if (
                    dist < matching_radius * 2
                ).all():  # TODO: verify the x2. the previous value was 4 / 3600, whereas it was 2 / 3600 everywhere else. Which is why I assumed it should be multiplied by 2.
                    filtered.append(candidates[i])

            for i, cand in enumerate(filtered):
                # Create the cutout from image based on the candidate
                cutout = cutouts.get_cutout(image, cand, 20, mask=mask, header=header)
                # We may directly download the template image for this cutout from HiPS server - same scale and orientation
                cutout['template'] = templates.get_hips_image(
                    template_name, header=cutout['header']
                )[0]
                # We do not have difference image, so it will only display original one, template and mask
                plots.plot_cutout(cutout, qq=[0.5, 99.9], stretch='linear')

            # compute upper limit
            ra0, dec0, sr0 = astrometry.get_frame_center(
                wcs=wcs, width=image.shape[1], height=image.shape[0]
            )
            pixscale = astrometry.get_pixscale(wcs=wcs)

            # Function to get the zero point as a function of position on the image
            zero_fn = m['zero_fn']
            obj['mag_calib'] = obj['mag'] + zero_fn(obj['x'], obj['y'])

            # We may roughly estimate the effective gain of the image from background mean and rms as gain = mean/rms**2
            bg, rms = photometry.get_background(image, mask=mask, get_rms=True)

            psf_model, psf_snapshots = psf.run_psfex(
                image,
                mask=mask,
                checkimages=['SNAPSHOTS'],
                order=0,
                verbose=True,
                _workdir=workdir_psfex,
            )

            sims = []
            for _ in tqdm(range(100)):
                image1 = image.copy()

                # Simulate s_n_blind_match random stars
                sim = pipeline.place_random_stars(
                    image1,
                    psf_model,
                    nstars=s_n_blind_match,
                    minflux=10,
                    maxflux=1e6,
                    wcs=wcs,
                    gain=gain,
                    saturation=50000,
                )

                sim['mag_calib'] = sim['mag'] + zero_fn(sim['x'], sim['y'])
                sim['detected'] = False
                sim['mag_measured'] = np.nan
                sim['magerr_measured'] = np.nan
                sim['flags_measured'] = np.nan

                mask1 = image1 >= 50000

                obj1 = photometry.get_objects_sextractor(
                    image1,
                    mask=mask | mask1,
                    r0=1,
                    aper=5.0,
                    wcs=wcs,
                    gain=gain,
                    minarea=3,
                    sn=s_n_detection,
                    _workdir=workdir_sextractor_obj1,
                )

                obj1['mag_calib'] = obj1['mag'] + zero_fn(obj1['x'], obj1['y'])

                # Positional match within FWHM/2 radius
                oidx, sidx, dist = spherical_match(
                    obj1['ra'],
                    obj1['dec'],
                    sim['ra'],
                    sim['dec'],
                    pixscale * np.median(obj1['fwhm']) / 2,
                )
                # Mark matched stars
                sim['detected'][sidx] = True
                # Also store measured magnitude, its error and flags
                sim['mag_measured'][sidx] = obj1['mag_calib'][oidx]
                sim['magerr_measured'][sidx] = obj1['magerr'][oidx]
                sim['flags_measured'][sidx] = obj1['flags'][oidx]

                sims.append(sim)

            sims = vstack(sims)

            data = {
                'ra': [ra0],
                'dec': [dec0],
                'magsys': ['ab'],
                'mjd': [time.mjd],
                'mag': [sims['mag_calib'][0]],
                'magerr': [sims['magerr_measured'][0]],
                'limiting_mag': [sims['mag_calib'][0]],
                'filter': [filt],
            }

            data_out = {
                'obj_id': obj_id,
                'instrument_id': instrument.id,
                'group_ids': [g.id for g in user.accessible_groups],
                **data,
            }

            for i in range(len(data['mag'])):
                # if mag is not None or nan but magerr is, set magerr to 0
                if not (data['mag'][i] is None or np.isnan(data['mag'][i])):
                    if data['magerr'][i] is None or np.isnan(data['magerr'][i]):
                        data['magerr'][i] = 0.0

            shutil.rmtree(workdir_sextractor_obj)
            shutil.rmtree(workdir_psfex)
            shutil.rmtree(workdir_sextractor_obj1)

            add_external_photometry(data_out, user)
    except Exception as e:
        try:
            if workdir_sextractor_obj is not None:
                shutil.rmtree(workdir_sextractor_obj)
            if workdir_psfex is not None:
                shutil.rmtree(workdir_psfex)
            if workdir_sextractor_obj1 is not None:
                shutil.rmtree(workdir_sextractor_obj1)
        except Exception as e2:
            log(e2)
        log(e)
        pass


class ImageAnalysisHandler(BaseHandler):
    @permissions(["Upload data"])
    def post(self, obj_id):
        """
        ---
        description: Submit a new image for analysis
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        try:
            if 'image_analysis' not in cfg:
                return self.error('Image analysis is not enabled')

            missing_bins = []
            for exe in ['scamp', 'psfex']:
                bin = shutil.which(exe)
                if bin is None:
                    missing_bins.append(exe)

            if len(missing_bins) > 0:
                return self.error(
                    f"Can't run image analysis, missing dependencies: {', '.join(missing_bins)}"
                )

            data = self.get_json()
            instrument_id = data.get('instrument_id')
            if instrument_id is None:
                return self.error(message=f'Missing instrument {instrument_id}')
            instrument = Instrument.get_if_accessible_by(
                instrument_id, self.current_user, raise_if_none=True, mode="read"
            )

            if instrument is None:
                return self.error(
                    message=f'Found no instrument with id {instrument_id}'
                )

            matching_radius = data.get('matching_radius')
            if matching_radius is None:
                return self.error(message='Missing matching_radius')
            try:
                matching_radius = float(matching_radius)
            except ValueError:
                return self.error(message='Invalid matching_radius')

            matching_radius = matching_radius / 3600.0  # arcsec -> deg

            gain = data.get('gain')
            if gain is None:
                return self.error(message='Missing gain')
            try:
                gain = float(gain)
            except ValueError:
                return self.error(message='Invalid gain')

            catalog_name_refinement = data.get('astrometric_refinement_cat')
            if catalog_name_refinement is None:
                return self.error(message='Missing astrometric_refinement_cat')
            if catalog_name_refinement not in catalogs_enum:
                return self.error(
                    message=f'Invalid astrometric_refinement_cat, must be once of: {", ".join(catalogs_enum)}'
                )

            catalog_name_crossmatch = data.get('crossmatch_catalog')
            if catalog_name_crossmatch is None:
                return self.error(message='Missing crossmatch_catalog')
            if catalog_name_crossmatch not in catalogs_enum:
                return self.error(
                    message=f'Invalid crossmatch_catalog, must be once of: {", ".join(catalogs_enum)}'
                )

            template_name = data.get('template')
            if template_name is None:
                return self.error(message='Missing template')
            if template_name not in templates_enum:
                return self.error(
                    message=f'Invalid template, must be once of: {", ".join(templates_enum)}'
                )

            method = data.get('astrometric_refinement_meth')
            if method is None:
                return self.error(message='Missing method')
            if method not in methods_enum:
                return self.error(
                    message=f'Invalid method, must be once of: {", ".join(methods_enum)}'
                )

            file_data = data.get("image_data")
            if file_data is None:
                return self.error(message='Missing image data')

            filt = data.get("filter")
            if filt is None:
                return self.error(message='Missing filter')

            obstime = data.get("obstime")
            if obstime is None:
                return self.error(message='Missing obstime')

            s_n_detection = data.get("s_n_detection", 5)
            if s_n_detection is None:
                return self.error(message='Missing s_n_detection')
            if not isinstance(s_n_detection, int) or int(s_n_detection) < 0:
                return self.error(
                    message='Invalid s_n_detection, must be a positive integer'
                )

            s_n_blind_match = data.get("s_n_blind_match", 20)
            if s_n_blind_match is None:
                return self.error(message='Missing s_n_blind_match')
            if not isinstance(s_n_blind_match, int) or int(s_n_blind_match) < 0:
                return self.error(
                    message='Invalid s_n_blind_match, must be a positive integer'
                )

            try:
                obstime = Time(arrow.get(obstime.strip()).datetime)
            except Exception as e:
                return self.error(message=f'Invalid obstime: {e}')

            file_data = file_data.split('base64,')
            file_name = file_data[0].split('name=')[1].split(';')[0]

            if file_name.endswith('.fz'):
                suffix = '.fits.fz'
            else:
                suffix = '.fits'
            with tempfile.NamedTemporaryFile(
                suffix=suffix, mode="wb", delete=True
            ) as f:
                file_data = base64.b64decode(file_data[-1])
                f.write(file_data)
                f.flush()
                hdul = fits.open(f.name)

                hdul_index = -1
                for i, hdu in enumerate(hdul):
                    if hdu.data is not None:
                        hdul_index = i
                        break
                if hdul_index == -1:
                    return self.error(message='No image found in file')
                header = hdul[hdul_index].header
                image_data = hdul[hdul_index].data.astype(np.double)
                header['FILTER'] = filt
                header['DATE-OBS'] = obstime.isot
                IOLoop.current().run_in_executor(
                    None,
                    lambda: reduce_image(
                        image_data,
                        header,
                        obj_id,
                        instrument.id,
                        self.current_user.id,
                        gain,
                        matching_radius,
                        catalog_name_refinement,
                        catalog_name_crossmatch,
                        template_name,
                        method,
                        s_n_detection,
                        s_n_blind_match,
                    ),
                )
                return self.success()
        except Exception as e:
            log(e)
            return self.error(str(e))
