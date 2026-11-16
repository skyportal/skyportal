import json
import pathlib

import pytest

from skyportal.utils.spherex import VISIT_GAP_DAYS, _count_images, summarize

# Real coverage rows from IRSA for a galaxy in COSMOS (150.067693, 2.193719).
FIXTURE = pathlib.Path(__file__).parents[1] / "data" / "spherex_coverage.json"


@pytest.fixture()
def rows():
    with open(FIXTURE) as f:
        return json.load(f)


def _row(day, n=1, collection="spherex_dr1", detector=1):
    return {
        "obs_collection": collection,
        "energy_bandpassname": f"SPHEREx-D{detector}",
        "mjd_day": float(day),
        "n_images": n,
        "em_min": 0.75e-6,
        "em_max": 1.1e-6,
    }


def test_nothing_observed_reads_as_not_observed():
    data = summarize([], ra=10.0, dec=20.0)
    assert data["observed"] is False
    assert data["n_images"] == 0
    assert data["collections"] == {} and data["detectors"] == []
    assert data["visits"] == []
    assert data["wavelength_um"] is None
    assert data["first_observed"] is None and data["last_observed"] is None
    assert data["query"] == {"ra": 10.0, "dec": 20.0}


def test_real_rows_summarize_into_the_annotation(rows):
    data = summarize(rows, ra=150.067693, dec=2.193719)
    assert data["observed"] is True
    assert data["n_images"] == sum(r["n_images"] for r in rows)
    assert sum(data["collections"].values()) == data["n_images"]
    # The fixture spans DR1 and the QR3 images taken after it.
    assert set(data["collections"]) == {"spherex_dr1", "spherex_qr3"}
    assert data["detectors"] == [1, 2, 3, 4, 5, 6]
    assert data["wavelength_um"] == [0.746, 5.01]
    assert data["first_observed"] <= data["last_observed"]


def test_visits_account_for_every_image(rows):
    data = summarize(rows)
    assert len(data["visits"]) > 1
    assert sum(v["n_images"] for v in data["visits"]) == data["n_images"]
    starts = [v["start"] for v in data["visits"]]
    assert starts == sorted(starts)
    assert data["visits"][0]["start"] == data["first_observed"]
    assert data["visits"][-1]["end"] == data["last_observed"]


def test_a_long_gap_starts_a_new_visit():
    days = [61000, 61003, 61000 + VISIT_GAP_DAYS + 3, 61200, 61201]
    data = summarize([_row(day, n=2) for day in days])
    assert [v["n_images"] for v in data["visits"]] == [6, 4]
    # A gap of exactly VISIT_GAP_DAYS still belongs to the same visit.
    assert data["visits"][0] == {
        "start": "2025-11-21",
        "end": "2025-12-24",
        "n_images": 6,
    }
    assert data["visits"][1]["start"] == "2026-06-09"


def test_sia_images_count_like_the_tap_query():
    """Both query paths must hand summarize the same rows."""
    images = [
        {
            "obs_collection": "spherex_qr3",
            "energy_bandpassname": "SPHEREx-D4",
            "t_min": t,
            "em_min": em_min,
            "em_max": 3.8e-6,
        }
        for t, em_min in [(61200.1, 2.43e-6), (61200.9, 2.42e-6), (61201.5, 2.43e-6)]
    ]
    assert sorted(_count_images(images), key=lambda r: r["mjd_day"]) == [
        {
            "obs_collection": "spherex_qr3",
            "energy_bandpassname": "SPHEREx-D4",
            "mjd_day": 61200.0,
            "n_images": 2,
            "em_min": 2.42e-6,
            "em_max": 3.8e-6,
        },
        {
            "obs_collection": "spherex_qr3",
            "energy_bandpassname": "SPHEREx-D4",
            "mjd_day": 61201.0,
            "n_images": 1,
            "em_min": 2.43e-6,
            "em_max": 3.8e-6,
        },
    ]
