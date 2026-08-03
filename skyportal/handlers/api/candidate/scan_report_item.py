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


async def create_scan_report_item(session, report, sources_by_obj):
    """
    Parameters
    ----------
    session: sqlalchemy.orm.Session
    report: skyportal.model.ScanReport
        The scanning report to create an item for
    sources_by_obj: tuple (obj_id, source_ids)
        The object and link source ids to create the item for
    Returns
    -------
    scan_report_item: skyportal.model.ScanReportItem
    """
    obj_id, source_ids = sources_by_obj

    if not obj_id or not source_ids:
        return None

    obj = await session.scalar(
        Obj.select(session.user_or_token, mode="read")
        .options(
            selectinload(Obj.photstats),
            selectinload(Obj.classifications),
        )
        .where(Obj.id == obj_id)
    )

    if obj.photstats:
        current_filter = obj.photstats[0].last_detected_filter
        current_mag = obj.photstats[0].last_detected_mag
        current_age = Time.now().mjd - obj.photstats[0].first_detected_mjd
        dm = obj.dm
        abs_mag = current_mag - dm if dm else None
    else:
        current_filter = None
        current_mag = None
        current_age = None
        abs_mag = None

    sources_result = await session.scalars(
        Source.select(session.user_or_token, mode="read")
        .options(
            selectinload(Source.saved_by),
            selectinload(Source.group),
        )
        .where(Source.obj_id == obj_id, Source.id.in_(source_ids))
    )
    sources = sources_result.all()

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

    # Query follow-up requests through their own access rules so the report only
    # includes what the scanner is allowed to see (allocation group membership).
    # Every request is kept (newest first) with its requester, so scanners can see
    # who requested what, where and at which priority.
    followup_requests = (
        await session.scalars(
            FollowupRequest.select(session.user_or_token, mode="read")
            .options(
                joinedload(FollowupRequest.allocation).joinedload(
                    Allocation.instrument
                ),
                joinedload(FollowupRequest.requester),
            )
            .where(FollowupRequest.obj_id == obj_id)
            .order_by(FollowupRequest.created_at.desc())
        )
    ).all()

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

    # Observing-run assignments, also filtered by the scanner's access rules.
    assignment_rows = (
        await session.scalars(
            ClassicalAssignment.select(session.user_or_token, mode="read")
            .options(
                joinedload(ClassicalAssignment.run).joinedload(ObservingRun.instrument),
                joinedload(ClassicalAssignment.requester),
            )
            .where(ClassicalAssignment.obj_id == obj_id)
            .order_by(ClassicalAssignment.created_at.desc())
        )
    ).all()

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

    # Pre-fill the item's comment with the most recent note the scanner left on the
    # source, if any, so scanners don't have to re-enter it after generating the report.
    latest_comment = await session.scalar(
        Comment.select(session.user_or_token, mode="read")
        .where(
            Comment.obj_id == obj_id,
            Comment.author_id == report.author_id,
            Comment.bot.is_(False),
        )
        .order_by(Comment.created_at.desc())
        .limit(1)
    )

    return ScanReportItem(
        obj_id=obj.id,
        scan_report=report,
        data={
            "tns_name": obj.tns_name,
            "comment": latest_comment.text if latest_comment else None,
            "host_redshift": obj.redshift,
            "current_filter": current_filter,
            "abs_mag": safe_round(abs_mag, 3),
            "current_mag": safe_round(current_mag, 3),
            "current_age": safe_round(current_age, 2),
            "classifications": classifications,
            "saved_info": saved_info,
            "followups": followups,
            "assignments": assignments,
        },
    )


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
