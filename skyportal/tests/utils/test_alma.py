import json
import pathlib

import pytest

from skyportal.utils.alma import MAX_DATASETS, summarize

# Real rows from the ALMA archive around Centaurus A.
FIXTURE = pathlib.Path(__file__).parents[1] / "data" / "alma_coverage.json"


@pytest.fixture()
def rows():
    with open(FIXTURE) as f:
        return json.load(f)


def test_nothing_observed_reads_as_not_observed():
    data = summarize([], ra=10.0, dec=20.0, radius_arcsec=30.0)
    assert data["observed"] is False
    assert data["n_observations"] == 0
    assert data["bands"] == [] and data["datasets"] == []
    assert data["frequency_ghz"] is None
    assert data["query"] == {"ra": 10.0, "dec": 20.0, "radius_arcsec": 30.0}


def test_real_rows_summarize_into_the_annotation(rows):
    data = summarize(rows, ra=201.365063, dec=-43.019113, radius_arcsec=20.0)
    assert data["observed"] is True
    assert data["n_observations"] == len(rows)
    # The fixture deliberately spans several bands and proposals.
    assert data["bands"] == sorted(set(data["bands"]))
    assert len(data["bands"]) > 1
    assert len(data["proposals"]) > 1
    assert data["first_release"] <= data["last_release"]


def test_resolutions_report_the_finest_available(rows):
    data = summarize(rows)
    # Smaller is finer for both, so the best is the minimum.
    assert data["best_spatial_resolution_arcsec"] == pytest.approx(
        min(r["spatial_resolution"] for r in rows)
    )
    assert data["best_velocity_resolution_m_s"] == pytest.approx(
        min(r["velocity_resolution"] for r in rows)
    )


def test_frequency_range_spans_the_rows(rows):
    data = summarize(rows)
    freqs = [r["frequency"] for r in rows]
    assert data["frequency_ghz"] == [min(freqs), max(freqs)]


def test_datasets_are_unique_and_capped():
    """The dataset list is what an analysis service fetches, so it stays bounded."""
    rows = [
        {"member_ous_uid": f"uid://A001/X{i // 2:04d}", "proposal_id": "p"}
        for i in range(4 * MAX_DATASETS)
    ]
    data = summarize(rows)
    assert len(data["datasets"]) == MAX_DATASETS
    assert len(set(data["datasets"])) == MAX_DATASETS
    assert data["datasets_truncated"] is True

    few = summarize(rows[:4])
    assert few["datasets_truncated"] is False


def test_unparseable_values_are_skipped_rather_than_crashing():
    rows = [
        {"frequency": None, "band_list": None, "spatial_resolution": "n/a"},
        {"frequency": 100.0, "band_list": "6 7", "spatial_resolution": 0.5},
    ]
    data = summarize(rows)
    assert data["frequency_ghz"] == [100.0, 100.0]
    assert data["bands"] == [6, 7]
    assert data["best_spatial_resolution_arcsec"] == 0.5


def test_nan_measurements_are_excluded_not_propagated():
    """The archive leaves NaN in these columns; one would poison the whole range."""
    nan = float("nan")
    rows = [
        {"frequency": nan, "spatial_resolution": nan, "velocity_resolution": nan},
        {"frequency": 230.0, "spatial_resolution": 0.4, "velocity_resolution": 1000.0},
        {"frequency": 100.0, "spatial_resolution": 1.2, "velocity_resolution": 5000.0},
    ]
    data = summarize(rows)
    assert data["frequency_ghz"] == [100.0, 230.0]
    assert data["best_spatial_resolution_arcsec"] == 0.4
    assert data["best_velocity_resolution_m_s"] == 1000.0

    # Every value NaN is the same as having none.
    only_nan = summarize([{"frequency": nan, "spatial_resolution": nan}])
    assert only_nan["frequency_ghz"] is None
    assert only_nan["best_spatial_resolution_arcsec"] is None
