from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import joinedload

from baselayer.app.access import auth_or_token
from baselayer.app.models import User
from baselayer.log import make_log

from ....models import Filter, Group, Obj, Source
from ....models.candidate import Candidate
from ....models.scan_report.scan_report import ScanReport
from ...base import BaseHandler
from .scan_report_item import create_scan_report_item

log = make_log("api/scan_report")


def get_infos_saved_sources_by_obj(session, group_ids, detection_range, saved_range):
    """
    Retrieve all candidates saved as source in given range by object
    Parameters
    ----------
    session: sqlalchemy.orm.Session
    group_ids: list
    detection_range: dict
    saved_range: dict

    Returns
    -------
    list of saved_infos, skyportal.models.Obj
    """
    try:
        return (
            session.query(
                Obj,
                func.json_agg(
                    func.distinct(
                        func.json_build_object(
                            "saved_at",
                            Source.saved_at,
                            "saved_by",
                            User.username,
                            "group",
                            Group.name,
                        ).cast(JSONB)
                    )
                ).label("saved_infos"),
            )
            .join(Source)
            .join(Candidate)
            .join(Filter)
            .join(User, Source.saved_by_id == User.id)
            .join(Group, Source.group_id == Group.id)
            .filter(
                Source.group_id.in_(group_ids),
                Filter.group_id.in_(group_ids),
                Source.saved_at.between(
                    saved_range.get("start_save_date"),
                    saved_range.get("end_save_date"),
                ),
                Candidate.passed_at.between(
                    detection_range.get("start_date"),
                    detection_range.get("end_date"),
                ),
                Source.active.is_(True),
            )
            .group_by(Obj)
            .all()
        )
    except Exception as e:
        log(f"Error while retrieving saved candidates: {e}")
        return []


class ScanReportHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """
        ---
        summary: Populate the candidate scan report with all saved candidates in a given range
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
                  candidates_detection_range:
                    type: object
                    properties:
                      start_date:
                        type: string
                        format: date-time
                        description: Start date of the candidate detection range
                      end_date:
                        type: string
                        format: date-time
                        description: End date of the candidate detection range
                    saved_candidates_range:
                      type: object
                      properties:
                        start_save_date:
                          type: string
                          format: date-time
                          description: Start date of the saved candidates range
                        end_save_date:
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

            detection_range = data.get("candidates_detection_range")
            if not detection_range:
                return self.error("No candidate detection range provided")

            saved_range = data.get("saved_candidates_range")
            if not saved_range:
                return self.error("No saved candidates range provided")

            try:
                saved_infos_by_obj = get_infos_saved_sources_by_obj(
                    session,
                    group_ids,
                    detection_range,
                    saved_range,
                )
            except Exception:
                return self.error(f"Error while retrieving candidates")

            if not saved_infos_by_obj:
                return self.error("No saved sources found for the given options")

            groups = session.scalars(
                Group.select(session.user_or_token).where(Group.id.in_(group_ids))
            ).all()

            if len(groups) != len(group_ids):
                return self.error("Some groups provided do not exist")

            scan_report = ScanReport(
                creator_id=self.associated_user_object.id,
                groups=groups,
                creation_options={
                    "candidates_detection_range": detection_range,
                    "saved_candidates_range": saved_range,
                },
            )

            session.add(scan_report)

            for obj, saved_infos in saved_infos_by_obj:
                scan_report_item = create_scan_report_item(
                    scan_report, obj, saved_infos
                )

                session.add(scan_report_item)
                scan_report.items.append(scan_report_item)

            session.commit()

            self.push_all("skyportal/REFRESH_SCAN_REPORTS")

            return self.success()

    @auth_or_token
    def get(self):
        """
        ---
        summary: Retrieve multiple scan reports
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

            # Add the creator username to each scan report
            items_dict = [
                {**scan_report.to_dict(), "username": scan_report.creator.username}
                for scan_report in items
            ]

            return self.success(data=items_dict)
