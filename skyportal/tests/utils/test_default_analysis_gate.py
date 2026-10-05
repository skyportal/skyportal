"""The clauses the analysis_rerun sweep selects default analyses with."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql

from skyportal.models import DefaultAnalysis
from skyportal.models.analysis import (
    _default_analysis_gated,
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
