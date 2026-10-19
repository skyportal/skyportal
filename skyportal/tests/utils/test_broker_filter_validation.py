"""Unit tests for ``_version_validation``: reading a broker filter version's
stored validation verdict, keyed per fid with a legacy single-slot fallback.
"""

from types import SimpleNamespace

from skyportal.handlers.api.broker import (
    BrokerFilterValidateBody,
    _apply_pending_switch,
    _store_version_validation,
    _version_validation,
)


def test_per_fid_map_hit():
    altdata = {
        "boom": {
            "validations": {
                "A": {"passed": True, "message": None},
                "B": {"passed": False, "message": "div0"},
            }
        }
    }
    assert _version_validation(altdata, "A")["passed"] is True
    assert _version_validation(altdata, "B")["message"] == "div0"


def test_unknown_fid_is_none():
    altdata = {"boom": {"validations": {"A": {"passed": True}}}}
    assert _version_validation(altdata, "C") is None


def test_legacy_slot_fallback_when_fid_matches():
    altdata = {"boom": {"validation": {"fid": "X", "passed": True, "message": None}}}
    assert _version_validation(altdata, "X")["passed"] is True


def test_legacy_slot_ignored_when_fid_differs():
    altdata = {"boom": {"validation": {"fid": "X", "passed": True}}}
    assert _version_validation(altdata, "Y") is None


def test_missing_altdata_is_safe():
    assert _version_validation({}, "A") is None
    assert _version_validation(None, "A") is None


def test_store_then_read_round_trip():
    altdata = {}
    _store_version_validation(altdata, {"fid": "A", "passed": False, "message": "div0"})
    _store_version_validation(altdata, {"fid": "B", "passed": True, "message": None})
    # storing B does not clobber A's verdict
    assert _version_validation(altdata, "A") == {"passed": False, "message": "div0"}
    assert _version_validation(altdata, "B")["passed"] is True


def test_validate_body_accepts_a_string_fid():
    """BOOM's fids are strings; an int-only body rejected every BOOM validation."""
    assert BrokerFilterValidateBody(fid="nbHFqW").fid == "nbHFqW"
    assert BrokerFilterValidateBody(fid=3).fid == 3
    assert BrokerFilterValidateBody().fid is None


def _pending_filter():
    calls = []
    broker = SimpleNamespace(
        broker_class=SimpleNamespace(
            update_filter=lambda broker, session, **kwargs: calls.append(kwargs)
        )
    )
    f = SimpleNamespace(
        id=1,
        altdata={
            "boom": {
                "filter_id": "boom-id",
                "pending_switch": {"fid": "B", "by": "alice"},
            }
        },
    )
    return broker, f, calls


def test_pending_switch_happens_when_validation_passes():
    broker, f, calls = _pending_filter()
    _apply_pending_switch(broker, None, f, "B", True)
    assert calls == [
        {
            "boom_filter_id": "boom-id",
            "active": True,
            "active_fid": "B",
            "skip_validation": True,
        }
    ]
    assert "pending_switch" not in f.altdata["boom"]
    event = f.altdata["boom"]["activations"][-1]
    assert (event["fid"], event["active"], event["switched"], event["by"]) == (
        "B",
        True,
        True,
        "alice",
    )


def test_pending_switch_is_dropped_when_validation_fails():
    broker, f, calls = _pending_filter()
    _apply_pending_switch(broker, None, f, "B", False)
    assert calls == []
    assert "pending_switch" not in f.altdata["boom"]
    assert "activations" not in f.altdata["boom"]


def test_validating_another_version_keeps_the_pending_switch():
    broker, f, calls = _pending_filter()
    _apply_pending_switch(broker, None, f, "C", True)
    assert calls == []
    assert f.altdata["boom"]["pending_switch"]["fid"] == "B"
