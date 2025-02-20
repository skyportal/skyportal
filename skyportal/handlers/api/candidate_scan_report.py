from datetime import datetime

from baselayer.app.access import auth_or_token
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ...models import Obj
from ...models.candidate_scan_report import CandidateScanReport
from ..base import BaseHandler

log = make_log("api/candidate_scan_report")


class CandidateScanReportHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """
        ---
        summary: Add a candidate scan to the report
        tags:
          - report
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  obj_id:
                    type: integer
                  comment:
                    type: string
                  already_classified:
                    type: boolean
                  host_redshift:
                    type: number
                  current_age:
                    type: string
                  forced_photometry_requested:
                    type: boolean
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
        if not data.get("obj_id"):
            return self.error("No object ID provided")

        with self.Session() as session:
            obj = session.scalar(
                Obj.select(session.user_or_token, mode="read").where(
                    Obj.id == data.get("obj_id")
                )
            )
            if obj is None:
                return self.error("Object not found")

            candidate_scan_report = CandidateScanReport(
                date=datetime.now(),
                scanner=session.user_or_token.username,
                obj_id=data.get("obj_id"),
                comment=data.get("comment"),
                already_classified=data.get("already_classified"),
                host_redshift=obj.redshift,
                current_age=data.get("current_age"),
                forced_photometry_requested=data.get("forced_photometry_requested"),
                saver_id=session.user_or_token.id,
            )

            session.add(candidate_scan_report)
            session.commit()

            flow = Flow()
            flow.push("*", "skyportal/REFRESH_CANDIDATE_SCAN_REPORT")

            return self.success()

    @auth_or_token
    def patch(self, candidate_scan_report_id):
        """
        ---
        summary: Update a candidate scan from the report
        tags:
          - report
        parameters:
          - in: path
            name: candidate_scan_report_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  comment:
                    type: string
                  already_classified:
                    type: boolean
                  host_redshift:
                    type: number
                  current_age:
                    type: string
                  forced_photometry_requested:
                    type: boolean
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

        if not candidate_scan_report_id:
            return self.error("Nothing to update")

        with self.Session() as session:
            candidate_scan_report = session.scalar(
                CandidateScanReport.select(session.user_or_token, mode="read").where(
                    CandidateScanReport.id == candidate_scan_report_id,
                )
            )
            if candidate_scan_report is None:
                return self.error("Report line not found")

            for key, value in data.items():
                setattr(candidate_scan_report, key, value)

            flow = Flow()
            flow.push("*", "skyportal/REFRESH_CANDIDATE_SCAN_REPORT")

            session.commit()
            return self.success()

    @auth_or_token
    def get(self):
        """
        ---
        summary: Get all candidate scan in the report
        tags:
          - report
        parameters:
          - in: query
            name: rows
            schema:
              type: integer
            description: Number of rows to return
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
            rows = int(self.get_query_argument("rows", default="10"))
            page = int(self.get_query_argument("page", default="1"))
        except ValueError:
            rows = 10
            page = 1

        with self.Session() as session:
            candidates_scan_report = session.scalars(
                CandidateScanReport.select(session.user_or_token, mode="read")
                .order_by(CandidateScanReport.date.desc())
                .limit(rows)
                .offset(rows * (page - 1))
            ).all()
            return self.success(data=candidates_scan_report)
