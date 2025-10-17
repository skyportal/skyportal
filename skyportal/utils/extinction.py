import os

import astropy.units as u
import dustmaps.sfd
import numpy as np
import sncosmo
from astropy.coordinates import SkyCoord
from dust_extinction.parameter_averages import G23
from dustmaps.config import config

from baselayer.log import make_log

config["data_dir"] = "/tmp"
log = make_log("extinction")


def get_extinction_coefficient(filter_name, Rv=3.1, Ebv=1.0):
    """
    Calculate the extinction coefficient for a given filter.

    Parameters:
    -----------
    filter_name : str
        Filter name (e.g., 'ztfg', 'sdssg', 'bessellv', etc.)
    Rv : float, optional
        Rv parameter of the extinction model (default: 3.1)
    Ebv : float, optional
        E(B-V) reference value (default: 1.0)

    Returns:
    --------
    float
        Extinction coefficient A_λ/E(B-V) in magnitudes
    """
    try:
        bandpass = sncosmo.get_bandpass(filter_name)
        wave_eff = bandpass.wave_eff
        ext = G23(Rv=Rv)
        extinction_coeff = -2.5 * np.log10(ext.extinguish(wave_eff * u.AA, Ebv=Ebv))
        return extinction_coeff
    except Exception as e:
        raise Exception(f"Filter '{filter_name}' not recognized: {e}")


class _ExtinctionCalculator:
    """Internal class to handle SFD dust map queries efficiently."""

    def __init__(self):
        self._sfd_query = None

    def _ensure_sfd_ready(self):
        """Ensure SFD dust map data and query are ready."""
        if self._sfd_query is None:
            path = dustmaps.sfd.data_dir()
            path = os.path.join(path, "sfd")
            if not os.path.exists(path):
                log("No SFD data for dustmaps, downloading it")
                dustmaps.sfd.fetch()

            self._sfd_query = dustmaps.sfd.SFDQuery()

    def get_ebv(self, ra: float, dec: float) -> float:
        """Get E(B-V) extinction value."""
        self._ensure_sfd_ready()
        coords = SkyCoord(ra, dec, unit="deg")
        return self._sfd_query(coords)


_calculator = _ExtinctionCalculator()


def calculate_extinction(
    ra: float, dec: float, filter_name: str, Rv: float = 3.1
) -> float | None:
    """
    Calculate extinction A_lambda for given coordinates and filter.

    Parameters
    ----------
    ra : float
        Right ascension in degrees
    dec : float
        Declination in degrees
    filter_name : str
        Filter name (any sncosmo filter: 'ztfg', 'sdssg', 'bessellv', etc.)
    Rv : float, optional
        Total-to-selective extinction ratio (default: 3.1)

    Returns
    -------
    float or None
        Extinction A_lambda in magnitudes, or None if filter not supported

    Examples
    --------
    >>> ext = calculate_extinction(180.0, 45.0, 'ztfg')
    >>> ext = calculate_extinction(12.5, -30.2, 'sdssg')
    """
    try:
        # Get extinction coefficient A_λ/E(B-V)
        coeff = get_extinction_coefficient(filter_name, Rv=Rv, Ebv=1.0)

        # Get E(B-V) from SFD dust maps
        ebv = _calculator.get_ebv(ra, dec)

        # Calculate A_λ = (A_λ/E(B-V)) * E(B-V)
        extinction = coeff * ebv

        return extinction

    except Exception as e:
        log(f"Could not calculate extinction for {filter_name}: {e}")
        return None


def deredden_flux(
    flux: float,
    ra: float = None,
    dec: float = None,
    filter_name: str = None,
    Rv: float = 3.1,
    extinction: float = None,
) -> float | None:
    """
    De-redden flux using extinction correction.

    Parameters
    ----------
    flux : float
        Observed flux in microjansky
    ra : float, optional
        Right ascension in degrees (required if extinction not provided)
    dec : float, optional
        Declination in degrees (required if extinction not provided)
    filter_name : str, optional
        Filter name (any sncosmo filter) (required if extinction not provided)
    Rv : float, optional
        Total-to-selective extinction ratio (default: 3.1)
    extinction : float, optional
        Pre-computed extinction value in magnitudes. If provided, ra, dec, and filter_name are ignored.

    Returns
    -------
    float or None
        De-reddened flux in microjansky, or None if filter not supported
    """
    if extinction is None:
        if ra is None or dec is None or filter_name is None:
            raise ValueError(
                "Either extinction must be provided, or ra, dec, and filter_name must all be provided"
            )
        extinction = calculate_extinction(ra, dec, filter_name, Rv)
        if extinction is None:
            return None

    if np.isnan(flux) or flux <= 0:
        return flux

    correction_factor = 10 ** (0.4 * extinction)
    return flux * correction_factor
