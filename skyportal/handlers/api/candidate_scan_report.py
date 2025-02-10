from datetime import datetime

from baselayer.app.access import auth_or_token
from baselayer.log import make_log

from ...models import Obj
from ...models.candidate_scan_report import CandidateScanReport
from ..base import BaseHandler

log = make_log("api/candidate_scan_report")


class CandidateScanReportHandler(BaseHandler):
    @auth_or_token
    def post(self):
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

            return self.success()

    @auth_or_token
    def patch(self, candidate_scan_report_id=None):
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

            session.commit()
            return self.success()

    @auth_or_token
    def get(self):
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

    @auth_or_token
    def delete(self, candidate_scan_report_id):
        if not candidate_scan_report_id:
            return self.error("Report line not found")

        with self.Session() as session:
            candidate_scan_report = session.scalar(
                CandidateScanReport.select(session.user_or_token, mode="read").where(
                    CandidateScanReport.id == candidate_scan_report_id,
                )
            )
            if candidate_scan_report is None:
                return self.error("Report line not found")

            session.delete(candidate_scan_report)
            session.commit()
        return self.success()
