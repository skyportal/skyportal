from astropy.time import Time

from baselayer.app.access import auth_or_token
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ....models.scan_report.scan_report_item import ScanReportItem
from ....utils.safe_round import safe_round
from ...base import BaseHandler

log = make_log("api/candidate_scan_report_item")


def create_scan_report_item(report_id, saved_candidate):
    """
    Parameters
    ----------
    report_id: int
        The ID of the scan report to create an item for
    saved_candidate: skyportal.model.Source
        The saved candidate to create a scan report item for
    Returns
    -------
    scan_report_item: skyportal.model.ScanReportItem
    """
    phot_stats = saved_candidate.obj.photstats
    current_mag = phot_stats[0].last_detected_mag if phot_stats else None
    current_age = (
        (Time.now().mjd - phot_stats[0].first_detected_mjd) if phot_stats else None
    )

    return ScanReportItem(
        obj_id=saved_candidate.obj_id,
        scan_report_id=report_id,
        data={
            "comment": None,
            "already_classified": None,
            "host_redshift": saved_candidate.obj.redshift,
            "current_mag": safe_round(current_mag, 3),
            "current_age": safe_round(current_age, 2),
        },
    )


class ScanReportItemHandler(BaseHandler):
    @auth_or_token
    def patch(self, report_id, item_id):
        """
        ---
        summary: Update an item from a scan report
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
                  already_classified:
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

        with self.Session() as session:
            item = session.scalar(
                ScanReportItem.select(session.user_or_token, mode="read").where(
                    ScanReportItem.id == item_id,
                    ScanReportItem.scan_report_id == report_id,
                )
            )
            if item is None:
                return self.error("Report item not found")

            item.data["comment"] = (data.get("comment"),)
            item.data["already_classified"] = (data.get("already_classified"),)

            flow = Flow()
            flow.push("*", "skyportal/REFRESH_SCAN_REPORT_ITEM")

            session.commit()
            return self.success()

    @auth_or_token
    def get(self, report_id, _):
        """
        ---
        summary: Retrieve all items in a scan report
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
                schema: ArrayOfCandidateScanReport
          400:
            content:
              application/json:
                schema: Error
        """
        with self.Session() as session:
            items = session.scalars(
                ScanReportItem.select(session.user_or_token, mode="read").where(
                    ScanReportItem.scan_report_id == report_id
                )
            ).all()
            return self.success(data=items)
