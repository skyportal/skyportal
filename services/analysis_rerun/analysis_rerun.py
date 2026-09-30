"""Re-run default analyses that were withheld for insufficient data, once the
light curve has grown enough to classify.

Default analyses fire once, on save-to-group (see create_default_analysis_on_save),
and never again -- so a source saved with two detections is frozen at that data.
Classifiers that gate on a sparse light curve (ORACLE, FLARE) mark the run
``insufficient_data`` in the webhook message (stored in ObjAnalysis.status_message).
This service periodically finds those gated runs whose object now meets the
detection threshold and re-triggers the same default analysis, which posts the
confident classification. Once a non-gated run lands, the object is skipped.
"""

import time
import traceback
from datetime import timedelta

import sqlalchemy as sa
from sqlalchemy import Integer

from baselayer.app.env import load_env
from baselayer.app.models import DBSession, init_db
from baselayer.log import make_log
from skyportal.models import DefaultAnalysis, ObjAnalysis, Photometry, Source
from skyportal.models.analysis import _default_analysis_under_limit, _run_default_analysis
from skyportal.utils.naive_datetime import utcnow_naive
from skyportal.utils.services import check_loaded

env, cfg = load_env()

init_db(**cfg["database"])

log = make_log("analysis_rerun")

_RR = cfg.get("analysis_rerun", {}) or {}
INTERVAL = int(_RR.get("interval_seconds", 3600))
LOOKBACK_DAYS = int(_RR.get("lookback_days", 14))
# Match the classifier bridges' gate (oracle_bridge/flare_bridge): >=N detections
# with >=2 each in g and r, counted at >=5 sigma.
MIN_DETECTIONS = int(_RR.get("min_detections", 8))
MIN_PER_BAND = int(_RR.get("min_per_band", 2))
DETECTION_SNR = float(_RR.get("detection_snr", 5.0))

# The marker a gated run leaves in ObjAnalysis.status_message (ORACLE's withheld
# message and FLARE's triage verdict both contain it).
MARKER = "insufficient_data"

_G = {"ztfg", "g"}
_R = {"ztfr", "r"}
_DET = {"ztfg", "ztfr", "ztfi", "g", "r", "i"}


def _sufficient(session, obj_id, min_detections, min_per_band):
    """(enough?, total, g, r) from the object's >=5-sigma ZTF detections."""
    counts = dict(
        session.execute(
            sa.select(Photometry.filter, sa.func.count())
            .where(Photometry.obj_id == obj_id, Photometry.snr >= DETECTION_SNR)
            .group_by(Photometry.filter)
        ).all()
    )
    g = sum(n for f, n in counts.items() if f in _G)
    r = sum(n for f, n in counts.items() if f in _R)
    total = sum(n for f, n in counts.items() if f in _DET)
    return total >= min_detections and g >= min_per_band and r >= min_per_band, total, g, r


def _maybe_rerun(session, obj_id, service_id):
    # Only act if the LATEST run for this (obj, service) is a completed, gated one:
    # a pending re-run or an already-classified (non-gated) run means skip.
    latest = session.scalars(
        sa.select(ObjAnalysis)
        .where(
            ObjAnalysis.obj_id == obj_id,
            ObjAnalysis.analysis_service_id == service_id,
        )
        .order_by(ObjAnalysis.created_at.desc())
    ).first()
    if latest is None or latest.status != "completed":
        return
    if MARKER not in (latest.status_message or ""):
        return

    group_ids = session.scalars(
        sa.select(Source.group_id).where(Source.obj_id == obj_id)
    ).all()
    if not group_ids:
        return
    default_analysis = session.scalars(
        sa.select(DefaultAnalysis).where(
            DefaultAnalysis.analysis_service_id == service_id,
            DefaultAnalysis.source_filter["group_id"].astext.cast(Integer).in_(group_ids),
            _default_analysis_under_limit(),
        )
    ).first()
    if default_analysis is None:
        return

    # The DefaultAnalysis is the source of truth for the threshold (the classifier
    # bridge reads the same params); the config values are only a fallback.
    da_params = default_analysis.default_analysis_parameters or {}
    min_detections = int(da_params.get("min_detections", MIN_DETECTIONS))
    min_per_band = int(da_params.get("min_per_band", MIN_PER_BAND))
    ok, total, g, r = _sufficient(session, obj_id, min_detections, min_per_band)
    if not ok:
        return  # still too sparse; nothing changed since the gated run

    log(
        f"re-running {default_analysis.analysis_service.name} on {obj_id} "
        f"({total} det, g={g} r={r}) -- was {MARKER}"
    )
    _run_default_analysis(
        default_analysis.id,
        default_analysis.author_id,
        obj_id,
        f"Re-run of {default_analysis.analysis_service.name} on {obj_id}: "
        f"light curve now has {total} detections",
    )


def sweep():
    cutoff = utcnow_naive() - timedelta(days=LOOKBACK_DAYS)
    with DBSession() as session:
        pairs = session.execute(
            sa.select(ObjAnalysis.obj_id, ObjAnalysis.analysis_service_id)
            .where(
                ObjAnalysis.status == "completed",
                ObjAnalysis.status_message.ilike(f"%{MARKER}%"),
                ObjAnalysis.modified >= cutoff,
            )
            .distinct()
        ).all()
        log(f"{len(pairs)} gated (obj, service) pair(s) in the last {LOOKBACK_DAYS}d")
        for obj_id, service_id in pairs:
            try:
                _maybe_rerun(session, obj_id, service_id)
            except Exception as e:
                log(f"error on {obj_id}/{service_id}: {e}")
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
