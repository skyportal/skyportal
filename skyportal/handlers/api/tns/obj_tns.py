from skyportal_py_models.objs import ObjTNSGetQuery

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from baselayer.log import make_log

from ....models import Obj, TNSRetrievalRequest
from ...base import BaseHandler

env, cfg = load_env()
log = make_log("api/obj_tns")


class ObjTNSHandler(BaseHandler):
    @auth_or_token
    async def get(self, obj_id: str, *, query: ObjTNSGetQuery = None):
        """
        ---
        summary: Get TNS info for an object
        description: >
            Queue a search of TNS around an object. The search runs in the
            background and its status is returned with the source.
        tags:
          - tns
          - objs
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

        query = self.parse_query(ObjTNSGetQuery)

        radius = query.radius
        if radius < 0:
            return self.error("radius must be non-negative")

        if not all(
            cfg.get(f"app.tns.{key}")
            for key in ("endpoint", "bot_id", "bot_name", "api_key")
        ):
            return self.error("TNS is not configured on this instance")

        async with self.AsyncSession() as session:
            obj = await session.scalar(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            )
            if obj is None:
                return self.error(f"No object available with ID {obj_id}")

            request = await session.scalar(
                TNSRetrievalRequest.select(session.user_or_token).where(
                    TNSRetrievalRequest.obj_id == obj.id,
                    TNSRetrievalRequest.status.in_(["pending", "processing"]),
                )
            )
            if request is None:
                request = TNSRetrievalRequest(
                    obj_id=obj.id,
                    user_id=self.associated_user_object.id,
                    radius=radius,
                )
                session.add(request)
                await session.commit()
                self.push_all(
                    action="skyportal/REFRESH_SOURCE",
                    payload={"obj_key": obj.internal_key},
                )

            return self.success(data={"id": request.id})
