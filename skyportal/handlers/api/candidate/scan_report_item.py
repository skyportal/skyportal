from astropy.time import Time

from baselayer.app.access import auth_or_token
from baselayer.log import make_log

from ....models import Obj, Source
from ....models.scan_report.scan_report_item import ScanReportItem
from ....utils.safe_round import safe_round
from ...base import BaseHandler

log = make_log("api/scan_report_item")


def create_scan_report_item(session, report, sources_by_obj):
    """
    Parameters
    ----------
    session: sqlalchemy.orm.Session
    report: skyportal.model.ScanReport
        The scanning report to create an item for
    sources_by_obj: tuple (obj_id, source_ids)
        The object and link source ids to create the item for
    Returns
    -------
    scan_report_item: skyportal.model.ScanReportItem
    """
    obj_id, source_ids = sources_by_obj

    if not obj_id or not source_ids:
        return None

    obj = session.scalar(
        Obj.select(session.user_or_token, mode="read").where(Obj.id == obj_id)
    )
    current_mag = obj.photstats[0].last_detected_mag if obj.photstats else None
    current_age = (
        (Time.now().mjd - obj.photstats[0].first_detected_mjd)
        if obj.photstats
        else None
    )

    sources = session.scalars(
        Source.select(session.user_or_token, mode="read").where(
            Source.obj_id == obj_id, Source.id.in_(source_ids)
        )
    ).all()

    classifications = None
    if obj.classifications:
        classifications = [
            {
                "probability": classification.probability,
                "classification": classification.classification,
                "ml": classification.ml,
            }
            for classification in obj.classifications
        ]

    saved_info = None
    if sources:
        saved_info = [
            {
                "saved_at": source.saved_at.isoformat(),
                "saved_by": source.saved_by.username,
                "group": source.group.name,
            }
            for source in sources
        ]

    return ScanReportItem(
        obj_id=obj.id,
        scan_report=report,
        data={
            "tns_name": obj.tns_name,
            "comment": None,
            "host_redshift": obj.redshift,
            "current_mag": safe_round(current_mag, 3),
            "current_age": safe_round(current_age, 2),
            "classifications": classifications,
            "saved_info": saved_info,
        },
    )


class ScanReportItemHandler(BaseHandler):
    @auth_or_token
    def patch(self, report_id, item_id):
        """
        ---
        summary: Update an item from a scanning report
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

            item.data = {
                **item.data,
                "comment": data.get("comment"),
            }

            session.commit()

            self.push_all(
                action="skyportal/REFRESH_SCAN_REPORT_ITEM",
                payload={"report_id": report_id},
            )
            return self.success()

    @auth_or_token
    def get(self, report_id, _):
        """
        ---
        summary: Retrieve all items in a scanning report
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
