import numpy as np

from skyportal.models.photometry import PHOT_ZP


def mag2flux(mags):
    """Convert AB magnitudes to fluxes in micro Janskies.

    Parameters
    ----------
    mags : float array
        Magnitudes in the AB system.

    Returns
    -------
    float array
        Fluxes in units of micro Jansky.
    """
    return 10 ** (-0.4 * (mags - PHOT_ZP))


def magerr2fluxerr(mags, magerr):
    """Convert magnitude errors to flux errors in micro Janskies.

    Parameters
    ----------
    mags : float array
        Magnitudes in the AB system.
    magerr : float array
        Errors on the magnitudes.

    Returns
    -------
    float array
        Flux errors in units of micro Jansky.
    """
    return mag2flux(mags) * magerr * np.log(10) / 2.5
