from collections import defaultdict

from astropy.time import Time
from sqlalchemy.orm import joinedload, selectinload

from baselayer.app.access import auth_or_token
from baselayer.log import make_log

from ....models import (
    Allocation,
    Annotation,
    ClassicalAssignment,
    Comment,
    FollowupRequest,
    Obj,
    ObservingRun,
    Source,
    SourcesConfirmedInGCN,
)
from ....models.scan_report.scan_report_item import ScanReportItem
from ....utils.gcn_crossmatch import ANNOTATION_ORIGIN as GCN_CROSSMATCH_ORIGIN
from ....utils.parse import safe_round
from ...base import BaseHandler

log = make_log("api/scan_report_item")


def _survey_of(bandpass):
    """Map a bandpass name to its survey label for the detections summary."""
    if not bandpass:
        return None
    b = bandpass.lower()
    if b.startswith("ztf"):
        return "ZTF"
    if b.startswith("lsst"):
        return "LSST"
    return bandpass


def _followup_request_type(allocation, instrument):
    """Classify a follow-up request as forced photometry, spectroscopy or photometry."""
    if allocation and allocation.types and "forced_photometry" in allocation.types:
        return "forced_photometry"
    if instrument and instrument.type in ("spectrograph", "imaging spectrograph"):
        return "spectroscopy"
    return "photometry"


def _build_scan_report_item(
    report,
    obj,
    sources,
    followup_requests,
    assignment_rows,
    comment,
    now_mjd,
    gcn_match=None,
):
    """Build a report item from data already fetched for this obj (no queries)."""
    if obj.photstats:
        current_filter = obj.photstats[0].last_detected_filter
        current_mag = obj.photstats[0].last_detected_mag
        current_age = now_mjd - obj.photstats[0].first_detected_mjd
        dm = obj.dm
        abs_mag = current_mag - dm if dm else None
    else:
        current_filter = None
        current_mag = None
        current_age = None
        abs_mag = None

    classifications = None
    if obj.classifications:
        classifications = [
            {
                "probability": classification.probability,
                "classification": classification.classification,
                "ml": classification.ml,
            }
            for classification in obj.classifications
        ]

    saved_info = None
    if sources:
        saved_info = [
            {
                "saved_at": source.saved_at.isoformat(),
                "saved_by": source.saved_by.username,
                "group": source.group.name,
            }
            for source in sources
        ]

    # Every follow-up request is kept (newest first) with its requester, so scanners
    # can see who requested what, where and at which priority.
    followups = [
        {
            "instrument": followup.instrument.name,
            "type": _followup_request_type(followup.allocation, followup.instrument),
            "priority": (followup.payload or {}).get("priority"),
            "status": followup.status,
            "requester": followup.requester.username if followup.requester else None,
        }
        for followup in followup_requests
    ] or None

    assignments = [
        {
            "instrument": assignment.run.instrument.name,
            "run_date": (
                assignment.run.calendar_date.isoformat()
                if assignment.run.calendar_date
                else None
            ),
            "priority": assignment.priority,
            "status": assignment.status,
            "requester": (
                assignment.requester.username if assignment.requester else None
            ),
        }
        for assignment in assignment_rows
    ] or None

    # First and peak detection per survey, read from the (already-loaded) PhotStat so
    # we don't scan raw photometry (which doesn't scale to long report windows).
    # PhotStat carries the global first detection and the peak per filter; a report is
    # generated per single-survey group, so the global first is that survey's first,
    # and peak per survey is the brightest across the survey's filters.
    detections_by_survey = {}
    if obj.photstats:
        ps = obj.photstats[0]

        def _entry(mjd, mag):
            if mjd is None:
                return None
            return {
                "mag": safe_round(mag, 3),
                "mjd": safe_round(mjd, 5),
                "days_ago": safe_round(now_mjd - mjd, 2),
            }

        first_entry = _entry(ps.first_detected_mjd, ps.first_detected_mag)
        first_survey = _survey_of(ps.first_detected_filter)

        peak_by_survey = {}  # survey -> (mag, mjd), brightest (min mag) across filters
        peak_mjd_per_filter = ps.peak_mjd_per_filter or {}
        for bandpass, mag in (ps.peak_mag_per_filter or {}).items():
            if mag is None:
                continue
            survey = _survey_of(bandpass)
            current = peak_by_survey.get(survey)
            if current is None or mag < current[0]:
                peak_by_survey[survey] = (mag, peak_mjd_per_filter.get(bandpass))

        for survey in set(peak_by_survey) | ({first_survey} if first_survey else set()):
            peak = peak_by_survey.get(survey)
            detections_by_survey[survey] = {
                "first": first_entry if survey == first_survey else None,
                "peak": _entry(peak[1], peak[0]) if peak else None,
            }
    detections_by_survey = detections_by_survey or None

    return ScanReportItem(
        obj_id=obj.id,
        scan_report=report,
        data={
            "tns_name": obj.tns_name,
            "comment": comment.text if comment else None,
            "host_redshift": obj.redshift,
            "current_filter": current_filter,
            "abs_mag": safe_round(abs_mag, 3),
            "current_mag": safe_round(current_mag, 3),
            "current_age": safe_round(current_age, 2),
            "classifications": classifications,
            "saved_info": saved_info,
            "followups": followups,
            "assignments": assignments,
            "detections_by_survey": detections_by_survey,
            # Present only for an event-scoped report: how this object relates to
            # the event, and the scanner's verdict on it.
            "gcn_match": gcn_match,
        },
    )


