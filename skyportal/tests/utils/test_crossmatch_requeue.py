"""Re-searching active events after a filter's cuts change.

A crossmatch state records how far it has got and never re-searches a window
it has covered in full. That is right while the filter holds still, and wrong
once someone edits it: without a requeue, the new cuts only ever apply to
events still to come.
"""

import datetime
import types

from skyportal.utils.gcn_crossmatch import DEFAULTS, conf, requeue_crossmatch_for_filter


class _Session:
    """Captures the UPDATE instead of running it."""

    def __init__(self, rowcount=0):
        self.statements = []
        self.rowcount = rowcount

    def execute(self, stmt):
        self.statements.append(stmt)
        return types.SimpleNamespace(rowcount=self.rowcount)


def _compiled(session):
    return str(session.statements[0].compile(compile_kwargs={"literal_binds": False}))


def test_it_resets_the_fields_that_gate_a_re_search():
    session = _Session(rowcount=3)
    requeue_crossmatch_for_filter(session, 1446)
    sql = _compiled(session)
    # last_queried is what clamps the lower bound past a closed window, and
    # archival_done is what skips the look-back.
    for column in ("status", "last_queried", "last_alert_jd", "archival_done", "error"):
        assert column in sql, column


def test_it_is_scoped_to_the_one_filter():
    session = _Session()
    requeue_crossmatch_for_filter(session, 1446)
    assert "filter_id" in _compiled(session)


def test_it_only_touches_events_still_being_polled():
    # Events past max_event_age are never queried again, so resetting them
    # would be churn.
    session = _Session()
    requeue_crossmatch_for_filter(session, 1446)
    sql = _compiled(session)
    assert "dateobs" in sql and "gcnevent_id" in sql


def test_the_age_cutoff_follows_the_instance_setting():
    assert conf({"max_event_age": 5.0}, "max_event_age") == 5.0
    assert conf({}, "max_event_age") == DEFAULTS["max_event_age"]
    assert conf(None, "max_event_age") == DEFAULTS["max_event_age"]


def test_it_reports_how_many_states_it_requeued():
    assert requeue_crossmatch_for_filter(_Session(rowcount=7), 1446) == 7
    assert requeue_crossmatch_for_filter(_Session(rowcount=0), 1446) == 0


def test_a_filter_id_given_as_a_string_still_works():
    # The handler hands over whatever the Filter row holds.
    session = _Session()
    requeue_crossmatch_for_filter(session, "1446")
    assert session.statements


def test_the_cutoff_is_in_the_past():
    # Guards against a sign error making the window exclude everything.
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(
        days=float(DEFAULTS["max_event_age"])
    )
    assert cutoff < datetime.datetime.utcnow()


def test_the_requeue_body_defaults_to_every_filter():
    from skyportal_py_models.gcn_events import GcnEventCrossmatchRequeueBody as Body

    # Omitting filter_id keeps the old behaviour, so existing callers are
    # unaffected by the scoping.
    assert Body().filter_id is None
    assert Body(filter_id=1446).filter_id == 1446


def test_the_requeue_body_rejects_what_it_cannot_use():
    import pytest
    from skyportal_py_models.gcn_events import GcnEventCrossmatchRequeueBody as Body

    with pytest.raises(Exception):
        Body(filter_id="not an id")
    with pytest.raises(Exception):
        Body(unexpected=1)
