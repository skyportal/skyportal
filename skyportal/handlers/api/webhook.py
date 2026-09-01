from typing import Annotated

from pydantic import Field
from skyportal_py_models.analysis import AnalysisWebhookPostBody
from sqlalchemy.orm import selectinload

from baselayer.app import models as baselayer_models
from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ...models import Annotation, ObjAnalysis
from ...utils.naive_datetime import utcnow_naive
from ..base import BaseHandler
from .candidate.candidate import (
    update_summary_history_if_relevant,
)

log = make_log("app/webhook")

_, cfg = load_env()


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

        if analysis_resource_type.lower() not in ["obj"]:
            return self.error("Invalid analysis resource type", status=403)

        async with baselayer_models.async_plain_session_factory() as session:
            try:
                analysis = await session.scalar(sa_select_analysis_by_token(token))
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
            # than piling up; default the origin to the service name.
            await _upsert_analysis_annotations(session, analysis, results)

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
                        summary = {
                            "summary": analysis.serialize_results_data()["summary"]
                        }
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
                else:
                    if analysis_resource_type.lower() == "obj":
                        flow.push(
                            "*",
                            "skyportal/REFRESH_OBJ_ANALYSES",
                            payload={"obj_key": analysis.obj.internal_key},
                        )
            except Exception as e:
                log(f"Error pushing update to source: {e}")

        return self.success(data={"status": "success"})


async def _upsert_analysis_annotations(session, analysis, results):
    """Create or refresh the annotations an analysis service returned.

    Each entry is ``{"data": {...}, "origin": <optional>}``; the origin defaults
    to the service name and one annotation is kept per origin, so a re-run
    refreshes in place and the source page reads the latest.
    """
    import sqlalchemy as sa

    annotations = results.get("annotations") if isinstance(results, dict) else None
    for ann in annotations or []:
        if not isinstance(ann, dict) or not isinstance(ann.get("data"), dict):
            continue
        origin = ann.get("origin") or analysis.analysis_service.name
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


def sa_select_analysis_by_token(token):
    """Build the eager-loaded SELECT for the analysis row keyed by token."""
    import sqlalchemy as sa

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
