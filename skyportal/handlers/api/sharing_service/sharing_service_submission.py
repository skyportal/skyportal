from typing import Annotated, Any

import sqlalchemy as sa
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import joinedload, undefer

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from baselayer.log import make_log

from ....models import Obj, SharingService, SharingServiceSubmission
from ....utils.data_access import (
    is_existing_submission_request_async,
    process_instrument_ids_async,
    process_stream_ids_async,
    validate_photometry_options,
)
from ....utils.parse import get_page_and_n_per_page, str_to_bool
from ...base import BaseHandler

_, cfg = load_env()

log = make_log("api/sharing_service_submission")

is_configured = (
    cfg.get("app.hermes.endpoint")
    and cfg.get("app.hermes.topic")
    and cfg.get("app.hermes.token")
)


class SharingServiceSubmissionPostBody(BaseModel):
    """Request body for publishing an Obj to TNS or Hermes via a sharing service."""

    model_config = ConfigDict(extra="forbid")

    obj_id: str | None = Field(default=None, description="ID of the object to publish")
    sharing_service_id: int | None = Field(
        default=None,
        description="ID of the external sharing service to use for submission",
    )
    publishers: str | None = Field(
        default="", description="Custom string for publishers"
    )
    remarks: str | None = Field(default="", description="Custom remarks string")
    archival: bool | None = Field(
        default=False, description="Flag to indicate if the source is archival"
    )
    archival_comment: str | None = Field(
        default="",
        description="Comment for archival sources (required if archival is True)",
    )
    instrument_ids: list[int] | None = Field(
        default_factory=list,
        description="List of instrument IDs to associate with the submission",
    )
    stream_ids: list[int] | None = Field(
        default_factory=list,
        description="List of stream IDs to associate with the submission",
    )
    photometry_options: dict[str, Any] | None = Field(
        default_factory=dict, description="Options for photometry processing"
    )
    publish_to_tns: bool | None = Field(
        default=False,
        description="Flag to indicate if the submission should be published to TNS",
    )
    publish_to_hermes: bool | None = Field(
        default=False,
        description="Flag to indicate if the submission should be published to Hermes",
    )


