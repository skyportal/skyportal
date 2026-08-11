from datetime import timedelta

import arrow
import sqlalchemy as sa
from sqlalchemy.orm import selectinload

from baselayer.app.access import auth_or_token
from baselayer.log import make_log

from ....models import Filter, GcnEvent, Group, Source, SourcesConfirmedInGCN
from ....models.candidate import Candidate
from ....models.scan_report.scan_report import ScanReport
from ....utils.naive_datetime import utcnow_naive
from ...base import BaseHandler
from .scan_report_item import create_scan_report_items

log = make_log("api/scan_report")


async def get_sources_by_objs_in_range(
    session, group_ids, passed_filters_range, saved_range, gcn_event_dateobs=None
):
    """
    Retrieve all candidates saved as source in given range by object
    Parameters
    ----------
    session: sqlalchemy.orm.Session
        The database session
    group_ids: list
        The group ids to filter the candidates
    passed_filters_range: dict
        The range between which the candidates passed the filters
    saved_range: dict
        The range between which the candidates were saved as sources
    Returns
    -------
    list of tuples (obj_id, source_ids)
    """
    try:
        # Coerce the ISO strings to datetimes so the DB compares timestamps, not text.
        def to_datetime(value):
            return (
                arrow.get(value).to("utc").datetime.replace(tzinfo=None)
                if value
                else None
            )

        # An obj qualifies if it has a Source saved to a report group in the saved
        # window AND a Candidate that passed one of those groups' filters in the
        # passed window. The candidate side is a correlated EXISTS rather than a join
        # so an obj with many candidate rows over a long window doesn't blow up the
        # result combinatorially (Source x Candidate is a many-to-many on obj_id).
        candidate_passed = (
            sa.select(1)
            .select_from(Candidate)
            .join(Filter, Filter.id == Candidate.filter_id)
            .where(
                Candidate.obj_id == Source.obj_id,
                Filter.group_id.in_(group_ids),
                Candidate.passed_at.between(
                    to_datetime(passed_filters_range.get("start_date")),
                    to_datetime(passed_filters_range.get("end_date")),
                ),
            )
            .exists()
        )
        conditions = [
            Source.group_id.in_(group_ids),
            Source.saved_at.between(
                to_datetime(saved_range.get("start_saved_date")),
                to_datetime(saved_range.get("end_saved_date")),
            ),
            Source.active.is_(True),
            candidate_passed,
        ]

        if gcn_event_dateobs:
            # Scope to one GCN event through the association the crossmatch
            # records, not by re-testing the localization: containment alone
            # would also sweep in sources that merely sit in the error circle.
            conditions.append(
                sa.select(1)
                .select_from(SourcesConfirmedInGCN)
                .where(
                    SourcesConfirmedInGCN.obj_id == Source.obj_id,
                    SourcesConfirmedInGCN.dateobs == gcn_event_dateobs,
                )
                .exists()
            )

        result = await session.execute(
            sa.select(
                Source.obj_id,
                sa.func.array_agg(sa.func.distinct(Source.id)).label("source_ids"),
            )
            .where(*conditions)
            .group_by(Source.obj_id)
        )
        return result.all()
    except Exception as e:
        log(f"Error while retrieving saved candidates: {e}")
        return []


