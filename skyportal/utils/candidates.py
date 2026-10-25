import sqlalchemy as sa

from ..models import Candidate, Obj, Source


def stale_unsaved_candidates(cutoff):
    return sa.and_(
        sa.exists().where(Candidate.obj_id == Obj.id),
        ~sa.exists().where(Candidate.obj_id == Obj.id, Candidate.passed_at >= cutoff),
        ~sa.exists().where(Source.obj_id == Obj.id, Source.active.is_(True)),
    )
