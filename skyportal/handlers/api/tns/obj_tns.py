from skyportal_py_models.objs import ObjTNSBulkPostBody, ObjTNSGetQuery
from tornado.ioloop import IOLoop

from baselayer.app.access import auth_or_token, permissions
from baselayer.app.env import load_env
from baselayer.log import make_log

from ....models import (
    Obj,
)
from ....utils.tns import get_tns, get_tns_bulk, stale_tns_name_select
from ...base import BaseHandler

log = make_log("api/obj_tns")

_, cfg = load_env()


class ObjTNSHandler(BaseHandler):
    @auth_or_token
    async def get(self, obj_id: str, *, query: ObjTNSGetQuery = None):
        """
        ---
        summary: Get TNS info for an object
        description: Retrieve TNS information for an object
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

        async with self.AsyncSession() as session:
            obj = await session.scalar(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            )
            if obj is None:
                return self.error(f"No object available with ID {obj_id}")

            IOLoop.current().run_in_executor(
                None,
                lambda: get_tns(
                    obj_id=obj.id,
                    radius=radius,
                    user_id=self.associated_user_object.id,
                ),
            )

            return self.success()


class ObjTNSBulkHandler(BaseHandler):
    @permissions(["Manage sources"])
    async def post(self, *, body: ObjTNSBulkPostBody = None):
        """
        ---
        summary: Re-query TNS for many objects
        description: |
          Queue a TNS lookup for a list of objects, or for every classified
          object whose stored TNS name still carries the AT prefix. Each object
          takes the name TNS currently holds, which is how an AT becomes an SN
          once TNS accepts a classification.
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
        body = self.parse_body(ObjTNSBulkPostBody)

        if body.radius < 0:
            return self.error("radius must be non-negative")
        if bool(body.obj_ids) == body.stale_names_only:
            return self.error("Provide exactly one of obj_ids or stale_names_only")

        limit = cfg.get("app.tns.max_bulk_refresh", 1000)
        if body.max_objects is not None:
            if body.max_objects < 1:
                return self.error("max_objects must be positive")
            limit = min(body.max_objects, limit)

        async with self.AsyncSession() as session:
            if body.obj_ids:
                if len(body.obj_ids) > limit:
                    return self.error(
                        f"Cannot queue more than {limit} objects in one request"
                    )
                obj_ids = (
                    await session.scalars(
                        Obj.select(session.user_or_token, columns=[Obj.id]).where(
                            Obj.id.in_(body.obj_ids)
                        )
                    )
                ).all()
                missing = set(body.obj_ids) - set(obj_ids)
                if missing:
                    return self.error(
                        f"No object available with ID {', '.join(sorted(missing))}"
                    )
            else:
                obj_ids = (
                    await session.scalars(
                        stale_tns_name_select(session.user_or_token, limit)
                    )
                ).all()

            if not obj_ids:
                return self.success(data={"queued": 0, "queue_length": None})

            user_id = self.associated_user_object.id
            try:
                queue_length = await IOLoop.current().run_in_executor(
                    None,
                    lambda: get_tns_bulk(
                        obj_ids=list(obj_ids),
                        radius=body.radius,
                        user_id=user_id,
                    ),
                )
            except Exception as e:
                return self.error(f"Could not queue TNS refresh: {e}")

            log(f"Queued {len(obj_ids)} TNS refreshes for user {user_id}")
            return self.success(
                data={"queued": len(obj_ids), "queue_length": queue_length}
            )
