import asyncio

import arrow
import astropy.units as u
from astropy.time import Time, TimeDelta
from tornado.ioloop import IOLoop
from utils.tns import get_tns

from baselayer.app.access import auth_or_token
from baselayer.log import make_log

from ....models import TNSRobot
from ...base import BaseHandler

log = make_log("api/bulk_tns")


class BulkTNSHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """
        ---
        summary: Bulk retrieve objects from TNS
        description: Retrieve objects from TNS
        tags:
            - tns
            - objs
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  tnsrobotID:
                    type: int
                    description: |
                      TNS Robot ID.
                  startDate:
                    type: string
                    description: |
                      Arrow-parseable date string (e.g. 2020-01-01).
                      Filter by public_timestamp >= startDate.
                      Defaults to one day ago.
                  groupIds:
                    type: array
                    items:
                      type: integer
                    description: |
                      List of IDs of groups to indicate labelling for
                required:
                  - tnsrobotID
                  - groupIds
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
        group_ids = data.get("groupIds", None)
        if group_ids is None:
            return self.error("group_ids is required")
        elif isinstance(group_ids, str):
            group_ids = [int(x) for x in group_ids.split(",")]
        elif not isinstance(group_ids, list):
            return self.error("group_ids type not understood")

        start_date = data.get("startDate", None)
        if start_date is None:
            start_date = Time.now() - TimeDelta(1 * u.day)
        else:
            start_date = Time(arrow.get(start_date.strip()).datetime)

        tnsrobot_id = data.get("tnsrobotID", None)
        if tnsrobot_id is None:
            return self.error("tnsrobotID is required")

        include_photometry = data.get("includePhotometry", False)
        include_spectra = data.get("includeSpectra", False)

        with self.Session() as session:
            tnsrobot = session.scalars(
                TNSRobot.select(session.user_or_token).where(TNSRobot.id == tnsrobot_id)
            ).first()
            if tnsrobot is None:
                return self.error(f"No TNSRobot available with ID {tnsrobot_id}")

            altdata = tnsrobot.altdata
            if not altdata:
                return self.error("Missing TNS information.")
            if "api_key" not in altdata:
                return self.error("Missing TNS API key.")

            try:
                asyncio.get_event_loop()
            except Exception:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            IOLoop.current().run_in_executor(
                None,
                lambda: get_tns(
                    tnsrobot.id,
                    self.associated_user_object.id,
                    include_photometry=include_photometry,
                    include_spectra=include_spectra,
                    start_date=start_date.isot,
                    group_ids=group_ids,
                ),
            )

            return self.success()
