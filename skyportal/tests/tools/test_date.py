import numpy as np
from astropy.time import Time

from baselayer.app.env import load_env

_, cfg = load_env()
# The minimum signal-to-noise ratio to consider a photometry point as a detection
PHOT_DETECTION_THRESHOLD = cfg["misc.photometry_detection_threshold_nsigma"]


def test_mjd_to_iso_conversion(public_source):
    m1, m2 = list(
        zip(
            *[
                (Time(phot.iso.isoformat()[:-6], format="isot").mjd, phot.mjd)
                for phot in public_source.photometry
                if phot.snr and phot.snr > PHOT_DETECTION_THRESHOLD
            ]
        )
    )
    np.testing.assert_allclose(m1, m2)