async def create_scan_report_items(
    session, report, sources_by_objs, gcn_event_dateobs=None
):
    """Build report items for many objects with a constant number of queries.

    Each data type (Obj, Source, FollowupRequest, ClassicalAssignment, Photometry,
    Comment) is fetched once for every object and grouped by obj_id, rather than
    querying once per object.

    Parameters
    ----------
    session: sqlalchemy.orm.Session
    report: skyportal.model.ScanReport
    sources_by_objs: list of tuples (obj_id, source_ids)
    Returns
    -------
    list of skyportal.model.ScanReportItem
    """
    valid = [
        (obj_id, source_ids)
        for obj_id, source_ids in sources_by_objs
        if obj_id and source_ids
    ]
    if not valid:
        return []

    user_or_token = session.user_or_token

    # For an event-scoped report, snapshot each object's relation to the event:
    # the crossmatch's own measurements plus the scanner's verdict so far.
    gcn_match_by_obj = {}
    if gcn_event_dateobs is not None:
        obj_ids = [obj_id for obj_id, _ in valid]
        verdicts = (
            await session.scalars(
                SourcesConfirmedInGCN.select(user_or_token).where(
                    SourcesConfirmedInGCN.obj_id.in_(obj_ids),
                    SourcesConfirmedInGCN.dateobs == gcn_event_dateobs,
                )
            )
        ).all()
        annotations = (
            await session.scalars(
                Annotation.select(user_or_token).where(
                    Annotation.obj_id.in_(obj_ids),
                    Annotation.origin == GCN_CROSSMATCH_ORIGIN,
                )
            )
        ).all()
        measured = {}
        want = gcn_event_dateobs.isoformat()
        for annotation in annotations:
            for payload in (annotation.data or {}).values():
                if isinstance(payload, dict) and payload.get("dateobs") == want:
                    measured[annotation.obj_id] = payload
        for verdict in verdicts:
            entry = dict(measured.pop(verdict.obj_id, {}))
            entry.update(
                {
                    "confirmed": verdict.confirmed,
                    "explanation": verdict.explanation,
                    "notes": verdict.notes,
                }
            )
            gcn_match_by_obj[verdict.obj_id] = entry
        # matched by the crossmatch but with no verdict row yet
        for obj_id, payload in measured.items():
            gcn_match_by_obj[obj_id] = {**payload, "confirmed": None}

    objs = {}
    sources_by_obj = defaultdict(list)
    followups_by_obj = defaultdict(list)
    assignments_by_obj = defaultdict(list)
    comment_by_obj = {}  # obj_id -> most recent non-bot scanner comment

    # Fetch in chunks of objects: a single ``obj_id IN (...)`` over a long report
    # window (thousands of objects) pushes the planner off the obj_id index onto a
    # seq scan of these large tables, which times out. Chunking keeps every query on
    # the index. Access rules are still applied per model.
    for chunk in (valid[i : i + 500] for i in range(0, len(valid), 500)):
        chunk_obj_ids = [obj_id for obj_id, _ in chunk]
        chunk_source_ids = [sid for _, sids in chunk for sid in sids]

        for obj in (
            await session.scalars(
                Obj.select(user_or_token, mode="read")
                .options(
                    selectinload(Obj.photstats),
                    selectinload(Obj.classifications),
                )
                .where(Obj.id.in_(chunk_obj_ids))
            )
        ).all():
            objs[obj.id] = obj

        for source in (
            await session.scalars(
                Source.select(user_or_token, mode="read")
                .options(selectinload(Source.saved_by), selectinload(Source.group))
                .where(
                    Source.obj_id.in_(chunk_obj_ids),
                    Source.id.in_(chunk_source_ids),
                )
            )
        ).all():
            sources_by_obj[source.obj_id].append(source)

        for followup in (
            await session.scalars(
                FollowupRequest.select(user_or_token, mode="read")
                .options(
                    joinedload(FollowupRequest.allocation).joinedload(
                        Allocation.instrument
                    ),
                    joinedload(FollowupRequest.requester),
                )
                .where(FollowupRequest.obj_id.in_(chunk_obj_ids))
                .order_by(FollowupRequest.created_at.desc())
            )
        ).all():
            followups_by_obj[followup.obj_id].append(followup)

        for assignment in (
            await session.scalars(
                ClassicalAssignment.select(user_or_token, mode="read")
                .options(
                    joinedload(ClassicalAssignment.run).joinedload(
                        ObservingRun.instrument
                    ),
                    joinedload(ClassicalAssignment.requester),
                )
                .where(ClassicalAssignment.obj_id.in_(chunk_obj_ids))
                .order_by(ClassicalAssignment.created_at.desc())
            )
        ).all():
            assignments_by_obj[assignment.obj_id].append(assignment)

        for comment in (
            await session.scalars(
                Comment.select(user_or_token, mode="read")
                .where(
                    Comment.obj_id.in_(chunk_obj_ids),
                    Comment.author_id == report.author_id,
                    Comment.bot.is_(False),
                )
                .order_by(Comment.created_at.desc())
            )
        ).all():
            comment_by_obj.setdefault(comment.obj_id, comment)

    now_mjd = Time.now().mjd
    items = []
    for obj_id, _source_ids in valid:
        obj = objs.get(obj_id)
        if obj is None:
            continue
        items.append(
            _build_scan_report_item(
                report,
                obj,
                sources_by_obj.get(obj_id, []),
                followups_by_obj.get(obj_id, []),
                assignments_by_obj.get(obj_id, []),
                comment_by_obj.get(obj_id),
                now_mjd,
                gcn_match=gcn_match_by_obj.get(obj_id),
            )
        )
    return items


