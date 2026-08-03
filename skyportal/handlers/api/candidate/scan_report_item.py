from collections import defaultdict

from astropy.time import Time
from sqlalchemy.orm import joinedload, selectinload

from baselayer.app.access import auth_or_token
from baselayer.log import make_log

from ....models import (
    Allocation,
    ClassicalAssignment,
    Comment,
    FollowupRequest,
    Obj,
    ObservingRun,
    Photometry,
    Source,
)
from ....models.scan_report.scan_report_item import ScanReportItem
from ....utils.parse import safe_round
from ...base import BaseHandler

log = make_log("api/scan_report_item")


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
    detections,
    comment,
    now_mjd,
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

    # First and peak detection per survey (instrument), with how long ago each was
    # recorded. A detection is a point with a measured magnitude (flux > 0).
    detections_by_survey = {}
    if detections:
        by_survey = defaultdict(list)
        for point in detections:
            by_survey[point.instrument.name].append(point)

        def _detection(point):
            return {
                "mag": safe_round(point.mag, 3),
                "mjd": safe_round(point.mjd, 5),
                "days_ago": safe_round(now_mjd - point.mjd, 2),
            }

        for survey, points in by_survey.items():
            detections_by_survey[survey] = {
                "first": _detection(min(points, key=lambda p: p.mjd)),
                "peak": _detection(min(points, key=lambda p: p.mag)),
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
        },
    )


async def create_scan_report_items(session, report, sources_by_objs):
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

    obj_ids = [obj_id for obj_id, _ in valid]
    source_ids = [sid for _, sids in valid for sid in sids]
    user_or_token = session.user_or_token

    objs = {
        obj.id: obj
        for obj in (
            await session.scalars(
                Obj.select(user_or_token, mode="read")
                .options(
                    selectinload(Obj.photstats),
                    selectinload(Obj.classifications),
                )
                .where(Obj.id.in_(obj_ids))
            )
        ).all()
    }

    # Each of the following is grouped by obj_id; access rules are applied per model.
    sources_by_obj = defaultdict(list)
    for source in (
        await session.scalars(
            Source.select(user_or_token, mode="read")
            .options(selectinload(Source.saved_by), selectinload(Source.group))
            .where(Source.obj_id.in_(obj_ids), Source.id.in_(source_ids))
        )
    ).all():
        sources_by_obj[source.obj_id].append(source)

    followups_by_obj = defaultdict(list)
    for followup in (
        await session.scalars(
            FollowupRequest.select(user_or_token, mode="read")
            .options(
                joinedload(FollowupRequest.allocation).joinedload(
                    Allocation.instrument
                ),
                joinedload(FollowupRequest.requester),
            )
            .where(FollowupRequest.obj_id.in_(obj_ids))
            .order_by(FollowupRequest.created_at.desc())
        )
    ).all():
        followups_by_obj[followup.obj_id].append(followup)

    assignments_by_obj = defaultdict(list)
    for assignment in (
        await session.scalars(
            ClassicalAssignment.select(user_or_token, mode="read")
            .options(
                joinedload(ClassicalAssignment.run).joinedload(ObservingRun.instrument),
                joinedload(ClassicalAssignment.requester),
            )
            .where(ClassicalAssignment.obj_id.in_(obj_ids))
            .order_by(ClassicalAssignment.created_at.desc())
        )
    ).all():
        assignments_by_obj[assignment.obj_id].append(assignment)

    detections_by_obj = defaultdict(list)
    for point in (
        await session.scalars(
            Photometry.select(user_or_token, mode="read")
            .options(joinedload(Photometry.instrument))
            .where(Photometry.obj_id.in_(obj_ids), Photometry.mag.isnot(None))
        )
    ).all():
        detections_by_obj[point.obj_id].append(point)

    # Most recent non-bot comment left by the scanner, per obj (newest first).
    comment_by_obj = {}
    for comment in (
        await session.scalars(
            Comment.select(user_or_token, mode="read")
            .where(
                Comment.obj_id.in_(obj_ids),
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
                detections_by_obj.get(obj_id, []),
                comment_by_obj.get(obj_id),
                now_mjd,
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
