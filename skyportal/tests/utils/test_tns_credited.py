"""Who a TNS report credits as observer and reducer.

TNS refuses a classification report whose spectrum names no observer. A
robotic instrument observes nothing by hand, so its spectra arrive with none
and the instrument's own default is what keeps the field filled.
"""

import types

from skyportal.utils.tns_submission import _credited


def _person(first, last):
    return types.SimpleNamespace(first_name=first, last_name=last)


def test_free_text_wins_over_everything():
    # A spectrum carrying an external observer names someone not in SkyPortal.
    assert _credited("Guest Observer", [_person("Ada", "Lovelace")], "Robot") == (
        "Guest Observer"
    )


def test_linked_users_win_over_the_instrument_default():
    assert _credited(None, [_person("Ada", "Lovelace")], "SEDmRobot") == "Ada Lovelace"


def test_several_linked_users_are_listed():
    people = [_person("Ada", "Lovelace"), _person("Grace", "Hopper")]
    assert _credited(None, people) == "Ada Lovelace, Grace Hopper"


def test_the_instrument_default_fills_an_otherwise_empty_field():
    # The SEDM case: no external observer, no linked users.
    assert _credited(None, [], "SEDmRobot") == "SEDmRobot"
    assert _credited(None, None, "SEDmRobot") == "SEDmRobot"


def test_no_one_anywhere_gives_an_empty_string_not_none():
    # TNS wants the key present; None would serialize as null.
    assert _credited(None, []) == ""
    assert _credited(None, None, None) == ""


def test_a_half_named_person_does_not_leave_stray_spacing():
    assert _credited(None, [_person("Cher", None)]) == "Cher"
    assert _credited(None, [_person(None, "Hopper")]) == "Hopper"


def test_the_reducer_takes_no_instrument_default():
    # Only the observer is defaulted; a missing reducer is allowed by TNS.
    assert _credited(None, []) == ""
