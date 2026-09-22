"""The pure bits of autonomous triage: the master switch and how a query's
recipients combine (subscribers in the group, plus always-on notify groups).
Query matching and enqueue are DB-backed and covered by API tests."""

from skyportal.utils.assistant_triage import combine_recipients, triage_enabled


def _cfg(base_url="http://llm", enabled=True):
    return {
        "app.assistant": {"base_url": base_url, "analysis_triage": {"enabled": enabled}}
    }


def test_enable_gate_needs_flag_and_assistant():
    assert triage_enabled(_cfg(enabled=True)) is True
    assert triage_enabled(_cfg(enabled=False)) is False
    assert triage_enabled(_cfg(base_url=None, enabled=True)) is False
    assert triage_enabled({}) is False


def test_subscribers_are_kept_only_if_in_the_group():
    # 1 and 2 subscribed; only 1 is still a group member -> only 1 is kept.
    assert combine_recipients([1, 2], [1, 3], []) == [1]


def test_notify_groups_are_always_included():
    # 9 is not a subscriber but is in an always-on notify group.
    assert combine_recipients([1], [1], [9]) == [1, 9]


def test_no_recipients_when_nobody_qualifies():
    assert combine_recipients([2], [1, 3], []) == []


def test_deduplicates_across_sources():
    assert combine_recipients([1, 2], [1, 2], [2, 5]) == [1, 2, 5]
