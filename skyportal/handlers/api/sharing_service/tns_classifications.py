from datetime import timedelta

import sqlalchemy as sa
from skyportal_py_models.sharing_services import (
    TNSClassificationsGetQuery,
    TNSClassificationsResponse,
)
from sqlalchemy.orm import joinedload, selectinload, undefer

from baselayer.app.access import auth_or_token

from ....models import (
    Classification,
    GroupClassification,
    Instrument,
    Obj,
    SharingService,
    SharingServiceGroup,
    SharingServiceSubmission,
    Spectrum,
)
from ....utils.naive_datetime import utcnow_naive
from ....utils.parse import is_null
from ....utils.tns import missing_spectrum_credits, tns_classification_id
from ...base import BaseHandler


def _report(submission):
    """The classification report a submission sent, or an empty dict."""
    return ((submission.tns_payload or {}).get("classification_report") or {}).get(
        "0"
    ) or {}


def _is_queued(submission):
    return submission.tns_status in ("pending", "processing")


def _is_failed(submission):
    return (submission.tns_status or "").startswith("Error")


def _tns_classification(obj):
    info = obj.tns_info if isinstance(obj.tns_info, dict) else {}
    object_type = info.get("object_type")
    return object_type.get("name") if isinstance(object_type, dict) else None


def _reports_automatically(classification, service_groups):
    for service_group in service_groups:
        if (
            service_group.group_id in {g.id for g in classification.groups}
            and service_group.auto_share_classifications_to_tns
            and classification.author_id
            in {p.user_id for p in service_group.auto_publishers}
            and (
                not classification.author.is_bot
                or service_group.auto_sharing_allow_bots
            )
        ):
            return True
    return False


def _not_reported_reason(obj, classification, spectrum, submissions, service_groups):
    queued = next((s for s in submissions if _is_queued(s)), None)
    if queued is not None:
        if queued.tns_status == "processing":
            return "queued", "Sending"
        return "queued", "Waiting to be sent"
    if obj.withhold_from_tns:
        return "held", "Don't report to TNS is ticked"
    if submissions and _is_failed(submissions[0]):
        error = submissions[0].tns_status.removeprefix("Error:").strip()
        return "failed", f"Last report failed: {error}"
    if is_null(obj.tns_name):
        return "no_tns_name", "No TNS name"
    if spectrum is None:
        return "no_spectrum", "No spectrum"
    if tns_classification_id(classification.classification) is None:
        return "no_tns_type", f"{classification.classification} has no TNS type"
    missing = missing_spectrum_credits(spectrum)
    if missing:
        return "missing_credits", f"Spectrum has no {', '.join(missing)}"
    if not _reports_automatically(classification, service_groups):
        return "manual", "Manual report needed"
    if not spectrum.auto_report_to_tns:
        return "manual", "Manual report needed: spectrum not opted in"
    return "manual", "Manual report needed: not queued automatically"


