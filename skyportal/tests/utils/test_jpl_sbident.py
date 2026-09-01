"""Reading JPL's Small-Body Identification responses."""

import asyncio

import pytest

from skyportal.utils.jpl_sbident import (
    JPLSBIdentError,
    _parse_offset,
    _sexagesimal,
    parse_matches,
)

FIELDS = [
    "Object name",
    "Astrometric RA (hh:mm:ss)",
    "Astrometric Dec (dd mm'ss\")",
    'Dist. from center RA (")',
    'Dist. from center Dec (")',
    'Dist. from center Norm (")',
    "Visual magnitude (V)",
]


def _payload(rows):
    return {"fields_second": FIELDS, "data_second_pass": rows}


def test_coordinates_match_what_the_api_echoes():
    # These are the strings JPL returned for this position, so a change here
    # would be a change to what we are asking about.
    assert _sexagesimal(188.73658, is_ra=True) == "12-34-56.78"
    assert _sexagesimal(1.396, is_ra=False) == "+01-23-45.60"
    assert _sexagesimal(-5.5, is_ra=False) == "-05-30-00.00"


def test_offsets_in_the_shortened_exponential_form():
    # Wide offsets come back as "-3.E3" rather than a plain number.
    assert _parse_offset("-3.E3") == 3000.0
    assert _parse_offset("199.") == 199.0
    assert _parse_offset("") is None
    assert _parse_offset(None) is None


def test_only_bodies_inside_the_radius_are_matches():
    rows = [
        ["1 Ceres (A801 AA)", "", "", "1.", "2.", "2.5", "15.6"],
        ["99 Far (A900 XX)", "", "", "80.", "60.", "120.", "18.1"],
    ]
    matches = parse_matches(_payload(rows))
    assert [m["name"] for m in matches] == ["1 Ceres (A801 AA)"]


def test_matches_are_nearest_first():
    rows = [
        ["far", "", "", "", "", "5.0", "18.0"],
        ["near", "", "", "", "", "0.9", "17.0"],
    ]
    assert [m["name"] for m in parse_matches(_payload(rows))] == ["near", "far"]


def test_radius_is_adjustable():
    rows = [["99 Far (A900 XX)", "", "", "80.", "60.", "120.", "18.1"]]
    assert parse_matches(_payload(rows)) == []
    assert len(parse_matches(_payload(rows), max_arcsec=200)) == 1


def test_no_second_pass_means_no_matches():
    # The first pass is a coarse screen; a response carrying only that has not
    # answered the question.
    assert parse_matches({"fields_second": FIELDS, "data_second_pass": []}) == []


def test_unexpected_columns_are_refused_rather_than_guessed():
    with pytest.raises(JPLSBIdentError):
        parse_matches({"fields_second": ["Something else"], "data_second_pass": [[1]]})


class _FakeSession:
    """Stands in for the DB, answering the telescope lookup with one value."""

    def __init__(self, obscode):
        self._obscode = obscode

    async def scalar(self, *args, **kwargs):
        return self._obscode


def test_survey_site_is_taken_from_the_telescope():
    from skyportal.utils.jpl_sbident import obscode_for_survey

    assert asyncio.run(obscode_for_survey(_FakeSession("I41"), "ZTF")) == "I41"


def test_unrecorded_site_falls_back_to_geocentric():
    # Parallax at main-belt distances is about the size of the match radius, so
    # a telescope with no code is answered from Earth's centre rather than from
    # a guessed site.
    from skyportal.utils.jpl_sbident import GEOCENTRIC_OBSCODE, obscode_for_survey

    for empty in (None, ""):
        assert (
            asyncio.run(obscode_for_survey(_FakeSession(empty), "WINTER"))
            == GEOCENTRIC_OBSCODE
        )
