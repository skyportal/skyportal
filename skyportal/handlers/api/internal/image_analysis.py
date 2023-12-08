from baselayer.app.access import permissions
from baselayer.app.env import load_env
from baselayer.log import make_log
import os
import arrow
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
from astropy.coordinates import search_around_sky
from astropy.table import Table
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
    utils,
)

import base64
import io
import matplotlib.pyplot as plt
import numpy as np
import sqlalchemy as sa
import tempfile
from tornado.ioloop import IOLoop
import shutil

from ..photometry import add_external_photometry
from ...base import BaseHandler
from ....models import Comment, Instrument, Obj, User, ThreadSession

_, cfg = load_env()

log = make_log('image_analysis')

for dir in os.listdir('/tmp'):
    if dir.startswith('sex') or dir.startswith('psfex'):
        shutil.rmtree(os.path.join('/tmp', dir))

catalogs_enum = {
    "ps1": ["gmag", "rmag", "imag", "zmag"],
    "gaiaedr3": ["Gmag", "BPmag", "RPmag"],
    "skymapper": ["uPSF", "vPSF", "gPSF", "rPSF", "iPSF", "zPSF"],
    "sdss": ["umag", "gmag", "rmag", "imag", "zmag"],
    "usnob1": ["R1mag", "B1mag"],
    "gsc": ["Rmag", "Bjmag", "Vmag", "Imag"],
}

templates_enum = ["PanSTARRS/DR1/g", "PanSTARRS/DR1/r", "PanSTARRS/DR1/i"]

methods_enum = ["scamp", "astropy", "astrometrynet"]

DEFAULT_INSTRUMENT_GAINS = {'KAO': 2.14}