class TNSClassificationsHandler(BaseHandler):
    @auth_or_token
    async def get(
        self, *, query: TNSClassificationsGetQuery = None
    ) -> TNSClassificationsResponse:
        """
        ---
        summary: List TNS classification reports and classifications not reported
        description: |
          Classification reports sent to TNS in the last days, and the recent
          human classifications of sources in groups that share with TNS that
          are not on TNS yet, each with the reason.
        tags:
          - external sharing service
        """
        query = self.parse_query(TNSClassificationsGetQuery)
        since = utcnow_naive() - timedelta(days=query.days)

        async with self.AsyncSession() as session:
            user = session.user_or_token
            services = (
                (
                    await session.scalars(
                        SharingService.select(user)
                        .options(
                            selectinload(SharingService.groups).selectinload(
                                SharingServiceGroup.auto_publishers
                            )
                        )
                        .where(SharingService.enable_sharing_with_tns.is_(True))
                    )
                )
                .unique()
                .all()
            )
            service_names = {s.id: s.name for s in services}
            service_groups = [g for s in services for g in s.groups]

            submissions = (
                (
                    await session.scalars(
                        SharingServiceSubmission.select(user)
                        .options(
                            undefer(SharingServiceSubmission.tns_payload),
                            joinedload(SharingServiceSubmission.obj),
                        )
                        .where(
                            SharingServiceSubmission.sharing_service_id.in_(
                                list(service_names)
                            ),
                            SharingServiceSubmission.publish_to_tns.is_(True),
                            SharingServiceSubmission.tns_report_type
                            == "classification_report",
                            SharingServiceSubmission.created_at >= since,
                        )
                        .order_by(SharingServiceSubmission.created_at.desc())
                    )
                )
                .unique()
                .all()
            )
            sent = [s for s in submissions if not _is_queued(s) and not _is_failed(s)]

            classification_names = dict(
                (
                    await session.execute(
                        sa.select(
                            Classification.id, Classification.classification
                        ).where(
                            Classification.id.in_(
                                [s.tns_report_classification_id for s in sent]
                            )
                        )
                    )
                ).all()
            )
            spectrum_instruments = dict(
                (
                    await session.execute(
                        sa.select(Spectrum.id, Instrument.name)
                        .join(Instrument)
                        .where(
                            Spectrum.id.in_([s.tns_report_spectrum_id for s in sent])
                        )
                    )
                ).all()
            )

            reported = []
            for submission in sent:
                report = _report(submission)
                redshift = report.get("redshift")
                reported.append(
                    {
                        "id": submission.id,
                        "created_at": submission.created_at,
                        "obj_id": submission.obj_id,
                        "tns_name": submission.obj.tns_name,
                        "sharing_service": service_names.get(
                            submission.sharing_service_id
                        ),
                        "user_id": submission.user_id,
                        "auto_submission": submission.auto_submission,
                        "tns_status": submission.tns_status,
                        "tns_submission_id": submission.tns_submission_id,
                        "classification": classification_names.get(
                            submission.tns_report_classification_id
                        ),
                        "redshift": (
                            redshift
                            if isinstance(redshift, int | float)
                            else submission.obj.redshift
                        ),
                        "instrument": spectrum_instruments.get(
                            submission.tns_report_spectrum_id
                        ),
                        "authors": report.get("classifier")
                        or submission.custom_publishing_string,
                    }
                )

            classifications = (
                (
                    await session.scalars(
                        Classification.select(user)
                        .options(
                            selectinload(Classification.groups),
                            selectinload(Classification.author),
                        )
                        .where(
                            Classification.ml.is_(False),
                            sa.or_(
                                Classification.probability.is_(None),
                                Classification.probability > 0,
                            ),
                            Classification.created_at >= since,
                            Classification.id.in_(
                                sa.select(GroupClassification.classification_id).where(
                                    GroupClassification.group_id.in_(
                                        [g.group_id for g in service_groups]
                                    )
                                )
                            ),
                        )
                        .order_by(Classification.created_at.desc())
                    )
                )
                .unique()
                .all()
            )
            latest = {}
            for classification in classifications:
                latest.setdefault(classification.obj_id, classification)

            objs = {
                obj.id: obj
                for obj in (
                    await session.scalars(
                        Obj.select(user).where(Obj.id.in_(list(latest)))
                    )
                )
                .unique()
                .all()
            }
            obj_submissions = {}
            for submission in (
                await session.scalars(
                    sa.select(SharingServiceSubmission)
                    .options(undefer(SharingServiceSubmission.tns_payload))
                    .where(
                        SharingServiceSubmission.obj_id.in_(list(latest)),
                        SharingServiceSubmission.publish_to_tns.is_(True),
                        SharingServiceSubmission.tns_report_type
                        == "classification_report",
                    )
                    .order_by(SharingServiceSubmission.created_at.desc())
                )
            ).all():
                obj_submissions.setdefault(submission.obj_id, []).append(submission)
            spectra = {}
            for spectrum in (
                (
                    await session.scalars(
                        Spectrum.select(user)
                        .options(
                            selectinload(Spectrum.pis),
                            selectinload(Spectrum.observers),
                            selectinload(Spectrum.reducers),
                            selectinload(Spectrum.instrument),
                        )
                        .where(Spectrum.obj_id.in_(list(latest)))
                        .order_by(
                            (Spectrum.type == "source").desc(),
                            Spectrum.observed_at.desc(),
                        )
                    )
                )
                .unique()
                .all()
            ):
                spectra.setdefault(spectrum.obj_id, spectrum)

            not_reported = []
            for obj_id, classification in latest.items():
                obj = objs.get(obj_id)
                if obj is None:
                    continue
                submissions = obj_submissions.get(obj_id, [])
                tns_type = tns_classification_id(classification.classification)
                if any(
                    not _is_queued(s)
                    and not _is_failed(s)
                    and (
                        s.created_at >= classification.created_at
                        or _report(s).get("objtypeid") == tns_type
                    )
                    for s in submissions
                ):
                    continue
                spectrum = spectra.get(obj_id)
                reason_code, reason = _not_reported_reason(
                    obj, classification, spectrum, submissions, service_groups
                )
                queued = next((s for s in submissions if _is_queued(s)), None)
                not_reported.append(
                    {
                        "obj_id": obj_id,
                        "tns_name": obj.tns_name,
                        "tns_classification": _tns_classification(obj),
                        "classification_id": classification.id,
                        "classification": classification.classification,
                        "classified_by": classification.author_name,
                        "classified_at": classification.created_at,
                        "redshift": obj.redshift,
                        "spectrum_id": spectrum.id if spectrum else None,
                        "instrument": spectrum.instrument.name if spectrum else None,
                        "reason_code": reason_code,
                        "reason": reason,
                        "tns_send_after": queued.tns_send_after if queued else None,
                    }
                )

            return self.success(
                data={"reported": reported, "not_reported": not_reported}
            )
