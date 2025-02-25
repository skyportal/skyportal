from baselayer.app.access import auth_or_token
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ....models.scan_report_item import ScanReportItem
from ...base import BaseHandler

log = make_log("api/candidate_scan_report_item")


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

        with self.Session() as session:
            item = session.scalar(
                ScanReportItem.select(session.user_or_token, mode="read").where(
                    ScanReportItem.id == item_id,
                    ScanReportItem.scan_report_id == report_id,
                )
            )
            if item is None:
                return self.error("Report item not found")

            item.comment = data.get("comment", item.comment)
            item.already_classified = data.get(
                "already_classified", item.already_classified
            )
            item.forced_photometry_requested = data.get(
                "forced_photometry_requested", item.forced_photometry_requested
            )

            flow = Flow()
            flow.push("*", "skyportal/REFRESH_CANDIDATE_SCAN_REPORT")

            session.commit()
            return self.success()

    @auth_or_token
    def get(self, report_id):
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