class ScanReportItemHandler(BaseHandler):
    @auth_or_token
    async def patch(self, report_id: int, item_id: int):
        """
        ---
        summary: Update an item from a scanning report
        tags:
          - report item
        parameters:
          - in: path
            name: report_id
            required: true
            schema:
              type: integer
            description: ID of the report where the item is located
          - in: path
            name: item_id
            required: true
            schema:
              type: integer
            description: ID of the report item to update
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  comment:
                    type: string
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          $ref: '#/components/schemas/ScanReportItem'
          400:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()
        try:
            report_id = int(report_id)
            item_id = int(item_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid report_id/item_id: {report_id}/{item_id}")

        async with self.AsyncSession() as session:
            item = await session.scalar(
                ScanReportItem.select(session.user_or_token, mode="read").where(
                    ScanReportItem.id == item_id,
                    ScanReportItem.scan_report_id == report_id,
                )
            )
            if item is None:
                return self.error("Report item not found")

            item.data = {
                **item.data,
                "comment": data.get("comment"),
            }

            await session.commit()

            self.push_all(
                action="skyportal/REFRESH_SCAN_REPORT_ITEM",
                payload={"report_id": report_id},
            )
            return self.success()

    @auth_or_token
    async def get(self, report_id: int, _):
        """
        ---
        summary: Retrieve all items in a scanning report
        tags:
          - report item
        parameters:
          - in: path
            name: report_id
            required: true
            schema:
              type: integer
            description: ID of the report to retrieve items from
        responses:
          200:
            content:
              application/json:
                schema: ArrayOfScanReportItems
          400:
            content:
              application/json:
                schema: Error
        """
        try:
            report_id = int(report_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid report_id: {report_id}")
        async with self.AsyncSession() as session:
            result = await session.scalars(
                ScanReportItem.select(session.user_or_token, mode="read").where(
                    ScanReportItem.scan_report_id == report_id
                )
            )
            return self.success(data=result.all())
