"""The clauses the analysis_rerun sweep selects default analyses with."""

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

from skyportal.models import DBSession, DefaultAnalysis
from skyportal.models.analysis import (
    _default_analysis_gated,
    _default_analysis_rerun_blocked,
    _default_analysis_under_limit,
)


def compiled(clause):
    return str(clause.compile(dialect=psql.dialect()))


def test_the_gate_indexes_the_parameters_column():
    # JSONType carries no getitem comparator, so building this raised
    # NotImplementedError before the column's json type was named.
    sql = compiled(_default_analysis_gated())
    assert "default_analysis_parameters ->>" in sql
    assert "IS NOT NULL" in sql


def test_the_whole_sweep_query_builds():
    sql = compiled(
        sa.select(DefaultAnalysis).where(
            _default_analysis_gated(), _default_analysis_under_limit()
        )
    )
    assert "default_analysis_parameters ->>" in sql
    assert "stats ->>" in sql


def _rerun_blocked(analysis):
    clause = _default_analysis_rerun_blocked(
        analysis.analysis_service_id, analysis.obj_id
    )
    return DBSession().scalar(sa.select(clause))


def test_a_queued_run_blocks_a_rerun(public_obj_analysis):
    assert _rerun_blocked(public_obj_analysis)


def test_an_insufficient_run_blocks_until_a_new_detection(public_obj_analysis):
    public_obj_analysis.status = "completed"
    public_obj_analysis.status_message = "4 detections [insufficient_data]"
    DBSession().commit()
    assert _rerun_blocked(public_obj_analysis)

    public_obj_analysis.created_at = datetime(2000, 1, 1)
    DBSession().commit()
    assert not _rerun_blocked(public_obj_analysis)
