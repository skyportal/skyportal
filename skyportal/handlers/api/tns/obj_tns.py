from tornado.ioloop import IOLoop

from baselayer.app.access import auth_or_token
from baselayer.log import make_log

from ....models import (
    Obj,
)
from ....utils.tns import get_tns
from ...base import BaseHandler

log = make_log("api/obj_tns")


class ObjTNSHandler(BaseHandler):
    @auth_or_token
    async def get(self, obj_id: str):
        """
        ---
        summary: Get TNS info for an object
        description: Retrieve TNS information for an object
        tags:
          - tns
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

        radius = self.get_query_argument("radius", 2.0, type=float)
        if radius is None:
            return self.error("radius must be a number")
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
