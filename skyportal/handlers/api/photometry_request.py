from sqlalchemy.orm import selectinload

from baselayer.app.access import auth_or_token

from ...models import FollowupRequest
from ..base import BaseHandler


class PhotometryRequestHandler(BaseHandler):
    @auth_or_token
    async def get(self, request_id):
        """
        ---
        summary: Get photometry request
        description: Get photometry request.
        tags:
          - followup requests
        parameters:
          - in: path
            name: request_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        try:
            request_id_int = int(request_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid request_id: {request_id}")

        refresh_source = self.get_query_argument("refreshSource", True)
        refresh_requests = self.get_query_argument("refreshRequests", False)

        async with self.AsyncSession() as session:
            try:
                followup_request = await session.scalar(
                    FollowupRequest.select(self.associated_user_object)
                    .where(FollowupRequest.id == request_id_int)
                    .options(
                        selectinload(FollowupRequest.instrument),
                        selectinload(FollowupRequest.obj),
                    )
                )
                if followup_request is None:
                    return self.error("Invalid followup request id.")

                api = followup_request.instrument.api_class
                if not api.implements()["get"]:
                    return self.error("Cannot retrieve requests on this instrument.")

                followup_request.last_modified_by_id = self.associated_user_object.id
                internal_key = followup_request.obj.internal_key

                # Bridge sync facility-API call via greenlet on async connection
                await session.run_sync(
                    lambda sync_session: api.get(
                        followup_request,
                        sync_session,
                        refresh_source=refresh_source,
                        refresh_requests=refresh_requests,
                    )
                )
                await session.commit()

                self.push_all(
                    action="skyportal/REFRESH_SOURCE",
                    payload={"obj_key": internal_key},
                )
                return self.success(
                    data={
                        "id": followup_request.id,
                        "request_status": followup_request.status,
                    }
                )
            except Exception as e:
                return self.error(f"Error retrieving request: {e}")
