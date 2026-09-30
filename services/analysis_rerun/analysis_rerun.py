"""Fire default analyses that were deferred for too-sparse a light curve, once the
object has enough photometry to classify.

Default analyses fire once, on save-to-group (create_default_analysis_on_save), and
never again -- and a default analysis that declares a detection threshold
(min_detections in its parameters) is *deferred* rather than submitted when the
light curve is too sparse, so no doomed OSG job runs (see _run_default_analysis /
_insufficient_photometry). Those deferred sources leave no analysis record, so this
service periodically finds sources saved to such a default analysis's group that now
meet the threshold and have no successful (or in-flight) run yet, and fires the
default analysis -- which now passes the gate and submits. Once a good run lands,
the source is skipped.
"""

import time
import traceback
from datetime import timedelta

import sqlalchemy as sa

from baselayer.app.env import load_env
from baselayer.app.models import DBSession, init_db
from baselayer.log import make_log
from skyportal.models import DefaultAnalysis, ObjAnalysis, Photometry, Source
from skyportal.models.analysis import (
    _default_analysis_gated,
    _default_analysis_under_limit,
    _insufficient_photometry,
    _run_default_analysis,
)
from skyportal.utils.naive_datetime import utcnow_naive
from skyportal.utils.services import check_loaded

env, cfg = load_env()

init_db(**cfg["database"])

log = make_log("analysis_rerun")

_RR = cfg.get("analysis_rerun", {}) or {}
INTERVAL = int(_RR.get("interval_seconds", 3600))
LOOKBACK_DAYS = int(_RR.get("lookback_days", 14))


def _sweep_default_analysis(session, default_analysis, cutoff):
    group_id = (default_analysis.source_filter or {}).get("group_id")
    if group_id is None:
        return

    # Sources saved to the group with recent photometry (so we only look at ones
    # that could have crossed the threshold) and no run that already blocks a
    # re-fire: a pending run (in flight) or a completed, non-gated one (classified).
    recent_objs = (
        sa.select(Photometry.obj_id).where(Photometry.created_at >= cutoff).distinct()
    )
    blocking = sa.exists().where(
        ObjAnalysis.obj_id == Source.obj_id,
        ObjAnalysis.analysis_service_id == default_analysis.analysis_service_id,
        sa.or_(
            ObjAnalysis.status == "pending",
            sa.and_(
                ObjAnalysis.status == "completed",
                ~sa.func.coalesce(ObjAnalysis.status_message, "").ilike(
                    "%insufficient_data%"
                ),
            ),
        ),
    )
    obj_ids = session.scalars(
        sa.select(Source.obj_id)
        .distinct()
        .where(
            Source.group_id == int(group_id),
            Source.obj_id.in_(recent_objs),
            ~blocking,
        )
    ).all()

    for obj_id in obj_ids:
        # _run_default_analysis re-checks the gate and only submits if sufficient;
        # skip the ones still too sparse so we don't churn through them each sweep.
        if _insufficient_photometry(session, default_analysis, obj_id):
            continue
        log(f"firing {default_analysis.analysis_service.name} on {obj_id}")
        _run_default_analysis(
            default_analysis.id,
            default_analysis.author_id,
            obj_id,
            f"Deferred {default_analysis.analysis_service.name} on {obj_id}: "
            "light curve now meets the detection threshold",
        )


def sweep():
    cutoff = utcnow_naive() - timedelta(days=LOOKBACK_DAYS)
    with DBSession() as session:
        default_analyses = session.scalars(
            sa.select(DefaultAnalysis).where(
                # Only ones that opt into the detection gate.
                _default_analysis_gated(),
                _default_analysis_under_limit(),
            )
        ).all()
        log(f"{len(default_analyses)} gated default analysis(es) to sweep")
        for default_analysis in default_analyses:
            try:
                _sweep_default_analysis(session, default_analysis, cutoff)
            except Exception as e:
                log(f"error on default analysis {default_analysis.id}: {e}")
                traceback.print_exc()


@check_loaded(logger=log)
def service(*args, **kwargs):
    while True:
        try:
            sweep()
        except Exception as e:
            log(e)
            traceback.print_exc()
        time.sleep(INTERVAL)


if __name__ == "__main__":
    service()
