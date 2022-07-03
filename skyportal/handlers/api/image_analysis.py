from baselayer.app.access import auth_or_token
from baselayer.log import make_log

import arrow
import astroscrappy
from astropy.io import fits
from astropy.wcs import WCS

import numpy as np
import tempfile

from stdpipe import (
    astrometry,
    photometry,
    catalogs,
    cutouts,
    templates,
    plots,
    pipeline,
)

from ..base import BaseHandler
from ...models import Instrument

log = make_log('api/image_analysis')


def reduce_image(filename, image, header):

    # Parsing its header and print it
    # time = utils.get_obs_time(header, verbose=False)
    # fname = header.get('FILTER')
    wcs = WCS(header)
    gain = 0.25  # otherwise it is a str

    # Masking saturated stars and cosmic rays
    # The mask is a binary frame with the same size as the image where True means that this pixel should not be used for the analysis
    mask = image > 0.9 * np.max(image)

    cmask, cimage = astroscrappy.detect_cosmics(image, mask, verbose=False)
    log(f'Done masking cosmics: {np.sum(cmask)} pixels masked')
    mask |= cmask

    # ## Detect and measure the objects
    # The detection is based on building the noise model through (grid-based) background and background rms estimation, and then extracting the groups of connected pixels above some pre-defined threshold
    # Detecting objects using SExtractor and getting their measurements in apertures with 3 pixels radius
    # edge argument : control the rejection of objects detected too close to frame edge

    # Astropy Table, ordered by the object brightness
    obj = photometry.get_objects_sextractor(image, gain=gain, aper=3.0, edge=10)
    if obj is None:
        raise ValueError(
            'No objects detected. If this is unexpected, check source extractor installation.'
        )
    log(f'{len(obj)} objects detected')

    # First rough estimation of average FWHM of detected objects, taking into account only unflagged ones
    fwhm = np.median(obj['fwhm'][obj['flags'] == 0])
    log(f'Average FWHM is {fwhm} pixels')

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
        sn=5,
        verbose=True,
    )
    log(f'{len(obj)} objects properly measured')

    # ## Astrometric calibration
    # Getting the center position, size and pixel scale for the image
    center_ra, center_dec, center_sr = astrometry.get_frame_center(
        filename=filename, width=image.shape[1], height=image.shape[0]
    )
    pixscale = astrometry.get_pixscale(filename=filename)

    log(
        f'Frame center is {center_ra} {center_dec} radius {center_sr} deg, {pixscale*3600} arcsec/pixel'
    )

    # ## Reference catalogue
    # Catalogue name may be any Vizier identifier (ps1, gaiadr2, gaiaedr3, usnob1, gsc, skymapper, apass, sdss, atlas, vsx).
    # Getting PanSTARRS objects brighter than r=17 mag
    cat = catalogs.get_cat_vizier(
        center_ra, center_dec, center_sr, 'ps1', filters={'rmag': '<21'}
    )
    log(f'{len(cat)} catalogue stars')

    # ## Astrometric refinement
    # Refining the astrometric solution based on the positions of detected objects and catalogue stars with scamp
    wcs = pipeline.refine_astrometry(
        obj, cat, wcs=wcs, method='scamp', cat_col_mag='rmag', verbose=True
    )
    if wcs is not None:
        # Update WCS info in the header
        astrometry.clear_wcs(
            header, remove_comments=True, remove_underscored=True, remove_history=True
        )
        header.update(wcs.to_header(relax=True))

    # ## Photometric calibration

    # Positionally matching detected objects with catalogue stars
    # Then building the photometric model for their instrumental magnitudes

    # Photometric calibration using 2 arcsec matching radius, r magnitude, g-r color and second order spatial variations
    pipeline.calibrate_photometry(
        obj,
        cat,
        sr=2 / 3600,
        cat_col_mag='rmag',
        cat_col_mag1='gmag',
        cat_col_mag2='rmag',
        max_intrinsic_rms=0.02,
        order=2,
        verbose=True,
    )

    # The code above automatically augments the object list with calibrated magnitudes, but we may also do it manually
    # obj['mag_calib'] = obj['mag'] + m['zero_fn'](obj['x'], obj['y'])
    # obj['mag_calib_err'] = np.hypot(obj['magerr'], m['zero_fn'](obj['x'], obj['y'], get_err=True))

    # ## Simple catalogue-based transient detection
    # Some transients may already be detected by comparing the detected objects with catalogue BUT limited approach

    # Filtering of transient candidates
    candidates = pipeline.filter_transient_candidates(
        obj, cat=cat, sr=2 / 3600, verbose=True
    )
    log('{candidates}')

    # Creating cutouts for these candidates and vizualizing them (6238 ???)
    def spherical_distance(ra1, dec1, ra2, dec2):

        x = np.sin(np.deg2rad((ra1 - ra2) / 2))
        x *= x
        y = np.sin(np.deg2rad((dec1 - dec2) / 2))
        y *= y

        z = np.cos(np.deg2rad((dec1 + dec2) / 2))
        z *= z

        return np.rad2deg(2 * np.arcsin(np.sqrt(x * (z - y) + y)))

    filtered = []
    for i, cand in enumerate(candidates):
        dist = spherical_distance(
            candidates[i]['ra'], candidates[i]['dec'], 191.4734, 89.1846
        )  # XRT enhanced position
        if dist < 4 / 3600:
            filtered.append(candidates[i])

    for i, cand in enumerate(filtered):
        # Create the cutout from image based on the candidate
        cutout = cutouts.get_cutout(image, cand, 20, mask=mask, header=header)
        # We may directly download the template image for this cutout from HiPS server - same scale and orientation
        cutout['template'] = templates.get_hips_image(
            'PanSTARRS/DR1/r', header=cutout['header']
        )[0]
        # We do not have difference image, so it will only display original one, template and mask
        plots.plot_cutout(cutout, qq=[0.5, 99.9], stretch='linear')


class ImageAnalysisHandler(BaseHandler):
    @auth_or_token
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

        data = self.get_json()
        instrument_id = data.get('instrument_id')
        if instrument_id is None:
            return self.error(message=f'Missing instrument {instrument_id}')
        instrument = Instrument.get_if_accessible_by(
            instrument_id, self.current_user, raise_if_none=True, mode="read"
        )

        image_data = data.get("image_data")
        if image_data is None:
            return self.error(message='Missing image data')

        # filt = data.get("filter")
        obstime = data.get("obstime")
        obstime = arrow.get(obstime.strip()).datetime

        with tempfile.NamedTemporaryFile(
            suffix=".fits.fz", mode="w", delete=False
        ) as f:
            f.write(image_data)
            f.flush()

            # hdul = fits.open(f.name)
            filename = './test.fits.fz'
            hdul = fits.open(filename)
            header = hdul[1].header
            image_data = hdul[1].data

            reduce_image(filename, image_data, header)

        self.push_all(action="skyportal/REFRESH_INSTRUMENTS")
        return self.success(data={"id": instrument.id})
