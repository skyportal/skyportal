"""What a GCN event's summary context keeps from each extraction.

A circular reports in whatever unit its band works in, so reading only
magnitudes dropped the X-ray and radio measurements entirely.
"""

from skyportal.handlers.api.gcn import (
    _row_measurement,
    _row_telescopes,
    _shorten,
)


def test_a_magnitude_carries_its_error():
    assert _row_measurement({"filter": "r", "mag": 19.2, "mag_error": 0.05}) == (
        "r = 19.2 +/- 0.05"
    )
    assert _row_measurement({"filter": "r", "mag": 19.2}) == "r = 19.2"


def test_a_limit_reads_as_one():
    assert _row_measurement({"filter": "z", "limiting_mag": 20.5}) == "z > 20.5"


def test_an_xray_row_keeps_its_band_and_flux():
    row = {"energy_band_kev": [0.3, 10.0], "energy_flux": 2e-13, "filter": "X-ray"}
    assert _row_measurement(row) == "0.3-10.0 keV = 2e-13 erg/cm2/s"


def test_an_xray_limit_reads_as_one():
    row = {"energy_band_kev": [0.5, 4.0], "limiting_energy_flux": 1.1e-12}
    assert _row_measurement(row) == "0.5-4.0 keV < 1.1e-12 erg/cm2/s"


def test_a_radio_row_keeps_its_frequency_and_unit():
    row = {"frequency_ghz": 6.8, "flux_density": 45.0, "flux_density_unit": "uJy"}
    assert _row_measurement(row) == "6.8 GHz = 45.0 uJy"


def test_a_row_that_measured_nothing_is_dropped():
    # Band, time and telescope but no value: an extraction that found only
    # context, which must not reach the prompt as a bare band name.
    assert _row_measurement(
        {"filter": "r", "obs_mjd": 61298.0, "telescope": "LCO"}
    ) is (None)
    assert _row_measurement({}) is None


def test_the_canonical_telescope_wins_and_repeats_collapse():
    rows = [
        {"telescope": "Las Cumbres Observatory", "telescope_canonical": "LCO"},
        {"telescope": "LCO", "telescope_canonical": "LCO"},
        {"telescope": "GTC"},
    ]
    assert _row_telescopes(rows) == ["LCO", "GTC"]


def test_rows_without_a_telescope_contribute_nothing():
    assert _row_telescopes([{"filter": "r"}, {}]) == []


def test_a_long_name_is_cut_on_a_word_boundary():
    name = "REM 60 cm robotic telescope (ESO observatory of La Silla, Chile)"
    assert (
        _shorten(name, 60) == "REM 60 cm robotic telescope (ESO observatory of La Silla"
    )
    assert _shorten("NOT", 60) == "NOT"
