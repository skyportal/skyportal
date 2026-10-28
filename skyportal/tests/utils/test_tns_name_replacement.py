"""Unit tests for ``should_replace_tns_name``: deciding whether a TNS source
supersedes the name already stored on an object.
"""

from types import SimpleNamespace

from skyportal.utils.tns import should_replace_tns_name, tns_designation


def _obj(tns_name, tns_info=None, ra=10.0, dec=20.0):
    return SimpleNamespace(
        id="ZTF26aaaaaaa", ra=ra, dec=dec, tns_name=tns_name, tns_info=tns_info
    )


def _info(ra, dec):
    return {"radeg": ra, "decdeg": dec}


def test_designation_drops_either_prefix():
    assert tns_designation("AT 2026agsu") == "2026agsu"
    assert tns_designation("SN 2026agsu") == "2026agsu"
    assert tns_designation("2026agsu") == "2026agsu"
    assert tns_designation(None) == ""


def test_an_unnamed_object_takes_the_name():
    assert should_replace_tns_name(_obj(None), "AT 2026agsu", 10.0, 20.0) is True
    assert should_replace_tns_name(_obj(""), "AT 2026agsu", 10.0, 20.0) is True


def test_the_same_name_is_left_alone():
    obj = _obj("AT 2026agsu", _info(10.0, 20.0))
    assert should_replace_tns_name(obj, "AT 2026agsu", 10.0, 20.0) is False


def test_at_becomes_sn_for_the_same_designation():
    """The upgrade the object actually needs once TNS accepts a classification."""
    obj = _obj("AT 2026agsu", _info(10.0, 20.0))
    assert should_replace_tns_name(obj, "SN 2026agsu", 10.0, 20.0) is True


def test_an_sn_name_is_not_downgraded_to_at():
    obj = _obj("SN 2026agsu", _info(10.0, 20.0))
    assert should_replace_tns_name(obj, "AT 2026agsu", 10.0, 20.0) is False


def test_a_different_sn_source_does_not_steal_the_name_on_prefix_alone():
    """A farther source wins on distance or leaves the object alone."""
    obj = _obj("AT 2026agsu", _info(10.0, 20.0))
    assert should_replace_tns_name(obj, "SN 2020xyz", 10.0005, 20.0005) is False


def test_a_closer_source_wins_whatever_its_prefix():
    obj = _obj("AT 2026agsu", _info(10.001, 20.001))
    assert should_replace_tns_name(obj, "AT 2026zzzz", 10.0, 20.0) is True


def test_a_name_without_stored_coordinates_still_upgrades():
    obj = _obj("AT 2026agsu", tns_info=None)
    assert should_replace_tns_name(obj, "SN 2026agsu", 10.0, 20.0) is True
