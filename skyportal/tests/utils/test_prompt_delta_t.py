"""The prompt-candidate exemption on the sources query.

A candidate detected close in time to the event is spared the cuts meant to thin
late ones; these pin the parameter and the clause it builds.
"""

import pytest
from pydantic import ValidationError

from skyportal.handlers.api.source import SourceGetQuery
from skyportal.handlers.api.sources import (
    PROMPT_EXEMPT_ANNOTATIONS,
    _prompt_candidate_clause,
)


def test_absent_by_default():
    assert SourceGetQuery().promptDeltaT is None


def test_accepts_a_window():
    assert SourceGetQuery(promptDeltaT=2).promptDeltaT == 2


def test_refuses_a_negative_window():
    with pytest.raises(ValidationError):
        SourceGetQuery(promptDeltaT=-1)


def test_detection_history_is_exempt():
    # The history cut thins late candidates, so a prompt one is spared it.
    assert "ndethist" in PROMPT_EXEMPT_ANNOTATIONS


def test_star_score_is_not_exempt():
    # A source on a star is not a counterpart however promptly it was seen.
    assert "sgscore" not in PROMPT_EXEMPT_ANNOTATIONS


def test_clause_matches_either_side_of_the_event():
    # delta_t is signed; a detection before the event is as prompt as one after.
    params = []
    clause = _prompt_candidate_clause(2, None, None, True, None, params)
    assert "abs((value ->> 'delta_t')::float) <= :prompt_delta_t" in clause
    assert [p.key for p in params] == ["prompt_delta_t"]
    assert params[0].value == 2.0


def test_clause_scopes_to_the_event_when_given():
    params = []
    clause = _prompt_candidate_clause(
        2, None, "2025-10-31 21:07:49", True, None, params
    )
    assert "(value ->> 'dateobs')::timestamp" in clause
    assert "annotations_filter_dateobs_prompt" in {p.key for p in params}


def test_clause_restricts_to_readable_groups():
    params = []
    clause = _prompt_candidate_clause(2, None, None, False, [3, 4], params)
    assert "group_annotations" in clause


def test_clause_denies_when_no_group_is_readable():
    # An empty IN list is not valid SQL, and no readable group means no readable
    # annotation, so the clause must match nothing rather than everything.
    params = []
    clause = _prompt_candidate_clause(2, None, None, False, [], params)
    assert "AND false" in clause
