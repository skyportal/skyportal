import numpy as np
from astropy.time import Time


def test_mjd_to_iso_conversion(public_source):
    m1, m2 = list(
        zip(
            *[
                (Time(phot.iso.isoformat()[:-6], format='isot').mjd, phot.mjd)
                for phot in public_source.photometry
                if phot.snr and phot.snr > 5
            ]
        )
    )
    np.testing.assert_allclose(m1, m2)
