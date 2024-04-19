import numpy as np
import sqlalchemy as sa
from sqlalchemy.orm import scoped_session, sessionmaker

from baselayer.app.env import load_env
from baselayer.log import make_log

from ...models import DBSession, GcnReport
from ...utils.cache import Cache
from ..base import BaseHandler

log = make_log('api/galaxy')
env, cfg = load_env()

Session = scoped_session(sessionmaker())

cache_dir = "cache/public_pages/reports"
cache = Cache(
    cache_dir=cache_dir,
    max_age=cfg["misc.minutes_to_keep_reports_cache"] * 60,
)

ALLOWED_REPORT_TYPES = ["gcn"]


class ReportHandler(BaseHandler):
    def get(self, report_type, report_id=None, option=None):
        """
        ---
        description: Retrieve all reports
        tags:
          - reports
        responses:
          200:
            content:
              application/json:
                schema: GcnReport
          400:
            content:
              application/json:
                schema: Error
        """

        if report_type not in ALLOWED_REPORT_TYPES:
            return self.error(
                f"Invalid report type {report_type}, must be one of {ALLOWED_REPORT_TYPES}"
            )

        if report_id is not None:
            report_id = int(report_id)
            cache_key = f"{report_type}_{report_id}"
            cached = cache[cache_key]
            if cached is None:
                if Session.registry.has():
                    session = Session()
                else:
                    session = Session(bind=DBSession.session_factory.kw["bind"])

                # if report_type == "gcn":
                report = session.scalar(
                    sa.select(GcnReport).where(GcnReport.id == report_id)
                )
                if report is None:
                    return self.error(f"Could not load GCN report {report_id}")
                if not report.published:
                    return self.error(f"GCN report {report_id} not yet published")
                report.generate_report()
                cached = cache[cache_key]

            data = np.load(cached, allow_pickle=True)
            data = data.item()
            if data['published']:
                if option == "plot":
                    self.set_header("Content-Type", "image/png")
                    return self.write(data['plot'])
                else:
                    self.set_header("Content-Type", "text/html; charset=utf-8")
                    return self.write(data['html'])
            else:
                return self.error(f"Report {report_id} not yet published")
        else:
            if Session.registry.has():
                session = Session()
            else:
                session = Session(bind=DBSession.session_factory.kw["bind"])

            if report_type == "gcn":
                reports = session.scalars(
                    sa.select(GcnReport)
                    .where(GcnReport.published.is_(True))
                    .order_by(GcnReport.dateobs.desc())
                ).all()
                reports = [
                    {
                        **report.to_dict(),
                        "group_name": report.group.name,
                    }
                    for report in reports
                ]
                return self.render(
                    "public_pages/reports/gcn_reports_template.html", reports=reports
                )
