from datetime import datetime

from baselayer.app.access import auth_or_token

from ...models import Candidate
from ...models.candidate_scan_report import CandidateScanReport
from ..base import BaseHandler


class CandidateScanReportHandler(BaseHandler):
    @auth_or_token
    def post(self, candidate_id):
        data = self.get_json()
        if not candidate_id:
            return self.error("No candidate to save")

        with self.Session() as session:
            candidate = session.scalar(
                Candidate.select(session.user_or_token, mode="read").where(
                    Candidate.id == candidate_id,
                )
            )
            if candidate is None:
                return self.error("Candidate not found")

            candidate_scan_report = CandidateScanReport(
                date=datetime.now(),
                scanner=session.user_or_token.username,
                obj_id=candidate.obj_id,
                comment=data.get("comment"),
                already_classified=data.get("already_classified"),
                host_redshift=candidate.obj.redshift,
                current_mag=candidate.obj.mag_nearest_source,
                current_age=data.get("current_age"),
                forced_photometry_requested=data.get("forced_photometry_requested"),
                photometry_followup=data.get("photometry_followup"),
                photometry_assigned_to=data.get("photometry_assigned_to"),
                is_real=data.get("is_real"),
                spectroscopy_requested=data.get("spectroscopy_requested"),
                spectroscopy_assigned_to=data.get("spectroscopy_assigned_to"),
                priority=data.get("priority"),
                saver_id=session.user_or_token.id,
            )

            session.add(candidate_scan_report)
            session.commit()

    @auth_or_token
    def get(self):
        rows_per_page = self.get_query_argument("rowsPerPage", default="10")
        page_number = self.get_query_argument("pageNumber", default="1")
        with self.Session() as session:
            candidates_scan_report = session.scalars(
                CandidateScanReport.select(session.user_or_token, mode="read")
                .order_by(CandidateScanReport.date.desc())
                .limit(rows_per_page)
                .offset(rows_per_page * (int(page_number) - 1))
            ).all()
            return self.success(data=candidates_scan_report)

    @auth_or_token
    def delete(self):
        return
