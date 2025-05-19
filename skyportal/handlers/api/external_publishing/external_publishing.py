import sqlalchemy as sa

from baselayer.app.access import auth_or_token
from baselayer.log import make_log

from ....models import (
    Obj,
    TNSRobot,
    TNSRobotSubmission,
)
from ...base import BaseHandler
from ..tns.tns_robot import (
    process_instrument_ids,
    process_stream_ids,
    validate_photometry_options,
)

log = make_log("api/external_publishing")


class ExternalPublishingHandler(BaseHandler):
    @auth_or_token
    def post(self, obj_id):
        """
        ---
        summary: Post an Obj to external publishing service (TNS, Hermes)
        description: Post an Obj to external publishing service (TNS, Hermes)
        tags:
          - external_publishing
          - objs
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
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

        with self.Session() as session:
            data = self.get_json()
            tnsrobotID = data.get("tnsrobotID")
            reporters = data.get("reporters", "")
            remarks = data.get("remarks", "")
            archival = data.get("archival", False)
            archival_comment = data.get("archivalComment", "")
            instrument_ids = data.get("instrument_ids", [])
            stream_ids = data.get("stream_ids", [])
            photometry_options = data.get("photometry_options", {})
            publish_to_tns = data.get("publish_to_tns", False)
            publish_to_hermes = data.get("publish_to_hermes", False)

            if publish_to_tns and self.current_user.affiliation is None:
                return self.error("User affiliation is required to publish to TNS")
            if not publish_to_tns and not publish_to_hermes:
                return self.error(
                    "Either publish to tns or publish to hermes must be set to True"
                )

            if tnsrobotID is None:
                return self.error("tnsrobotID is required")
            if reporters == "" or not isinstance(reporters, str):
                return self.error(
                    "reporters is required and must be a non-empty string"
                )

            process_instrument_ids(session, instrument_ids)
            process_stream_ids(session, stream_ids)

            obj = session.scalars(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            ).first()
            if obj is None:
                return self.error(f"No object available with ID {obj_id}")

            tnsrobot = session.scalars(
                TNSRobot.select(session.user_or_token).where(TNSRobot.id == tnsrobotID)
            ).first()
            if tnsrobot is None:
                return self.error(f"No TNSRobot available with ID {tnsrobotID}")

            if archival is True:
                if len(archival_comment) == 0:
                    return self.error(
                        "If source flagged as archival, archival_comment is required"
                    )

            if publish_to_tns:
                altdata = tnsrobot.altdata
                if not altdata:
                    return self.error("Missing TNS information.")
                if "api_key" not in altdata:
                    return self.error("Missing TNS API key.")

            photometry_options = validate_photometry_options(
                photometry_options, tnsrobot.photometry_options
            )

            # verify that there isn't already a TNSRobotSubmission for this object
            # and TNSRobot, that is:
            # 1. pending
            # 2. processing
            # 3. submitted
            # 4. complete
            # if so, do not add another request
            existing_submission_request = session.scalars(
                TNSRobotSubmission.select(session.user_or_token).where(
                    TNSRobotSubmission.obj_id == obj.id,
                    TNSRobotSubmission.tnsrobot_id == tnsrobot.id,
                    sa.or_(
                        TNSRobotSubmission.status == "pending",
                        TNSRobotSubmission.status == "processing",
                        TNSRobotSubmission.status.like("submitted%"),
                        TNSRobotSubmission.status.like("complete%"),
                    ),
                )
            ).first()
            if existing_submission_request is not None:
                return self.error(
                    f"TNSRobotSubmission request for obj_id {obj.id} and tnsrobot_id {tnsrobot.id} already exists and is: {existing_submission_request.status}"
                )
            # create a TNSRobotSubmission entry with that information
            tnsrobot_submission = TNSRobotSubmission(
                tnsrobot_id=tnsrobot.id,
                obj_id=obj.id,
                user_id=self.associated_user_object.id,
                custom_reporting_string=reporters,
                custom_remarks_string=remarks,
                archival=archival,
                archival_comment=archival_comment,
                instrument_ids=instrument_ids,
                stream_ids=stream_ids,
                photometry_options=photometry_options,
                auto_submission=False,
            )
            session.add(tnsrobot_submission)
            session.commit()
            log(
                f"Added TNSRobotSubmission request for obj_id {obj.id} (manual submission) with tnsrobot_id {tnsrobot.id} for user_id {self.associated_user_object.id}"
            )
            return self.success()