ASTROMETRY_NET_API_KEY = cfg.get('image_analysis.astrometry_net_api_key')


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
    file_name,
    header,
    obj_id,
    instrument_id,
    user_id,
    gain,
    matching_radius,
    catalog_name_refinement,
    catalog_name_crossmatch,
    crossmatch_catalog_filter_1,
    crossmatch_catalog_filter_2,
    catalog_limiting_magnitude,
    template_name,
    method,
    s_n_detection,
    s_n_blind_match,
    detect_cosmics=False,
    aper=3.0,
    bkgann=[5, 7],
    r0=0.5,
    saturation=50000,
    retrieve_wcs=False,
):
    """
    Reduce an image: Perform astrometric and photometric calibration,
    and extract photometry to add it to the database.

    Parameters
    ----------
    image: numpy.ndarray
        Image data
    file_name : str
        Name of the file being reduced
    header: astropy.io.fits.Header
        Image header
    obj_id: str
        Object ID
    instrument_id: int
        Instrument ID
    user_id: int
        User ID
    gain: float
        Gain of the image, e/ADU.
    matching_radius: float
        Matching radius in arcseconds
    catalog_name_refinement: str
        Name of the catalog used for astrometric refinement
    catalog_name_crossmatch: str
        Name of the catalog used for cross-matching
    crossmatch_catalog_filter_1 : str
        Crossmatch catalog filter (in closest band)
    crossmatch_catalog_filter_2 : str
        Crossmatch catalog filter (in second band)
    catalog_limiting_magnitude : float
        Limiting magnitude cutoff for catalog cross-match
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
    aper : float
        Circular aperture radius in pixels, to be used for flux measurement.
    bkgann : List[float]
        Background annulus (tuple with inner and outer radii) to be used for local background estimation. Inside the annulus, simple arithmetic mean of unmasked pixels is used for computing the background, and thus it is subject to some bias in crowded stellar fields. If not set, global background model is used instead.
    r0 : float
        Smoothing kernel size (sigma) to be used for improving object detection.
    saturation : float
        Counts above which saturation is assumed
    retrieve_wcs : boolean
        Use astrometry.net to solve WCS
    Returns
    -------
    None

    """

    try:
        workdir_sextractor_obj = tempfile.mkdtemp(prefix='sex')
        workdir_sextractor_obj1 = tempfile.mkdtemp(prefix='sex1')
        workdir_psfex = tempfile.mkdtemp(prefix='psfex')

        with ThreadSession() as session:
            instrument = session.scalars(
                sa.select(Instrument).where(Instrument.id == instrument_id)
            ).first()
            user = session.scalars(sa.select(User).where(User.id == user_id)).first()
            obj = session.scalars(sa.select(Obj).where(Obj.id == obj_id)).first()
            ra_obj = obj.ra
            dec_obj = obj.dec

            time = utils.get_obs_time(header, verbose=False)
            filt = header.get('FILTER')

            wcs = WCS(header)

            # subtract off median (to deal with biases)
            image -= np.nanmedian(image)

            # Fill value for image
            v, c = np.unique(image, return_counts=True)
            fill = v[c == np.max(c)][0]
            mask = image == fill

            # Masking saturated stars and cosmic rays
            # The mask is a binary frame with the same size as the image where True means that this pixel should not be used for the analysis
            # mask = image > 0.9 * np.max(image)
            mask |= image > saturation

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
                image,
                mask=mask,
                gain=gain,
                aper=aper,
                r0=r0,
                extra={'BACK_SIZE': 256},
                extra_params=['NUMBER'],
                minarea=5,
                _workdir=workdir_sextractor_obj,
            )
            if obj is None:
                raise ValueError(
                    'No objects detected. If this is unexpected, check source extractor installation.'
                )
            log(f'{file_name}: {len(obj)} objects retrieved')

            # First rough estimation of average FWHM of detected objects, taking into account only unflagged ones
            fwhm = np.median(obj['fwhm'][obj['flags'] == 0])
            log(f'{file_name}: FWHM: {fwhm}')

            # We will pass this FWHM to measurement function so that aperture and background radii will be relative to it.
            # We will also reject all objects with measured S/N < 5
            obj, _, _ = photometry.measure_objects(
                obj,
                image,
                mask=mask,
                fwhm=fwhm,
                gain=gain,
                aper=1,
                bkgann=bkgann,
                sn=s_n_detection,
                get_bg=True,
                bg_size=256,
                verbose=True,
            )
            log(f'{file_name}: {len(obj)} objects properly measured')

            # ## Astrometric calibration
            # Getting the center position, size and pixel scale for the image

            if retrieve_wcs:
                # Should be sufficient for most images
                pixscale_low = 0.3
                pixscale_upp = 3

                # We will use brightest objects with SNR > 10 to solve
                wcs = astrometry.blind_match_astrometrynet(
                    obj,
                    center_ra=ra_obj,
                    center_dec=dec_obj,
                    radius=1,
                    scale_lower=pixscale_low,
                    scale_upper=pixscale_upp,
                    sn=10,
                    api_key=ASTROMETRY_NET_API_KEY,
                )
                center_ra, center_dec, center_sr = astrometry.get_frame_center(
                    wcs=wcs, width=image.shape[1], height=image.shape[0]
                )
            else:
                center_ra, center_dec, center_sr = astrometry.get_frame_center(
                    header=header, width=image.shape[1], height=image.shape[0]
                )
            pixscale = astrometry.get_pixscale(wcs=wcs)
            log(
                f'{file_name}: Field center is at {center_ra:.3f} {center_dec:.3f}, radius {center_sr:.2f} deg, scale {3600*pixscale:.2f} arcsec/pix'
            )

            # ## Reference catalogue
            # Catalog name may be any Vizier identifier (ps1, gaiadr2, gaiaedr3, usnob1, gsc, skymapper, apass, sdss, atlas, vsx).
            cat_refinement = catalogs.get_cat_vizier(
                center_ra,
                center_dec,
                center_sr,
                catalog_name_refinement,
                filters={crossmatch_catalog_filter_1: f'<{catalog_limiting_magnitude}'},
            )

            if cat_refinement is None:
                raise ValueError(
                    'No objects in catalog. Please try a different catalog.'
                )

            # ## Astrometric refinement
            # Refining the astrometric solution based on the positions of detected objects and catalogue stars with scamp
            wcs = pipeline.refine_astrometry(
                obj,
                cat_refinement,
                sr=matching_radius,
                wcs=wcs,
                method=method,
                cat_col_mag=crossmatch_catalog_filter_1,
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
            else:
                raise ValueError('Need WCS to reduce image.')

            pixscale = astrometry.get_pixscale(wcs=wcs)

            # ## Photometric calibration

            # Positionally matching detected objects with catalogue stars
            # Then building the photometric model for their instrumental magnitudes

            # Photometric calibration using 2 arcsec matching radius, r magnitude, g-r color and second order spatial variations

            robusts = [True, False]
            m = None
            for robust in robusts:
                try:
                    m = pipeline.calibrate_photometry(
                        obj,
                        cat_refinement,
                        pixscale=pixscale,
                        sr=matching_radius,
                        cat_col_mag=crossmatch_catalog_filter_1,
                        cat_col_mag1=crossmatch_catalog_filter_1,
                        cat_col_mag2=crossmatch_catalog_filter_2,
                        max_intrinsic_rms=0.02,
                        order=2,
                        robust=robust,
                        scale_noise=True,
                        accept_flags=0x02,
                        verbose=True,
                    )
                    break
                except Exception as e:
                    log(
                        f'{file_name}: photometry with robust=True failed (str({e}). Trying with robust=False instead.'
                    )

            if m is None:
                raise ValueError('Photometry calibration failed')

            # Target
            target_obj = Table({'ra': [ra_obj], 'dec': [dec_obj]})
            x, y = wcs.all_world2pix(target_obj['ra'], target_obj['dec'], 0)
            if np.isnan(x) or np.isnan(y):
                raise ValueError('Object position appears to be outside of the image.')

            target_obj['x'], target_obj['y'] = x, y

            # try multiple form of background estimation
            bkganns = [bkgann, None]

            for bkgannulus in bkganns:
                try:
                    target_obj = photometry.measure_objects(
                        target_obj,
                        image,
                        mask=mask,
                        fwhm=fwhm,
                        aper=1,
                        bkgann=bkgannulus,
                        sn=None,
                        verbose=True,
                        gain=gain,
                    )
                    break
                except Exception as e:
                    log(
                        f'{file_name}: background annulus with {bkgannulus} failed (str({e}). Using global background instead.'
                    )

            x_size, y_size = image.shape
            if (
                (target_obj['x'] < 0)
                or (target_obj['x'] > x_size)
                or (target_obj['y'] < 0)
                or (target_obj['y'] > y_size)
            ):
                raise ValueError('Object is outside of the image')

            obj['mag_calib'] = obj['mag'] + m['zero_fn'](obj['x'], obj['y'], obj['mag'])
            target_obj['mag_calib'] = target_obj['mag'] + m['zero_fn'](
                target_obj['x'], target_obj['y'], target_obj['mag']
            )
            target_obj['mag_calib_err'] = np.hypot(
                target_obj['magerr'],
                m['zero_fn'](
                    target_obj['x'], target_obj['y'], target_obj['mag'], get_err=True
                ),
            )

            # use faintest object if object not detectable
            if np.isnan(target_obj['fluxerr']):
                target_obj['mag_limit'] = np.percentile(obj['mag_calib'], 95)
            else:
                target_obj['mag_limit'] = -2.5 * np.log10(
                    5 * target_obj['fluxerr']
                ) + m['zero_fn'](target_obj['x'], target_obj['y'], target_obj['mag'])

            fig = plt.figure(figsize=(10, 30))
            gs = fig.add_gridspec(5, 3)
            axs = [
                fig.add_subplot(gs[0, 0]),
                fig.add_subplot(gs[0, 1]),
                fig.add_subplot(gs[0, 2]),
            ]
            # Create the cutout from image based on the candidate
            cutout = cutouts.get_cutout(image, target_obj, 20, mask=mask, header=header)
            # We may directly download the template image for this cutout from HiPS server - same scale and orientation
            cutout['template'] = templates.get_ps1_image_and_mask(
                template_name[-1],
                header=cutout['header'],
            )[0]

            # We do not have difference image, so it will only display original one, template and mask
            plots.plot_cutout(
                cutout,
                planes=['image', 'template', 'mask'],
                qq=[0.5, 99.9],
                stretch='asinh',
                fig=fig,
                axs=axs,
                mark_x=cutout['image'].shape[0] // 2,
                mark_y=cutout['image'].shape[1] // 2,
                mark_r=fwhm,
            )

            ax = fig.add_subplot(gs[1, :])
            plots.plot_photometric_match(m, mode='mag', ax=ax)
            ax.set_ylim(-1, 1)
            ax = fig.add_subplot(gs[2, :])
            plots.plot_photometric_match(m, mode='color', ax=ax)
            ax.set_ylim(-1, 1)
            ax.set_xlim(-0.5, 1.5)
            ax = fig.add_subplot(gs[3:, :])
            plots.plot_photometric_match(m, mode='zero', ax=ax)

            buf = io.BytesIO()
            output_format = 'pdf'
            fig.savefig(buf, format=output_format)
            plt.close()
            buf.seek(0)

            attachment_bytes = base64.b64encode(buf.read())

            comment = Comment(
                text='Photometry Reduction',
                obj_id=obj_id,
                attachment_bytes=attachment_bytes,
                attachment_name=f"{file_name}.{output_format}",
                author=user,
                groups=user.accessible_groups,
                bot=True,
            )
            session.add(comment)
            session.commit()

            data = {
                'ra': [ra_obj],
                'dec': [dec_obj],
                'magsys': ['ab'],
                'mjd': [time.mjd],
                'limiting_mag': [target_obj['mag_limit'][0]],
                'filter': [filt],
            }
            if target_obj['mag_limit'][0] > target_obj['mag_calib'][0]:
                # only report detection if limiting magnitude supports it
                data['mag'] = [target_obj['mag_calib'][0]]
                data['magerr'] = [target_obj['mag_calib_err'][0]]

            data_out = {
                'obj_id': obj_id,
                'instrument_id': instrument.id,
                'group_ids': [g.id for g in user.accessible_groups],
                **data,
            }

            add_external_photometry(data_out, user)

            shutil.rmtree(workdir_sextractor_obj)
            shutil.rmtree(workdir_psfex)
            shutil.rmtree(workdir_sextractor_obj1)

    except Exception as e:
        try:
            if workdir_sextractor_obj is not None:
                shutil.rmtree(workdir_sextractor_obj)
            if workdir_psfex is not None:
                shutil.rmtree(workdir_psfex)
            if workdir_sextractor_obj1 is not None:
                shutil.rmtree(workdir_sextractor_obj1)
        except Exception as e2:
            log(f'{file_name}: {str(e2)}')
        log(f'{file_name}: {str(e)}')


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

            matching_radius = data.get('matching_radius', 2)
            if matching_radius is None:
                return self.error(message='Missing matching_radius')
            try:
                matching_radius = float(matching_radius)
            except ValueError:
                return self.error(message='Invalid matching_radius')

            matching_radius = matching_radius / 3600.0  # arcsec -> deg

            catalog_name_refinement = data.get('astrometric_refinement_cat', 'ps1')
            if catalog_name_refinement is None:
                return self.error(message='Missing astrometric_refinement_cat')
            if catalog_name_refinement not in catalogs_enum:
                return self.error(
                    message=f'Invalid astrometric_refinement_cat, must be once of: {", ".join(catalogs_enum)}'
                )

            catalog_name_crossmatch = data.get('crossmatch_catalog', 'ps1')
            if catalog_name_crossmatch is None:
                return self.error(message='Missing crossmatch_catalog')
            if catalog_name_crossmatch not in list(catalogs_enum.keys()):
                return self.error(
                    message=f'Invalid crossmatch_catalog, must be once of: {", ".join(catalogs_enum)}'
                )

            crossmatch_catalog_filter_1 = data.get('crossmatch_catalog_filter_1', 'ps1')
            if crossmatch_catalog_filter_1 is None:
                return self.error(message='crossmatch_catalog_filter_1')
            if (
                crossmatch_catalog_filter_1
                not in catalogs_enum[catalog_name_crossmatch]
            ):
                return self.error(
                    message=f'Invalid crossmatch_catalog_filter_1, must be once of: {", ".join(catalogs_enum[catalog_name_crossmatch])}'
                )

            crossmatch_catalog_filter_2 = data.get('crossmatch_catalog_filter_2', 'ps1')
            if crossmatch_catalog_filter_2 is None:
                return self.error(message='crossmatch_catalog_filter_2')
            if (
                crossmatch_catalog_filter_2
                not in catalogs_enum[catalog_name_crossmatch]
            ):
                return self.error(
                    message=f'Invalid crossmatch_catalog_filter_2, must be once of: {", ".join(catalogs_enum[catalog_name_crossmatch])}'
                )

            catalog_limiting_magnitude = data.get('catalog_limiting_magnitude', 21)
            if catalog_limiting_magnitude is None:
                return self.error(message='Missing catalog_limiting_magnitude')
            try:
                catalog_limiting_magnitude = float(catalog_limiting_magnitude)
            except ValueError:
                return self.error(message='Invalid catalog_limiting_magnitude')

            template_name = data.get('template', 'PanSTARRS/DR1/r')
            if template_name is None:
                return self.error(message='Missing template')
            if template_name not in templates_enum:
                return self.error(
                    message=f'Invalid template, must be once of: {", ".join(templates_enum)}'
                )

            method = data.get('astrometric_refinement_meth', 'astropy')
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

            saturation = data.get("saturation", 50000)
            if saturation is None:
                return self.error(message='Missing saturation')
            if not isinstance(saturation, int) or int(saturation) < 0:
                return self.error(
                    message='Invalid saturation, must be a positive integer'
                )

            retrieve_wcs = data.get("retrieve_wcs", False)
            if retrieve_wcs is None:
                return self.error(message='Missing retrieve_wcs')

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

                obstime = data.get("obstime")
                if obstime is None:
                    obstime = header.get('DATE-OBS')
                    if obstime is None:
                        return self.error(message='Missing obstime')

                try:
                    obstime = Time(arrow.get(obstime.strip()).datetime)
                except Exception as e:
                    return self.error(message=f'Invalid obstime: {e}')

                header['DATE-OBS'] = obstime.isot

                gain = data.get('gain')
                if gain is None:
                    gain = header.get('GAIN')
                    if gain is None:
                        if instrument.name in DEFAULT_INSTRUMENT_GAINS:
                            gain = DEFAULT_INSTRUMENT_GAINS[instrument.name]
                        else:
                            return self.error(message='Missing gain')

                try:
                    gain = float(gain)
                except ValueError:
                    return self.error(message='Invalid gain')

                IOLoop.current().run_in_executor(
                    None,
                    lambda: reduce_image(
                        image_data,
                        file_name,
                        header,
                        obj_id,
                        instrument.id,
                        self.current_user.id,
                        gain,
                        matching_radius,
                        catalog_name_refinement,
                        catalog_name_crossmatch,
                        crossmatch_catalog_filter_1,
                        crossmatch_catalog_filter_2,
                        catalog_limiting_magnitude,
                        template_name,
                        method,
                        s_n_detection,
                        s_n_blind_match,
                        saturation=saturation,
                        retrieve_wcs=retrieve_wcs,
                    ),
                )
                return self.success()
        except Exception as e:
            log(f'{file_name}: reduction failed: {str(e)}')
            return self.error(f'Reduction failed: {str(e)}')