class SharingServiceSubmissionHandler(BaseHandler):
    @auth_or_token
    async def post(self, *, body: SharingServiceSubmissionPostBody = None):
        """
        ---
        summary: Create an SharingServiceSubmission to publish an Obj to TNS or Hermes using a sharing service
        description: Create an SharingServiceSubmission to publish an Obj to TNS or Hermes using a sharing service.
        tags:
          - sharing service submission
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
        body = self.parse_body(SharingServiceSubmissionPostBody)

        obj_id = body.obj_id
        sharing_service_id = body.sharing_service_id
        publishers = body.publishers
        remarks = body.remarks
        archival = body.archival
        archival_comment = body.archival_comment
        instrument_ids = body.instrument_ids
        stream_ids = body.stream_ids
        photometry_options = body.photometry_options
        publish_to_tns = body.publish_to_tns
        publish_to_hermes = body.publish_to_hermes

        if sharing_service_id is None:
            return self.error("Sharing service id is required")
        try:
            sharing_service_id = int(sharing_service_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid sharing_service_id: {sharing_service_id}")
        if not obj_id:
            return self.error("obj_id is required")
        if not publish_to_tns and not publish_to_hermes:
            return self.error(
                "Either publish to TNS or publish to Hermes must be set to True"
            )
        if publish_to_hermes and not is_configured:
            return self.error("This instance is not configured to use Hermes")
        if publishers == "" or not isinstance(publishers, str):
            return self.error("publishers is required and must be a non-empty string")
        async with self.AsyncSession() as session:
            await process_instrument_ids_async(
                session, session.user_or_token, instrument_ids
            )
            await process_stream_ids_async(session, session.user_or_token, stream_ids)

            obj = await session.scalar(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            )
            if obj is None:
                return self.error(f"No object available with ID {obj_id}")

            sharing_service = await session.scalar(
                SharingService.select(session.user_or_token).where(
                    SharingService.id == sharing_service_id
                )
            )

            if publish_to_tns:
                tns_altdata = sharing_service.tns_altdata
                if not tns_altdata:
                    return self.error("Missing TNS information.")
                if "api_key" not in tns_altdata:
                    return self.error("Missing TNS API key.")

            if sharing_service is None:
                return self.error(
                    f"No sharing service available with ID {sharing_service_id}"
                )

            if archival is True:
                if len(archival_comment) == 0:
                    return self.error(
                        "If source flagged as archival, archival_comment is required"
                    )

            photometry_options = validate_photometry_options(
                photometry_options, sharing_service.photometry_options
            )

            if publish_to_tns:
                existing_submission_request = (
                    await is_existing_submission_request_async(
                        session, obj, sharing_service_id, "TNS"
                    )
                )
                if existing_submission_request is not None:
                    return self.error(
                        f"Submission request for TNS for obj_id {obj.id} and sharing service id {sharing_service.id} already exists and is: {existing_submission_request.tns_status}"
                    )
            if publish_to_hermes:
                existing_submission_request = (
                    await is_existing_submission_request_async(
                        session, obj, sharing_service_id, "Hermes"
                    )
                )
                if existing_submission_request is not None:
                    return self.error(
                        f"Submission request for Hermes for obj_id {obj.id} and sharing service id {sharing_service.id} already exists and is: {existing_submission_request.hermes_status}"
                    )

            # create a SharingServiceSubmission entry with that information
            sharing_service_submission = SharingServiceSubmission(
                sharing_service_id=sharing_service.id,
                obj_id=obj.id,
                user_id=self.associated_user_object.id,
                custom_publishing_string=publishers,
                custom_remarks_string=remarks,
                archival=archival,
                archival_comment=archival_comment,
                instrument_ids=instrument_ids,
                stream_ids=stream_ids,
                photometry_options=photometry_options,
                auto_submission=False,
                publish_to_tns=publish_to_tns,
                tns_status="pending" if publish_to_tns else None,
                publish_to_hermes=publish_to_hermes,
                hermes_status="pending" if publish_to_hermes else None,
            )
            session.add(sharing_service_submission)
            await session.commit()
            log(
                f"Added submission for obj_id {obj.id} (manual submission) with sharing service id {sharing_service.id} for user_id {self.associated_user_object.id}"
            )

            self.push_all(
                action="skyportal/REFRESH_SHARING_SERVICE_SUBMISSIONS",
                payload={"sharing_service_id": sharing_service.id},
            )
            return self.success()

    @auth_or_token
    async def get(
        self,
        sharing_service_submission_id: Annotated[
            int | None, Field(description="The ID of the sharing service submission")
        ] = None,
    ):
        """
        ---
        single:
            summary: Retrieve a SharingServiceSubmission
            description: Retrieve a SharingServiceSubmission
            tags:
                - sharing service submission
            parameters:
                - in: query
                  name: sharing_service_id
                  required: true
                  schema:
                    type: integer
                  description: The ID of the external sharing service to which the submission belongs
            responses:
                200:
                    content:
                        application/json:
                            schema: SingleSharingServiceSubmission
                400:
                    content:
                        application/json:
                            schema: Error
        multiple:
            summary: Retrieve all SharingServiceSubmissions
            description: Retrieve all SharingServiceSubmissions
            tags:
                - external sharing service
            parameters:
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
                            schema:
                                allOf:
                                  - $ref: '#/components/schemas/Success'
                                  - type: object
                                    properties:
                                      data:
                                        type: object
                                        properties:
                                          sharing_service_id:
                                            type: integer
                                          submissions:
                                            type: array
                                            items:
                                              $ref: '#/components/schemas/SharingServiceSubmission'
                                          pageNumber:
                                            type: integer
                                          numPerPage:
                                            type: integer
                                          totalMatches:
                                            type: integer
                400:
                    content:
                        application/json:
                            schema: Error
        """
        sharing_service_id = self.get_query_argument("sharing_service_id", None)
        if sharing_service_id is None:
            return self.error("Sharing service id is required")
        try:
            sharing_service_id = int(sharing_service_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid sharing_service_id: {sharing_service_id}")
        include_payload = str_to_bool(self.get_query_argument("include_payload", False))
        include_response = str_to_bool(
            self.get_query_argument("include_response", False)
        )
        page_number = self.get_query_argument("pageNumber", 1)
        page_size = self.get_query_argument("numPerPage", 100)
        try:
            page_number, page_size = get_page_and_n_per_page(page_number, page_size)
        except ValueError as e:
            return self.error(str(e))
        obj_id = self.get_query_argument("objectID", None)
        if obj_id is not None:
            obj_id = obj_id.strip()
            if not obj_id:
                obj_id = None

        if sharing_service_submission_id is not None:
            try:
                sharing_service_submission_id = int(sharing_service_submission_id)
            except (TypeError, ValueError):
                return self.error(
                    f"Invalid sharing_service_submission_id: {sharing_service_submission_id}"
                )

        async with self.AsyncSession() as session:
            sharing_service = await session.scalar(
                SharingService.select(session.user_or_token).where(
                    SharingService.id == sharing_service_id
                )
            )
            if sharing_service is None:
                return self.error(f"Sharing service {sharing_service_id} not found")

            if sharing_service_submission_id is not None:
                submission = await session.scalar(
                    SharingServiceSubmission.select(session.user_or_token)
                    .options(joinedload(SharingServiceSubmission.obj))
                    .where(
                        SharingServiceSubmission.sharing_service_id
                        == sharing_service_id,
                        SharingServiceSubmission.id == sharing_service_submission_id,
                    )
                )
                if submission is None:
                    return self.error(
                        f"Submission {sharing_service_submission_id} not found for bot {sharing_service_id}"
                    )
                submission_data = {
                    "tns_name": submission.obj.tns_name,
                    **submission.to_dict(),
                }
                return self.success(data=submission_data)
            else:
                stmt = SharingServiceSubmission.select(session.user_or_token).where(
                    SharingServiceSubmission.sharing_service_id == sharing_service_id
                )
                if obj_id is not None:
                    stmt = stmt.where(SharingServiceSubmission.obj_id == obj_id)

                # run a count query to get the total number of results
                count_result = await session.execute(
                    sa.select(sa.func.count()).select_from(stmt)
                )
                total_matches = count_result.scalar()

                stmt = stmt.order_by(SharingServiceSubmission.created_at.desc())
                stmt = stmt.options(joinedload(SharingServiceSubmission.obj))

                if include_payload:
                    stmt = stmt.options(undefer(SharingServiceSubmission.tns_payload))
                if include_response:
                    stmt = stmt.options(undefer(SharingServiceSubmission.response))

                result = await session.scalars(
                    stmt.limit(page_size).offset((page_number - 1) * page_size)
                )
                submissions = result.unique().all()

                return self.success(
                    data={
                        "sharing_service_id": sharing_service.id,
                        "submissions": [
                            {"tns_name": s.obj.tns_name, **s.to_dict()}
                            for s in submissions
                        ],
                        "pageNumber": page_number,
                        "numPerPage": page_size,
                        "totalMatches": total_matches,
                    }
                )
