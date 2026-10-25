"""Holding one object back from TNS.

Automatic sharing drops TNS for a withheld object and leaves the other
destinations alone; the manual path refuses instead, because someone is asking
and should be told why.
"""

import types

from skyportal.utils.data_access import (
    classification_is_reportable,
    destinations_not_withheld,
)

SERVICES = ["TNS", "Hermes", "TROVE", "Public page"]


def _obj(**kwargs):
    return types.SimpleNamespace(id="ZTF26abc", **kwargs)


def test_a_withheld_object_drops_tns():
    assert "TNS" not in destinations_not_withheld(
        _obj(withhold_from_tns=True), SERVICES
    )


def test_withholding_leaves_the_other_destinations_alone():
    # The flag is about TNS; Hermes, TROVE and the public page are untouched.
    remaining = destinations_not_withheld(_obj(withhold_from_tns=True), SERVICES)
    assert remaining == ["Hermes", "TROVE", "Public page"]


def test_an_ordinary_object_keeps_tns():
    assert (
        destinations_not_withheld(_obj(withhold_from_tns=False), SERVICES) == SERVICES
    )


def test_an_object_predating_the_column_keeps_tns():
    # An obj loaded without the attribute is shared as before, rather than
    # silently withheld.
    assert destinations_not_withheld(_obj(), SERVICES) == SERVICES


def test_withholding_does_nothing_when_tns_was_not_requested():
    assert destinations_not_withheld(_obj(withhold_from_tns=True), ["Hermes"]) == [
        "Hermes"
    ]


def test_the_caller_s_list_is_not_mutated():
    # auto_source_publishing rebinds publish_to; returning a copy keeps that
    # from surprising a caller that still holds the original.
    original = list(SERVICES)
    destinations_not_withheld(_obj(withhold_from_tns=True), original)
    assert original == SERVICES


def _classification(ml=False, groups=(1,), tns_name="2026abc", withheld=False):
    obj = types.SimpleNamespace(
        id="ZTF26abc", tns_name=tns_name, withhold_from_tns=withheld
    )
    return types.SimpleNamespace(
        id=1,
        ml=ml,
        obj=obj,
        author_id=7,
        groups=[types.SimpleNamespace(id=g) for g in groups],
    )


def test_a_human_classification_on_a_known_object_is_reportable():
    assert classification_is_reportable(_classification()) is True


def test_a_machine_classification_is_never_reportable():
    # ML classifications stay off TNS until someone decides otherwise.
    assert classification_is_reportable(_classification(ml=True)) is False


def test_an_object_held_back_is_not_reportable():
    assert classification_is_reportable(_classification(withheld=True)) is False


def test_an_object_tns_does_not_know_is_not_reportable():
    # A classification report attaches to an IAU name; without one there is
    # nothing to attach to.
    assert classification_is_reportable(_classification(tns_name=None)) is False
    assert classification_is_reportable(_classification(tns_name="")) is False


def test_a_classification_shared_with_no_group_is_not_reportable():
    # Groups are what opt in, so a classification shared with none has nobody
    # asking for it to go out.
    assert classification_is_reportable(_classification(groups=())) is False
