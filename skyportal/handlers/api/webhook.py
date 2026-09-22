from typing import Annotated

from pydantic import Field
from skyportal_py_models.analysis import AnalysisWebhookPostBody
from sqlalchemy.orm import selectinload

from baselayer.app import models as baselayer_models
from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ...models import Annotation, Classification, ObjAnalysis, Taxonomy
from ...utils.embedding_store import delete_embedding, upsert_embedding
from ...utils.embedding_store_config import summary_embeddings_enabled
from ...utils.naive_datetime import utcnow_naive
from ..base import BaseHandler
from .candidate.candidate import (
    update_summary_history_if_relevant,
)

log = make_log("app/webhook")

_, cfg = load_env()

_embedding_config = (
    cfg["analysis_services.openai_analysis_service.embeddings_store.summary"] or {}
)
_EMBED_TO_PGVECTOR = summary_embeddings_enabled(_embedding_config)


class AnalysisWebhookHandler(BaseHandler):
    async def post(
        self,
        analysis_resource_type: Annotated[
            str,
            Field(
                description='What underlying data the analysis was performed on: must be "obj" (more to be added in the future)'
            ),
        ],
        token: Annotated[str, Field(description="The unique token for this analysis.")],
        *,
        body: AnalysisWebhookPostBody = None,
    ):
        """
        ---
        summary: Return the results of an analysis
        description: Return the results of an analysis
        tags:
          - analysis
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        body = self.parse_body(AnalysisWebhookPostBody)
        log(
            f"Received webhook request for Analysis type={analysis_resource_type} token={token}"
        )

        if analysis_resource_type.lower() not in ["obj", "gcn_event"]:
            return self.error("Invalid analysis resource type", status=403)

        async with baselayer_models.async_plain_session_factory() as session:
            try:
                analysis = await session.scalar(
                    sa_select_analysis_by_token(token, analysis_resource_type)
                )
                if not analysis:
                    return self.error("Invalid token", status=403)
                last_active = analysis.last_activity
                if analysis.status not in ["pending", "queued"]:
                    return self.error(
                        f"Analysis already updated with status='{analysis.status}'"
                        f" and message={analysis.status_message}",
                        status=403,
                    )
                if analysis.invalid_after and utcnow_naive() > analysis.invalid_after:
                    analysis.status = "timed_out"
                    analysis.status_message = f"Analysis timed out before webhook call at {str(utcnow_naive())}"
                    analysis.last_activity = utcnow_naive()
                    analysis.duration = (
                        analysis.last_activity - last_active
                    ).total_seconds()
                    await session.commit()
                    return self.error("Token has expired", status=400)

                # lock the analysis associated with this token and commit immediately
                # to avoid race conditions, so results are not written more than once
                analysis.status = "completed"
                analysis.last_activity = utcnow_naive()
                analysis.duration = (
                    analysis.last_activity - last_active
                ).total_seconds()
                await session.commit()
            except Exception as e:
                log(f"Trouble accessing Analysis with token {token} {e}.")
                return self.error("Invalid token", status=403)

            if (body.status or "error") != "success":
                analysis.status = "failure"
            analysis.status_message = body.message or ""

            results = body.analysis or {}
            if len(results.keys()) > 0:
                analysis._data = results
                analysis.save_data()
                log(
                    f"Saved webhook data at {analysis.filename}. Message: {analysis.status_message}"
                )
            else:
                log(
                    f"Note: empty analysis results for this webhook. Message: {analysis.status_message}"
                )

            # A service may return annotations (e.g. a period for phase-folding on
            # the source page). Upsert one per origin so a re-run refreshes rather
            # than piling up; default the origin to the service name. Obj-scoped
            # only (annotations attach to an Obj).
            made_classification = False
            if analysis_resource_type.lower() == "obj":
                await _upsert_analysis_annotations(session, analysis, results)
                made_classification = await _upsert_analysis_classifications(
                    session, analysis, results
                )

            await session.commit()

            try:
                flow = Flow()
                if analysis.analysis_service.is_summary:
                    if "Incorrect API key provided" in analysis.status_message:
                        try:
                            flow.push(
                                analysis.author_id,
                                "baselayer/SHOW_NOTIFICATION",
                                payload={
                                    "note": "Invalid OpenAI API key for this summary. If you provided your own key, please correct it and try again.",
                                    "type": "error",
                                },
                            )
                        except Exception:
                            pass
                    try:
                        summary_results = analysis.serialize_results_data()
                        summary = {"summary": summary_results["summary"]}
                    except Exception as e:
                        raise ValueError(f"Error serializing summary: {e}")
                    summary["created_at"] = analysis.created_at
                    summary["is_bot"] = True
                    summary["analysis_id"] = analysis.id
                    update_summary_history_if_relevant(
                        summary, analysis.obj, analysis.author
                    )
                    await session.commit()
                    log("analysis is a summary. Pushing to source.")
                    flow.push(
                        "*",
                        "skyportal/REFRESH_SOURCE",
                        payload={"obj_key": analysis.obj.internal_key},
                    )
                    await _store_summary_embedding(session, analysis, summary_results)
                else:
                    if analysis_resource_type.lower() == "obj":
                        flow.push(
                            "*",
                            "skyportal/REFRESH_OBJ_ANALYSES",
                            payload={"obj_key": analysis.obj.internal_key},
                        )
                        if made_classification:
                            flow.push(
                                "*",
                                "skyportal/REFRESH_SOURCE",
                                payload={"obj_key": analysis.obj.internal_key},
                            )
                    elif analysis_resource_type.lower() == "gcn_event":
                        flow.push(
                            "*",
                            "skyportal/REFRESH_GCNEVENT",
                            payload={"gcnEvent_dateobs": analysis.dateobs.isoformat()},
                        )
            except Exception as e:
                log(f"Error pushing update to source: {e}")

        return self.success(data={"status": "success"})


async def _store_summary_embedding(session, analysis, summary_results):
    """Record the vector the analysis service returned with the summary.

    Written last: a rollback here would expire everything else the handler holds.
    """
    if not _EMBED_TO_PGVECTOR:
        return
    vector = summary_results.get("embedding")
    # The service names the model it used; the config may have moved on since.
    model = summary_results.get("embedding_model")
    try:
        if vector and model:
            await session.execute(upsert_embedding(analysis.obj_id, vector, model))
        else:
            # Any vector the obj holds describes text it no longer has.
            await session.execute(delete_embedding(analysis.obj_id))
        await session.commit()
    except Exception as e:
        # A summary without its vector is missing from the search, not lost.
        await session.rollback()
        log(f"Could not store the summary embedding for {analysis.obj_id}: {e}")


async def _upsert_analysis_annotations(session, analysis, results):
    """Create or refresh the annotations an analysis service returned.

    Each entry is ``{"data": {...}, "origin": <optional>}``; the origin defaults
    to the service name and one annotation is kept per origin, so a re-run
    refreshes in place and the source page reads the latest.
    """
    import sqlalchemy as sa

    annotations = results.get("annotations") if isinstance(results, dict) else None
    # A run scoped to only the author's single-user group is private: namespace
    # its annotation origin so it neither clobbers nor leaks into the shared
    # per-service annotation, which is matched by obj_id + origin alone.
    groups = list(analysis.groups)
    is_private = len(groups) == 1 and groups[0].single_user_group
    for ann in annotations or []:
        if not isinstance(ann, dict) or not isinstance(ann.get("data"), dict):
            continue
        origin = ann.get("origin") or analysis.analysis_service.name
        if is_private:
            origin = f"{origin} [{analysis.author.username}]"
        existing = await session.scalar(
            sa.select(Annotation).where(
                Annotation.obj_id == analysis.obj_id,
                Annotation.origin == origin,
            )
        )
        if existing is not None:
            existing.data = ann["data"]
        else:
            session.add(
                Annotation(
                    obj_id=analysis.obj_id,
                    origin=origin,
                    data=ann["data"],
                    author_id=analysis.author_id,
                    groups=list(analysis.groups),
                )
            )


def _allowed_classes(hierarchy):
    if "class" in hierarchy:
        yield hierarchy["class"]
    for item in hierarchy.get("subclasses", []) or []:
        yield from _allowed_classes(item)


async def _resolve_taxonomy(session, entry):
    """The taxonomy an ML classification names, by id or (latest) name."""
    import sqlalchemy as sa

    if entry.get("taxonomy_id") is not None:
        return await session.scalar(
            sa.select(Taxonomy).where(Taxonomy.id == entry["taxonomy_id"])
        )
    name = entry.get("taxonomy")
    if not name:
        return None
    return await session.scalar(
        sa.select(Taxonomy)
        .where(Taxonomy.name == name, Taxonomy.isLatest.is_(True))
        .order_by(Taxonomy.id.desc())
    )


async def _upsert_analysis_classifications(session, analysis, results):
    """Create or refresh the ML classifications an analysis service returned.

    Each entry is ``{"taxonomy"|"taxonomy_id", "classification", "probability",
    "origin"}``; it is written as ``ml=True`` and kept one per (obj, taxonomy,
    origin) so a re-run refreshes in place. The label must be in the taxonomy, so a
    service maps its own classes onto one SkyPortal ships. Returns whether any were
    written, so the caller can refresh the source.
    """
    import sqlalchemy as sa

    entries = results.get("classifications") if isinstance(results, dict) else None
    made = False
    for entry in entries or []:
        if not isinstance(entry, dict) or not entry.get("classification"):
            continue
        taxonomy = await _resolve_taxonomy(session, entry)
        if taxonomy is None:
            log(f"FLARE/ML classification skipped: no taxonomy for {entry}")
            continue
        if entry["classification"] not in _allowed_classes(taxonomy.hierarchy):
            log(
                f"ML classification {entry['classification']!r} not in taxonomy "
                f"{taxonomy.name!r}; skipping"
            )
            continue
        origin = entry.get("origin") or analysis.analysis_service.name
        probability = entry.get("probability")
        existing = await session.scalar(
            sa.select(Classification).where(
                Classification.obj_id == analysis.obj_id,
                Classification.taxonomy_id == taxonomy.id,
                Classification.origin == origin,
            )
        )
        if existing is not None:
            existing.classification = entry["classification"]
            existing.probability = probability
            existing.ml = True
        else:
            session.add(
                Classification(
                    classification=entry["classification"],
                    obj_id=analysis.obj_id,
                    origin=origin,
                    probability=probability,
                    ml=True,
                    taxonomy_id=taxonomy.id,
                    author_id=analysis.author_id,
                    author_name=analysis.author.username,
                    groups=list(analysis.groups),
                )
            )
        made = True
    return made


def sa_select_analysis_by_token(token, analysis_resource_type="obj"):
    """Build the eager-loaded SELECT for the analysis row keyed by token."""
    import sqlalchemy as sa

    if analysis_resource_type.lower() == "gcn_event":
        from ...models import GcnEventAnalysis

        return (
            sa.select(GcnEventAnalysis)
            .where(GcnEventAnalysis.token == token)
            .options(
                selectinload(GcnEventAnalysis.analysis_service),
                selectinload(GcnEventAnalysis.gcnevent),
                selectinload(GcnEventAnalysis.author),
                selectinload(GcnEventAnalysis.groups),
            )
        )

    return (
        sa.select(ObjAnalysis)
        .where(ObjAnalysis.token == token)
        .options(
            selectinload(ObjAnalysis.analysis_service),
            selectinload(ObjAnalysis.obj),
            selectinload(ObjAnalysis.author),
            selectinload(ObjAnalysis.groups),
        )
    )
