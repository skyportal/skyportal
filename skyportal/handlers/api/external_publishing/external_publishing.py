import sqlalchemy as sa

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from baselayer.log import make_log

from ....models import (
    Obj,
)
from ....models.external_publishing_bot import (
    ExternalPublishingBot,
    ExternalPublishingSubmission,
)
from ...base import BaseHandler
from ..tns.tns_robot import (
    process_instrument_ids,
    process_stream_ids,
    validate_photometry_options,
)

_, cfg = load_env()

log = make_log("api/external_publishing")

is_configured = (
    cfg.get("app.hermes.endpoint")
    and cfg.get("app.hermes.topic")
    and cfg.get("app.hermes.token")
)


def is_existing_submission_request(session, obj, external_publishing_bot_id, service):
    """Check if there is an existing submission request for the given object and bot and external service.
    session: SQLAlchemy
        session
    obj: Obj
        object to check
    external_publishing_bot_id: int
        ID of the external publishing bot
    service: str
        Name of the external service to check (TNS or Hermes)

    Returns:
        ExternalPublishingSubmission or None:
            The existing submission request if found, None otherwise.
    """
    if service not in ["TNS", "Hermes"]:
        raise ValueError("Invalid service name. Must be 'TNS' or 'Hermes'.")
    if service == "TNS":
        service_status = ExternalPublishingSubmission.tns_status
    else:
        service_status = ExternalPublishingSubmission.hermes_status
    return session.scalars(
        ExternalPublishingSubmission.select(session.user_or_token).where(
            ExternalPublishingSubmission.obj_id == obj.id,
            ExternalPublishingSubmission.external_publishing_bot_id
            == external_publishing_bot_id,
            sa.or_(
                service_status == "pending",
                service_status == "processing",
                service_status.like("submitted%"),
                service_status.like("complete%"),
            ),
        )
    ).first()


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
        data = self.get_json()

        with self.Session() as session:
            external_publishing_bot_id = data.get("external_publishing_bot_id")
            reporters = data.get("reporters", "")
            remarks = data.get("remarks", "")
            archival = data.get("archival", False)
            archival_comment = data.get("archivalComment", "")
            instrument_ids = data.get("instrument_ids", [])
            stream_ids = data.get("stream_ids", [])
            photometry_options = data.get("photometry_options", {})
            publish_to_tns = data.get("publish_to_tns", False)
            publish_to_hermes = data.get("publish_to_hermes", False)

            if not publish_to_tns and not publish_to_hermes:
                return self.error(
                    "Either publish to tns or publish to hermes must be set to True"
                )
            if publish_to_tns and self.current_user.affiliation is None:
                return self.error("User affiliation is required to publish to TNS")
            if publish_to_hermes and not is_configured:
                return self.error("This instance is not configured to use Hermes")

            if external_publishing_bot_id is None:
                return self.error("external_publishing_bot_id is required")
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

            external_publishing_bot = session.scalars(
                ExternalPublishingBot.select(session.user_or_token).where(
                    ExternalPublishingBot.id == external_publishing_bot_id
                )
            ).first()

            if publish_to_tns:
                altdata = external_publishing_bot.altdata
                if not altdata:
                    return self.error("Missing TNS information.")
                if "api_key" not in altdata:
                    return self.error("Missing TNS API key.")

            if external_publishing_bot is None:
                return self.error(
                    f"No publishing bot available with ID {external_publishing_bot_id}"
                )

            if archival is True:
                if len(archival_comment) == 0:
                    return self.error(
                        "If source flagged as archival, archival_comment is required"
                    )

            photometry_options = validate_photometry_options(
                photometry_options, external_publishing_bot.photometry_options
            )

            if publish_to_tns:
                existing_submission_request = is_existing_submission_request(
                    session, obj, external_publishing_bot_id, "TNS"
                )
                if existing_submission_request is not None:
                    return self.error(
                        f"Submission request for TNS for obj_id {obj.id} and bot_id {external_publishing_bot.id} already exists and is: {existing_submission_request.tns_status}"
                    )
            if publish_to_hermes:
                existing_submission_request = is_existing_submission_request(
                    session, obj, external_publishing_bot_id, "Hermes"
                )
                if existing_submission_request is not None:
                    return self.error(
                        f"Submission request for Hermes for obj_id {obj.id} and bot_id {external_publishing_bot.id} already exists and is: {existing_submission_request.hermes_status}"
                    )

            # create a ExternalPublishingSubmission entry with that information
            external_publishing_submission = ExternalPublishingSubmission(
                external_publishing_bot_id=external_publishing_bot.id,
                obj_id=obj.id,
                user_id=self.associated_user_object.id,
                custom_publishing_string=reporters,
                custom_remarks_string=remarks,
                archival=archival,
                archival_comment=archival_comment,
                instrument_ids=instrument_ids,
                stream_ids=stream_ids,
                photometry_options=photometry_options,
                auto_submission=False,
            )
            session.add(external_publishing_submission)
            session.commit()
            log(
                f"Added external publishing request for obj_id {obj.id} (manual submission) with bot_id {external_publishing_bot.id} for user_id {self.associated_user_object.id}"
            )
            return self.success()
