"""Unit tests for ``_version_validation``: reading a broker filter version's
stored validation verdict, keyed per fid with a legacy single-slot fallback.
"""

from skyportal.handlers.api.broker import (
    BrokerFilterValidateBody,
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
