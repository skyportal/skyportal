from astropy.time import Time

from baselayer.app.access import auth_or_token
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ....models import Source
from ....models.candidate import Candidate
from ....models.scan_report import ScanReport
from ....models.scan_report_item import ScanReportItem
from ...base import BaseHandler
from ..public_pages.public_source_page import safe_round

log = make_log("api/candidate_scan_report")


def get_saved_candidates(session, detection_range, saved_range):
    """
    Get all saved candidates in a given range which passed the filters in a given range.
    Parameters
    ----------
    session: sqlalchemy.orm.Session
    detection_range: dict
    saved_range: dict

    Returns
    -------
    list of saved candidates
    """
    return session.scalars(
        Source.select(session.user_or_token, mode="read")
        .join(Candidate, Source.obj_id == Candidate.obj_id)
        .where(
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
    ).all()


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
            detection_range = data.get("candidates_detection_range")
            if not detection_range:
                return self.error("No candidate detection range provided")

            saved_range = data.get("saved_candidates_range")
            if not saved_range:
                return self.error("No saved candidates range provided")

            saved_candidates = get_saved_candidates(
                session, detection_range, saved_range
            )

            if not saved_candidates:
                return self.error("No candidates found in the given range")

            scan_report = ScanReport(created_by_id=session.user_or_token.id)

            session.add(scan_report)

            for saved_candidate in saved_candidates:
                if saved_candidate.obj is None:
                    return self.error("No object found for one of the saved candidates")

                phot_stats = saved_candidate.obj.photstats
                current_mag = phot_stats[0].last_detected_mag if phot_stats else None
                current_age = (
                    (Time.now().mjd - phot_stats[0].first_detected_mjd)
                    if phot_stats
                    else None
                )

                scan_report_item = ScanReportItem(
                    obj_id=saved_candidate.obj_id,
                    scan_report_id=scan_report.id,
                    data={
                        "comment": "",
                        "already_classified": False,
                        "host_redshift": saved_candidate.obj.redshift,
                        "current_mag": safe_round(current_mag, 3),
                        "current_age": safe_round(current_age, 2),
                    },
                )

                session.add(scan_report_item)
                scan_report.items.append(scan_report_item)

            session.add(scan_report)
            session.commit()

            flow = Flow()
            flow.push("*", "skyportal/REFRESH_CANDIDATE_SCAN_REPORTS")

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
            items = session.scalars(
                ScanReport.select(session.user_or_token, mode="read")
                .order_by(ScanReport.created_at.desc())
                .limit(rows)
                .offset(rows * (page - 1))
            ).all()
            return self.success(data=items)
