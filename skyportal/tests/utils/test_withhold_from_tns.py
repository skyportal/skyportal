"""Holding one object back from TNS.

Automatic sharing drops TNS for a withheld object and leaves the other
destinations alone; the manual path refuses instead, because someone is asking
and should be told why.
"""

import types

from skyportal.handlers.api.candidate.candidate import (
    update_withhold_from_tns_if_relevant,
)
from skyportal.utils.data_access import (
    classification_is_reportable,
    destinations_not_withheld,
)

SERVICES = ["TNS", "Hermes", "TROVE", "Public page"]


def _obj(**kwargs):
    return types.SimpleNamespace(id="ZTF26abc", **kwargs)


def _remaining(obj, services=SERVICES):
    # Callers share one publish_to across their group loop, so dropping TNS
    # has to reach the caller's list for the later groups to skip it too.
    publish_to = list(services)
    destinations_not_withheld(obj, publish_to)
    return publish_to


def test_a_withheld_object_drops_tns():
    assert "TNS" not in _remaining(_obj(withhold_from_tns=True))


def test_withholding_leaves_the_other_destinations_alone():
    # The flag is about TNS; Hermes, TROVE and the public page are untouched.
    remaining = _remaining(_obj(withhold_from_tns=True))
    assert remaining == ["Hermes", "TROVE", "Public page"]


def test_an_ordinary_object_keeps_tns():
    assert _remaining(_obj(withhold_from_tns=False)) == SERVICES


def test_withholding_does_nothing_when_tns_was_not_requested():
    assert _remaining(_obj(withhold_from_tns=True), ["Hermes"]) == ["Hermes"]


def _classification(
    ml=False, groups=(1,), tns_name="2026abc", withheld=False, probability=None
):
    obj = types.SimpleNamespace(
        id="ZTF26abc", tns_name=tns_name, withhold_from_tns=withheld
    )
    return types.SimpleNamespace(
        id=1,
        ml=ml,
        probability=probability,
        obj=obj,
        author_id=7,
        groups=[types.SimpleNamespace(id=g) for g in groups],
    )


def test_a_human_classification_on_a_known_object_is_reportable():
    assert classification_is_reportable(_classification()) is True


def test_a_machine_classification_is_never_reportable():
    # ML classifications stay off TNS until someone decides otherwise.
    assert classification_is_reportable(_classification(ml=True)) is False


def test_a_zero_probability_classification_is_not_reportable():
    # p=0 says the object is not that class; the queue would report another one.
    assert classification_is_reportable(_classification(probability=0)) is False
    assert classification_is_reportable(_classification(probability=0.8)) is True


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


def test_the_flag_records_who_touched_it_and_when():
    obj = _obj(withhold_from_tns_set_by_id=None, withhold_from_tns_set_at=None)
    update_withhold_from_tns_if_relevant(
        {"withhold_from_tns": True}, obj, types.SimpleNamespace(id=7)
    )
    assert obj.withhold_from_tns_set_by_id == 7
    assert obj.withhold_from_tns_set_at is not None
    # Naive UTC, matching the column and the rest of objs.
    assert obj.withhold_from_tns_set_at.tzinfo is None


def test_clearing_the_flag_is_recorded_too():
    # Who un-withheld an object is as much the question as who withheld it.
    obj = _obj(withhold_from_tns_set_by_id=7, withhold_from_tns_set_at=None)
    update_withhold_from_tns_if_relevant(
        {"withhold_from_tns": False}, obj, types.SimpleNamespace(id=9)
    )
    assert obj.withhold_from_tns_set_by_id == 9


def test_an_unrelated_patch_leaves_the_record_alone():
    obj = _obj(withhold_from_tns_set_by_id=7, withhold_from_tns_set_at="earlier")
    update_withhold_from_tns_if_relevant(
        {"redshift": 0.1}, obj, types.SimpleNamespace(id=9)
    )
    assert obj.withhold_from_tns_set_by_id == 7
    assert obj.withhold_from_tns_set_at == "earlier"
