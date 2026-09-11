"""The |b| cut on the sources query.

Galactic latitude is derived from ra/dec rather than stored, so the filter is an
expression in the query; these pin the parameter it is driven by.
"""

import pytest
from pydantic import ValidationError

from skyportal.handlers.api.source import SourceGetQuery


def test_absent_by_default():
    # Sources are not restricted by galactic latitude unless asked.
    assert SourceGetQuery().minAbsGalacticLatitude is None


def test_accepts_a_latitude():
    assert SourceGetQuery(minAbsGalacticLatitude=10).minAbsGalacticLatitude == 10


def test_accepts_the_whole_sky_and_the_pole():
    assert SourceGetQuery(minAbsGalacticLatitude=0).minAbsGalacticLatitude == 0
    assert SourceGetQuery(minAbsGalacticLatitude=90).minAbsGalacticLatitude == 90


def test_refuses_a_latitude_off_the_sphere():
    # A bound outside [0, 90] cannot describe |b| and would silently match
    # nothing, so it is refused rather than accepted.
    for bad in (-1, 91):
        with pytest.raises(ValidationError):
            SourceGetQuery(minAbsGalacticLatitude=bad)
