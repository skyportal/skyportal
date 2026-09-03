import datetime

import pytest

from skyportal.utils.gcn import get_designation_date


@pytest.mark.parametrize(
    ("event_id", "expected"),
    [
        ("GRB 260604C", datetime.date(2026, 6, 4)),
        ("GRB260604C", datetime.date(2026, 6, 4)),
        ("GRB 990123", datetime.date(1999, 1, 23)),  # two-digit year is last century
        ("GW170817", datetime.date(2017, 8, 17)),
        ("S260604a", datetime.date(2026, 6, 4)),  # LVK superevent
        ("EP240315a", datetime.date(2024, 3, 15)),
        ("SVOM 250101A", datetime.date(2025, 1, 1)),
        ("IC220624A", datetime.date(2022, 6, 24)),
    ],
)
def test_designation_date_is_decoded(event_id, expected):
    assert get_designation_date(event_id) == expected


@pytest.mark.parametrize(
    "event_id",
    [
        "AT2017gfo",  # a counterpart name, not an event designation
        "GRB 999999",  # six digits that are not a date
        "GRB 261340A",  # month 13
        "",
        None,
        42,
    ],
)
def test_undecodable_designations_return_none(event_id):
    assert get_designation_date(event_id) is None
