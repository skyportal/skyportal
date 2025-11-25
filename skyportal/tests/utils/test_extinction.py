import numpy as np
import pytest

from skyportal.utils.extinction import (
    calculate_extinction,
    deredden_flux,
    get_extinction_coefficient,
)


@pytest.mark.parametrize(
    "filter_name, expected_coeff",
    [
        ("ztfg", 3.6507),
        ("ztfr", 2.5299),
        ("ztfi", 1.8451),
    ],
)
def test_ztf_filters_coefficients(filter_name, expected_coeff):
    """Test extinction coefficients for ZTF filters match reference values.

    Reference coefficients for ZTF filters for G23 extinction law from dust_extinction for Rv=3.1
    """
    coeff = get_extinction_coefficient(filter_name, Rv=3.1, Ebv=1.0)
    assert abs(coeff - expected_coeff) < 0.1, f"Expected ~{expected_coeff}, got {coeff}"


def test_invalid_filter():
    with pytest.raises(Exception):
        get_extinction_coefficient("invalid_filter", Rv=3.1, Ebv=1.0)


def test_extinction_calculation():
    extinction = calculate_extinction(0.0, 90.0, "ztfg", Rv=3.1)

    assert extinction is not None
    assert extinction >= 0, "Extinction should be non-negative"


def test_invalid_filter_returns_none():
    extinction = calculate_extinction(180.0, 45.0, "invalid_filter", Rv=3.1)
    assert extinction is None


def test_flux_correction_increases_flux():
    original_flux = 20.0
    corrected_flux = deredden_flux(original_flux, 0.0, 0.0, "ztfg", Rv=3.1)

    if corrected_flux is not None:
        assert corrected_flux >= original_flux, (
            "Corrected flux should be >= observed flux"
        )


@pytest.mark.parametrize(
    "flux_value",
    [np.nan, -10.0, 0.0],
)
def test_invalid_flux_handling(flux_value):
    corrected_flux = deredden_flux(flux_value, 0.0, 90.0, "ztfg", Rv=3.1)

    if np.isnan(flux_value):
        assert np.isnan(corrected_flux)
    elif flux_value <= 0:
        assert corrected_flux == flux_value


def test_no_extinction_for_invalid_filter():
    corrected_flux = deredden_flux(100.0, 180.0, 45.0, "invalid_filter", Rv=3.1)
    assert corrected_flux is None
