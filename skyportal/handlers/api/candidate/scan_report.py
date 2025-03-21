import sqlalchemy as sa
from sqlalchemy.orm import joinedload

from baselayer.app.access import auth_or_token
from baselayer.log import make_log

from ....models import Filter, Group, Source
from ....models.candidate import Candidate
from ....models.scan_report.scan_report import ScanReport
from ...base import BaseHandler
from .scan_report_item import create_scan_report_item

log = make_log("api/scan_report")


def get_sources_by_objs_in_range(session, group_ids, passed_filters_range, saved_range):
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
        return session.execute(
            sa.select(
                Source.obj_id,
                sa.func.array_agg(sa.func.distinct(Source.id)).label("source_ids"),
            )
            .join(Candidate, Candidate.obj_id == Source.obj_id)
            .join(Filter)
            .where(
                Source.group_id.in_(group_ids),
                Filter.group_id.in_(group_ids),
                Source.saved_at.between(
                    saved_range.get("start_saved_date"),
                    saved_range.get("end_saved_date"),
                ),
                Candidate.passed_at.between(
                    passed_filters_range.get("start_date"),
                    passed_filters_range.get("end_date"),
                ),
                Source.active.is_(True),
            )
            .group_by(Source.obj_id)
        ).all()
    except Exception as e:
        log(f"Error while retrieving saved candidates: {e}")
        return []


class ScanReportHandler(BaseHandler):
    @auth_or_token
    def post(self):
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
        data = self.get_json()

        with self.Session() as session:
            group_ids = data.get("group_ids")
            if not group_ids:
                return self.error("No groups provided")

            passed_filters_range = data.get("passed_filters_range")
            if not passed_filters_range:
                return self.error("No passed filters range provided")

            saved_range = data.get("saved_candidates_range")
            if not saved_range:
                return self.error("No saved candidates range provided")

            try:
                sources_by_objs = get_sources_by_objs_in_range(
                    session,
                    group_ids,
                    passed_filters_range,
                    saved_range,
                )
            except Exception:
                return self.error(f"Error while retrieving candidates")

            if not sources_by_objs:
                return self.error("No saved sources found for the given options")

            groups = session.scalars(
                Group.select(session.user_or_token).where(Group.id.in_(group_ids))
            ).all()

            if len(groups) != len(group_ids):
                return self.error("Some groups provided do not exist")

            scan_report = ScanReport(
                author_id=self.associated_user_object.id,
                groups=groups,
                options={
                    "passed_filters_range": passed_filters_range,
                    "saved_candidates_range": saved_range,
                },
            )

            session.add(scan_report)

            for sources_by_obj in sources_by_objs:
                scan_report_item = create_scan_report_item(
                    session, scan_report, sources_by_obj
                )

                if scan_report_item is None:
                    return self.error("Error while creating scan report item")

                session.add(scan_report_item)
                scan_report.items.append(scan_report_item)

            session.commit()

            self.push_all("skyportal/REFRESH_SCAN_REPORTS")

            return self.success()

    @auth_or_token
    def get(self):
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
                schema: ArrayOfCandidateScanReport
          400:
            content:
              application/json:
                schema: Error
        """
        try:
            rows = int(self.get_query_argument("numPerPage", default="10"))
            page = int(self.get_query_argument("page", default="1"))
        except ValueError:
            rows = 10
            page = 1

        with self.Session() as session:
            items = (
                session.scalars(
                    ScanReport.select(session.user_or_token, mode="read")
                    .options(joinedload(ScanReport.groups))
                    .order_by(ScanReport.created_at.desc())
                    .limit(rows)
                    .offset(rows * (page - 1))
                )
                .unique()
                .all()
            )

            # Add the author username to each scanning report
            items_dict = [
                {**scan_report.to_dict(), "author": scan_report.author.username}
                for scan_report in items
            ]

            return self.success(data=items_dict)
