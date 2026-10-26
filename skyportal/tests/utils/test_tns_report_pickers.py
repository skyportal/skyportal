"""Which spectrum and classification a TNS classification report carries.

Both default to the most recent, which is what the automatic path relies on; a
submitter can name one instead, and a name that does not belong to the object
selects nothing rather than someone else's data.
"""

import types

from skyportal.models import User
from skyportal.utils.tns_submission import pick_classification, pick_spectrum

# An unsaved instance is enough: the pickers only build a statement.
USER = User(id=1)


class _Session:
    """Returns a canned row and records the statement it was asked for."""

    def __init__(self, result=None):
        self.result = result
        self.statements = []

    def scalars(self, stmt):
        self.statements.append(stmt)
        return types.SimpleNamespace(first=lambda: self.result)


def _sql(session):
    return str(session.statements[-1])


def test_naming_a_classification_filters_on_its_id():
    session = _Session(result="picked")
    assert pick_classification(session, USER, "ZTF26abc", 42) == "picked"
    sql = _sql(session)
    assert "classifications.id = " in sql
    # The default's cuts must not narrow an explicit choice: a submitter who
    # names a classification means that one, machine-made or not. The ordering
    # and the ml/probability filters belong to the fallback alone.
    assert "ORDER BY" not in sql
    assert "probability" not in sql.split("WHERE")[-1]


def test_the_default_classification_excludes_machine_ones():
    session = _Session()
    pick_classification(session, USER, "ZTF26abc")
    sql = _sql(session)
    assert "ml" in sql and "created_at" in sql


def test_naming_a_spectrum_filters_on_its_id():
    session = _Session(result="picked")
    assert pick_spectrum(session, USER, "ZTF26abc", 7) == "picked"
    assert "spectra.id = " in _sql(session)


def test_the_default_spectrum_prefers_a_source_over_a_host():
    session = _Session()
    pick_spectrum(session, USER, "ZTF26abc")
    sql = _sql(session)
    assert "observed_at" in sql and "type" in sql


def test_both_pickers_scope_to_the_object():
    for picker in (pick_classification, pick_spectrum):
        session = _Session()
        picker(session, USER, "ZTF26abc")
        assert "obj_id" in _sql(session)


def test_an_id_that_does_not_match_selects_nothing():
    # The caller turns this into an error naming the choice, rather than
    # quietly falling back to the latest and reporting the wrong thing.
    assert pick_classification(_Session(result=None), USER, "ZTF26abc", 999) is None
    assert pick_spectrum(_Session(result=None), USER, "ZTF26abc", 999) is None


def test_zero_is_treated_as_a_choice_not_as_absent():
    # Guards against `if spectrum_id:` creeping in where `is not None` belongs.
    session = _Session()
    pick_spectrum(session, USER, "ZTF26abc", 0)
    assert "spectra.id = " in _sql(session)
