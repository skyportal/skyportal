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


def test_deredden_photometry_df_matches_per_filter_law():
    """The analysis-handler helper must deredden a photometry frame with the
    same per-filter A_lambda used elsewhere: mag -> mag - A, flux -> flux *
    10**(0.4 A), leaving magerr and unsupported/NaN values untouched."""
    import pandas as pd

    from skyportal.handlers.api.analysis import deredden_photometry_df

    ra, dec = 150.0, 2.5
    a_g = calculate_extinction(ra, dec, "ztfg")
    a_r = calculate_extinction(ra, dec, "ztfr")

    df = pd.DataFrame(
        {
            "mjd": [59000.0, 59001.0, 59002.0],
            "flux": [100.0, 50.0, np.nan],  # last row is a non-detection
            "fluxerr": [10.0, 5.0, 8.0],
            "mag": [20.0, 20.75, np.nan],
            "magerr": [0.1, 0.11, np.nan],
            "filter": ["ztfg", "ztfr", "ztfg"],
            "limiting_mag": [np.nan, np.nan, 21.0],
        }
    )
    out = deredden_photometry_df(df.copy(), ra, dec)

    assert out["mag"][0] == pytest.approx(20.0 - a_g)
    assert out["mag"][1] == pytest.approx(20.75 - a_r)
    assert out["flux"][0] == pytest.approx(100.0 * 10 ** (0.4 * a_g))
    assert out["fluxerr"][0] == pytest.approx(10.0 * 10 ** (0.4 * a_g))
    assert out["limiting_mag"][2] == pytest.approx(21.0 - a_g)  # non-detection UL
    assert np.isnan(out["mag"][2])  # masked mag stays masked
    assert out["magerr"][0] == 0.1  # magnitude errors unchanged


def test_deredden_photometry_df_noop_without_coordinates():
    """No coordinates -> return the frame unchanged rather than guessing."""
    import pandas as pd

    from skyportal.handlers.api.analysis import deredden_photometry_df

    df = pd.DataFrame({"mag": [20.0], "flux": [100.0], "filter": ["ztfg"]})
    out = deredden_photometry_df(df.copy(), None, None)
    assert out["mag"][0] == 20.0
    assert out["flux"][0] == 100.0


def test_correct_extinction_is_a_reserved_analysis_parameter():
    """correct_extinction is consumed by SkyPortal, so it is accepted for any
    service without appearing in that service's optional_analysis_parameters."""
    from skyportal.handlers.api.analysis import unknown_analysis_parameters

    oap = {"source": ["Arnett"], "tmax": {}}
    # reserved key allowed even though the service never declared it
    assert unknown_analysis_parameters({"correct_extinction": True}, oap) == set()
    assert (
        unknown_analysis_parameters(
            {"source": "Arnett", "correct_extinction": True}, oap
        )
        == set()
    )
    # genuinely unknown keys are still rejected
    assert unknown_analysis_parameters({"bogus": 1}, oap) == {"bogus"}
