import sqlalchemy as sa

from skyportal.models import DBSession, DefaultAnalysis
from skyportal.models.analysis import _default_analysis_gated


def _is_gated(default_analysis_id):
    return (
        DBSession().scalar(
            sa.select(DefaultAnalysis.id).where(
                DefaultAnalysis.id == default_analysis_id, _default_analysis_gated()
            )
        )
        is not None
    )


def test_only_default_analyses_with_min_detections_are_gated(public_default_analysis):
    session = DBSession()
    default_analysis = session.get(DefaultAnalysis, public_default_analysis.id)
    assert not _is_gated(default_analysis.id)

    default_analysis.default_analysis_parameters = {"min_detections": 3}
    session.commit()
    assert _is_gated(default_analysis.id)
