"""Reading JPL Scout's ephemeris mode.

Pinned against a captured mode-E response (`tests/data/scout_ephemeris.json`),
so these do not reach the network.
"""

import json
import os
from datetime import datetime

import pytest

from skyportal.utils.scout_ephemeris import (
    MAX_RECORDS,
    ScoutEphemerisError,
    clamp_window,
    ephemeris_at,
    parse_ephemeris,
    record_count,
    tdes_from_annotation,
)

FIXTURE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "scout_ephemeris.json",
)


@pytest.fixture
def payload():
    with open(FIXTURE) as f:
        return json.load(f)


def test_reads_position_and_uncertainty(payload):
    rows = parse_ephemeris(payload)
    assert len(rows) == 3
    first = rows[0]
    assert first["ra"] == pytest.approx(312.8884703)
    assert first["dec"] == pytest.approx(-7.7013694)
    # Plane-of-sky 1-sigma in arcminutes: the number that decides whether a
    # finder chart at this position is meaningful.
    assert first["sigma_pos_arcmin"] == pytest.approx(0.02)


def test_numbers_are_floats_not_strings(payload):
    # Every value in a Scout payload is a string.
    row = parse_ephemeris(payload)[0]
    for key in ("ra", "dec", "sigma_pos_arcmin", "vmag", "rate_arcsec_per_min"):
        assert row[key] is None or isinstance(row[key], float)


def test_rows_without_a_position_are_dropped(payload):
    payload["eph"][1]["median"].pop("ra")
    assert len(parse_ephemeris(payload)) == 2


def test_refuses_a_response_with_no_rows():
    with pytest.raises(ScoutEphemerisError):
        parse_ephemeris({"signature": {}})


def test_refuses_a_response_whose_rows_have_no_positions(payload):
    for row in payload["eph"]:
        row["median"] = {}
    with pytest.raises(ScoutEphemerisError):
        parse_ephemeris(payload)


def test_window_is_clamped_to_the_api_row_cap():
    # 24h at one-minute steps is 1441 rows against a 500-row limit.
    assert record_count(24, 1) > MAX_RECORDS
    clamped = clamp_window(24, 1)
    assert record_count(clamped, 1) <= MAX_RECORDS
    # A window that already fits is left alone.
    assert clamp_window(3, 1) == 3.0
    assert record_count(3, 1) <= MAX_RECORDS


def test_a_longer_step_buys_a_longer_window():
    assert clamp_window(24, 5) > clamp_window(24, 1)


def test_zero_step_is_refused():
    with pytest.raises(ScoutEphemerisError):
        record_count(3, 0)


def test_picks_the_row_nearest_the_requested_time(payload):
    rows = parse_ephemeris(payload)
    wanted = datetime.fromisoformat(rows[1]["time"])
    assert ephemeris_at(rows, wanted)["time"] == rows[1]["time"]


def test_nearest_row_without_a_time_falls_back(payload):
    rows = parse_ephemeris(payload)
    assert ephemeris_at(rows, None) is rows[0]
    assert ephemeris_at([], datetime.utcnow()) is None


def test_designation_comes_from_the_annotation():
    assert tdes_from_annotation({"tdes": "ZTF10Fd"}) == "ZTF10Fd"


def test_designation_falls_back_to_the_scout_url():
    # Rows ingested before the designation was recorded carry only the URL.
    data = {"url": "https://cneos.jpl.nasa.gov/scout/#/object/P22pvNY"}
    assert tdes_from_annotation(data) == "P22pvNY"


def test_no_designation_available():
    assert tdes_from_annotation({}) is None
    assert tdes_from_annotation(None) is None


def test_position_at_reads_the_nearest_row(monkeypatch, payload):
    """position_at returns (ra, dec, sigma) for the row nearest the moment."""
    import skyportal.utils.scout_ephemeris as se

    monkeypatch.setattr(
        se, "fetch_ephemeris", lambda *a, **k: se.parse_ephemeris(payload)
    )
    rows = se.parse_ephemeris(payload)
    when = datetime.fromisoformat(rows[1]["time"])
    ra, dec, sigma = se.position_at("ZTF10Fd", when)
    assert (ra, dec) == (rows[1]["ra"], rows[1]["dec"])
    assert sigma == rows[1]["sigma_pos_arcmin"]


def test_lookup_window_is_short():
    # A chart wants one position, not a track.
    from skyportal.utils.scout_ephemeris import STEP_LOOKUP_HOURS

    assert 0 < STEP_LOOKUP_HOURS <= 1
