"""The SQL built for the scan page's GCN crossmatch cuts.

Pins that the cuts reach the per-event values rather than a top-level key, and
that `minDistpsnr` lets through the negative distance a survey reports when
there is no PS1 source to measure against.
"""

import sqlalchemy as sa

from skyportal.handlers.api.candidate.candidate import crossmatch_value_clause

ORIGIN = "GCN-crossmatch"


def compile_clause(key, comparison):
    return str(
        crossmatch_value_clause(ORIGIN, key, comparison).compile(
            compile_kwargs={"literal_binds": True}
        )
    ).lower()


def test_credible_level_reads_the_per_event_value():
    sql = compile_clause("credible_level", lambda v: v <= 0.9)
    assert "jsonb_each" in sql
    assert "credible_level" in sql
    assert "<= 0.9" in sql


def test_distpsnr_keeps_a_candidate_with_no_ps1_match():
    # A negative distance is the survey's "no match"; comparing it against the
    # minimum would drop exactly the candidates the cut is meant to keep.
    sql = compile_clause("distpsnr", lambda v: sa.or_(v < 0, v >= 2.0))
    assert "< 0" in sql
    assert ">= 2.0" in sql
    assert " or " in sql


def test_origin_is_compared_case_insensitively():
    sql = compile_clause("credible_level", lambda v: v <= 0.9)
    assert "'gcn-crossmatch'" in sql
    assert "lower(annotations.origin)" in sql
