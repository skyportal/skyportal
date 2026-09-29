"""Which matching alert owns a GCN crossmatch annotation.

An object can match one event on many alerts. The broker returns them newest
first, and each was written in turn, so the oldest was the last word: a source
whose latest alert was 1.8 days before an EP trigger was annotated at -30.7,
from an archival match a month earlier. Scanners read delta_t as the latest
alert's offset from the trigger.
"""

from skyportal.utils.gcn_crossmatch import describes_later_alert


def test_a_later_alert_displaces_an_earlier_one():
    # delta_t is alert_jd - event_jd, so larger is later. An archival match
    # before the trigger loses to any alert after it.
    assert describes_later_alert({"delta_t": -1.8}, {"delta_t": -30.7})
    assert describes_later_alert({"delta_t": 0.4}, {"delta_t": -0.5})


def test_an_earlier_alert_does_not_regress_the_entry():
    assert not describes_later_alert({"delta_t": -30.7}, {"delta_t": -1.8})
    # The same alert twice is not later than itself; a re-run must not churn.
    assert not describes_later_alert({"delta_t": -1.8}, {"delta_t": -1.8})


def test_the_first_entry_for_an_event_is_written():
    assert describes_later_alert({"delta_t": -3.0}, {})
    assert describes_later_alert({"delta_t": -3.0}, None)


def test_an_entry_that_says_nothing_about_when_it_was_loses():
    # Annotations written before delta_t existed, or by a match that could not
    # date its alert: a real value beats a missing one, never the other way.
    assert describes_later_alert({"delta_t": -3.0}, {"distance_arcmin": 1.2})
    assert not describes_later_alert({"distance_arcmin": 1.2}, {"delta_t": -3.0})


def test_two_entries_with_no_delta_t_do_not_swap():
    assert not describes_later_alert({"credible_level": 50}, {"credible_level": 90})
