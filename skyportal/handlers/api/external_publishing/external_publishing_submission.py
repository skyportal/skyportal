import sqlalchemy as sa
from sqlalchemy.orm import joinedload

from baselayer.app.access import auth_or_token
from baselayer.log import make_log

from ....models.external_publishing_bot import (
    ExternalPublishingBot,
    ExternalPublishingSubmission,
)
from ....utils.parse import get_page_and_n_per_page
from ...base import BaseHandler

log = make_log("api/external_publishing_submission")


class ExternalPublishingSubmissionHandler(BaseHandler):
    @auth_or_token
    def get(self, external_publishing_bot_id, external_publishing_submission_id=None):
        """
        ---
        single:
            summary: Retrieve a ExternalPublishingSubmission
            description: Retrieve a ExternalPublishingSubmission
            tags:
                - external publishing bot
            parameters:
                - in: path
                  name: external_publishing_bot_id
                  required: true
                  schema:
                    type: integer
                  description: The ID of the external publishing bot
                - in: path
                  name: external_publishing_submission_id
                  required: false
                  schema:
                    type: integer
                  description: The ID of the external publishing submission
            responses:
                200:
                    content:
                        application/json:
                            schema: ExternalPublishingSubmission
                400:
                    content:
                        application/json:
                            schema: Error
        multiple:
            summary: Retrieve all ExternalPublishingSubmissions
            description: Retrieve all ExternalPublishingSubmissions
            tags:
                - external publishing bot
            parameters:
                - in: path
                  name: external_publishing_bot_id
                  required: true
                  schema:
                    type: integer
                  description: The ID of the ExternalPublishingBot
                - in: query
                  name: pageNumber
                  required: false
                  schema:
                    type: integer
                  description: The page number to retrieve, starting at 1
                - in: query
                  name: numPerPage
                  required: false
                  schema:
                    type: integer
                  description: The number of results per page, defaults to 100
                - in: query
                  name: include_payload
                  required: false
                  schema:
                    type: boolean
                  description: Whether to include the payload in the response
                - in: query
                  name: include_response
                  required: false
                  schema:
                    type: boolean
                  description: Whether to include the response in the response
                - in: query
                  name: objectID
                  required: false
                  schema:
                    type: string
                  description: The object ID of the submission
            responses:
                200:
                    content:
                        application/json:
                            schema: ArrayOfExternalPublishingSubmissions
                400:
                    content:
                        application/json:
                            schema: Error
        """
        include_payload = self.get_query_argument("include_payload", False)
        include_response = self.get_query_argument("include_response", False)
        if str(include_payload).lower().strip() in ["true", "t", "1"]:
            include_payload = True
        if str(include_response).lower().strip() in ["true", "t", "1"]:
            include_response = True

        page_number = self.get_query_argument("pageNumber", 1)
        page_size = self.get_query_argument("numPerPage", 100)
        page_number, page_size = get_page_and_n_per_page(page_number, page_size)

        obj_id = self.get_query_argument("objectID", None)
        if obj_id is not None:
            obj_id = obj_id.strip()
            if not obj_id:
                obj_id = None

        with self.Session() as session:
            external_publishing_bot = session.scalar(
                ExternalPublishingBot.select(session.user_or_token).where(
                    ExternalPublishingBot.id == external_publishing_bot_id
                )
            )
            if external_publishing_bot is None:
                return self.error(f"Bot {external_publishing_bot_id} not found")

            if external_publishing_submission_id is not None:
                submission = session.scalar(
                    ExternalPublishingSubmission.select(session.user_or_token).where(
                        ExternalPublishingSubmission.external_publishing_bot_id
                        == external_publishing_bot_id,
                        ExternalPublishingSubmission.id
                        == external_publishing_submission_id,
                    )
                )
                if submission is None:
                    return self.error(
                        f"Submission {external_publishing_submission_id} not found for bot {external_publishing_bot_id}"
                    )
                submission = {
                    "tns_name": submission.obj.tns_name,
                    **submission.to_dict(),
                }
                return self.success(data=submission)
            else:
                stmt = ExternalPublishingSubmission.select(session.user_or_token).where(
                    ExternalPublishingSubmission.external_publishing_bot_id
                    == external_publishing_bot_id
                )
                if obj_id is not None:
                    stmt = stmt.where(ExternalPublishingSubmission.obj_id == obj_id)

                # run a count query to get the total number of results
                total_matches = session.execute(
                    sa.select(sa.func.count()).select_from(stmt)
                ).scalar()

                stmt = stmt.order_by(ExternalPublishingSubmission.created_at.desc())

                if include_payload:
                    stmt = stmt.options(
                        sa.orm.undefer(ExternalPublishingSubmission.payload)
                    )
                if include_response:
                    stmt = stmt.options(
                        sa.orm.undefer(ExternalPublishingSubmission.response)
                    )

                submissions = session.scalars(
                    stmt.limit(page_size).offset((page_number - 1) * page_size)
                ).all()

                return self.success(
                    data={
                        "external_publishing_bot_id": external_publishing_bot.id,
                        "submissions": [
                            {"tns_name": s.obj.tns_name, **s.to_dict()}
                            for s in submissions
                        ],
                        "pageNumber": page_number,
                        "numPerPage": page_size,
                        "totalMatches": total_matches,
                    }
                )