class ScanReportHandler(BaseHandler):
    @auth_or_token
    async def post(self):
        """
        ---
        summary: Populate the candidate scanning report with all saved candidates in a given range
        tags:
          - report
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  group_ids:
                    type: array
                    items:
                      type: integer
                    description: groups use to filter the candidates and manage the report
                  passed_filters_range:
                    type: object
                    properties:
                      start_date:
                        type: string
                        format: date-time
                        description: Start date of the passed filters range
                      end_date:
                        type: string
                        format: date-time
                        description: End date of the passed filters range
                    saved_candidates_range:
                      type: object
                      properties:
                        start_saved_date:
                          type: string
                          format: date-time
                          description: Start date of the saved candidates range
                        end_saved_date:
                          type: string
                          format: date-time
                          description: End date of the saved candidates range
                  passed_filters_window_hours:
                    type: number
                    description: |
                      Alternative to passed_filters_range: a rolling window of this
                      many hours ending now. Ignored if passed_filters_range is given.
                      Lets a recurring caller generate reports on a schedule.
                  saved_candidates_window_hours:
                    type: number
                    description: |
                      Alternative to saved_candidates_range: a rolling window of this
                      many hours ending now. Ignored if saved_candidates_range is given.
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
                              $ref: '#/components/schemas/ScanReport'
            400:
                content:
                  application/json:
                    schema: Error
        """
        data = self.get_json()

        async with self.AsyncSession() as session:
            group_ids = data.get("group_ids")
            if not group_ids:
                return self.error("No groups provided")

            # Rolling windows (in hours) resolve to absolute ranges ending "now", so a
            # recurring caller (e.g. RecurringAPI) can generate reports on a schedule
            # without a stale, hardcoded window. Absolute ranges take precedence.
            now = utcnow_naive()

            def rolling_range(window, start_key, end_key):
                return {
                    start_key: (now - timedelta(hours=window)).isoformat(),
                    end_key: now.isoformat(),
                }

            passed_filters_range = data.get("passed_filters_range")
            if not passed_filters_range:
                window = data.get("passed_filters_window_hours")
                if window is not None:
                    try:
                        window = float(window)
                    except (TypeError, ValueError):
                        return self.error(
                            "passed_filters_window_hours must be a number of hours"
                        )
                    passed_filters_range = rolling_range(
                        window, "start_date", "end_date"
                    )
            if not passed_filters_range:
                return self.error("No passed filters range provided")

            saved_range = data.get("saved_candidates_range")
            if not saved_range:
                window = data.get("saved_candidates_window_hours")
                if window is not None:
                    try:
                        window = float(window)
                    except (TypeError, ValueError):
                        return self.error(
                            "saved_candidates_window_hours must be a number of hours"
                        )
                    saved_range = rolling_range(
                        window, "start_saved_date", "end_saved_date"
                    )
            if not saved_range:
                return self.error("No saved candidates range provided")

            # Optional: restrict the report to objects the crossmatch associated
            # with one GCN event.
            gcn_event_dateobs = data.get("gcn_event_dateobs")
            if gcn_event_dateobs:
                try:
                    gcn_event_dateobs = arrow.get(gcn_event_dateobs).naive
                except Exception:
                    return self.error(
                        f"Invalid gcn_event_dateobs: {data.get('gcn_event_dateobs')}"
                    )
                event = await session.scalar(
                    GcnEvent.select(session.user_or_token).where(
                        GcnEvent.dateobs == gcn_event_dateobs
                    )
                )
                if event is None:
                    return self.error("GCN event not found or not accessible")

            # Check if this report already exists
            existing_result = await session.scalars(
                ScanReport.select(session.user_or_token)
                .options(selectinload(ScanReport.groups))
                .where(
                    ScanReport.groups.any(Group.id.in_(group_ids)),
                    ScanReport.options["passed_filters_range"] == passed_filters_range,
                    ScanReport.options["saved_candidates_range"] == saved_range,
                    ScanReport.options["gcn_event_dateobs"].astext
                    == (gcn_event_dateobs.isoformat() if gcn_event_dateobs else None),
                )
            )
            for report in existing_result.all():
                existing_report_group_ids = [g.id for g in report.groups]
                if set(existing_report_group_ids) == set(group_ids):
                    return self.error(
                        "This report already exists for the given groups and options"
                    )

            try:
                sources_by_objs = await get_sources_by_objs_in_range(
                    session,
                    group_ids,
                    passed_filters_range,
                    saved_range,
                    gcn_event_dateobs=gcn_event_dateobs,
                )
            except Exception:
                return self.error("Error while retrieving candidates")

            if not sources_by_objs:
                return self.error("No saved sources found for the given options")

            groups_result = await session.scalars(
                Group.select(session.user_or_token).where(Group.id.in_(group_ids))
            )
            groups = groups_result.all()

            if len(groups) != len(group_ids):
                return self.error("Some groups provided do not exist")

            scan_report = ScanReport(
                author_id=self.associated_user_object.id,
                groups=groups,
                options={
                    "passed_filters_range": passed_filters_range,
                    "saved_candidates_range": saved_range,
                    "gcn_event_dateobs": (
                        gcn_event_dateobs.isoformat() if gcn_event_dateobs else None
                    ),
                },
            )

            session.add(scan_report)

            scan_report_items = await create_scan_report_items(
                session,
                scan_report,
                sources_by_objs,
                gcn_event_dateobs=gcn_event_dateobs,
            )
            for scan_report_item in scan_report_items:
                session.add(scan_report_item)
                scan_report.items.append(scan_report_item)
            await session.commit()

            self.push_all("skyportal/REFRESH_SCAN_REPORTS")

            return self.success()

    @auth_or_token
    async def get(self):
        """
        ---
        summary: Retrieve multiple scanning reports
        tags:
          - report
        parameters:
          - in: query
            name: numPerPage
            schema:
              type: integer
            description: Number of items to return
          - in: query
            name: page
            schema:
              type: integer
            description: Page number to return
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
                          type: object
                          properties:
                            reports:
                              type: array
                              items:
                                $ref: '#/components/schemas/ScanReport'
                            totalMatches:
                              type: integer
                            pageNumber:
                              type: integer
                            numPerPage:
                              type: integer
          400:
            content:
              application/json:
                schema: Error
        """
        rows = self.get_query_argument("numPerPage", 10, type=int) or 10
        page = self.get_query_argument("page", 1, type=int) or 1

        async with self.AsyncSession() as session:
            base_stmt = ScanReport.select(session.user_or_token, mode="read")
            total_matches = await session.scalar(
                sa.select(sa.func.count()).select_from(base_stmt.subquery())
            )
            result = await session.scalars(
                base_stmt.options(
                    selectinload(ScanReport.groups),
                    selectinload(ScanReport.author),
                )
                .order_by(ScanReport.created_at.desc())
                .limit(rows)
                .offset(rows * (page - 1))
            )
            items = result.unique().all()

            # Add the author username to each scanning report
            items_dict = [
                {**scan_report.to_dict(), "author": scan_report.author.username}
                for scan_report in items
            ]

            return self.success(
                data={
                    "reports": items_dict,
                    "totalMatches": total_matches,
                    "pageNumber": page,
                    "numPerPage": rows,
                }
            )
