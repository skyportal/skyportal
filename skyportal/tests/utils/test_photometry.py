import numpy as np

from skyportal.utils.photometry import mag2flux, magerr2fluxerr

# PHOT_ZP = 23.9 (AB mag of a 1 microJansky source)


def test_mag2flux_zeropoint_and_scaling():
    assert np.isclose(mag2flux(23.9), 1.0)  # at the zero point -> 1 uJy
    assert np.isclose(mag2flux(23.9 - 2.5), 10.0)  # 2.5 mag brighter -> 10x flux
    assert np.isclose(mag2flux(23.9 + 5.0), 0.01)  # 5 mag fainter -> 1/100 flux
    np.testing.assert_allclose(mag2flux(np.array([23.9, 21.4])), [1.0, 10.0])


def test_magerr2fluxerr():
    # at the zero point the flux is 1, so fluxerr = magerr * ln(10) / 2.5
    assert np.isclose(magerr2fluxerr(23.9, 0.1), 0.1 * np.log(10) / 2.5)
    # flux error scales with the flux
    assert np.isclose(magerr2fluxerr(21.4, 0.1), 10.0 * 0.1 * np.log(10) / 2.5)
