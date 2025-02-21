from datetime import datetime

from astropy.time import Time

from baselayer.app.access import auth_or_token
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ...models import Source
from ...models.candidate_scan_report import CandidateScanReport
from ..base import BaseHandler
from .public_pages.public_source_page import safe_round

log = make_log("api/candidate_scan_report")


class CandidateScanReportHandler(BaseHandler):
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
                  candidate_detection_range:
                    type: object
                    properties:
                      start_date:
                        type: string
                        format: date-time
                      end_date:
                        type: string
                        format: date-time
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
            if not data.get("saved_candidates_range"):
                return self.error("No saved candidates range provided")
            saved_range = data["saved_candidates_range"]

            saved_candidates = session.scalars(
                Source.select(session.user_or_token, mode="read").where(
                    Source.saved_by_id == session.user_or_token.id,
                    Source.saved_at.between(
                        saved_range.get("start_save_date"),
                        saved_range.get("end_save_date"),
                    ),
                    Source.active.is_(True),
                )
            ).all()

            if not saved_candidates:
                return self.error("No saved candidates found")

            for saved_candidate in saved_candidates:
                if saved_candidate.obj is None:
                    return self.error("No object found for one saved candidate")

                phot_stats = saved_candidate.obj.photstats
                current_mag = phot_stats[0].last_detected_mag if phot_stats else None
                current_age = (
                    (Time.now().mjd - phot_stats[0].first_detected_mjd)
                    if phot_stats
                    else None
                )

                candidate_scan_report = CandidateScanReport(
                    date=datetime.now(),
                    scanner=session.user_or_token.username,
                    obj_id=saved_candidate.obj_id,
                    already_classified=False,
                    host_redshift=saved_candidate.obj.redshift,
                    current_mag=safe_round(current_mag, 3),
                    current_age=safe_round(current_age, 2),
                    forced_photometry_requested=False,
                    saver_id=session.user_or_token.id,
                )

                session.add(candidate_scan_report)
                session.commit()

                flow = Flow()
                flow.push("*", "skyportal/REFRESH_CANDIDATE_SCAN_REPORTS")

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
