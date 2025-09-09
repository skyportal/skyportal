import asyncio

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
    def get(self, obj_id):
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

        radius = self.get_query_argument("radius", 2.0)

        try:
            radius = float(radius)
        except ValueError:
            return self.error("radius must be a number")
        else:
            if radius < 0:
                return self.error("radius must be non-negative")

        with self.Session() as session:
            obj = session.scalars(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            ).first()
            if obj is None:
                return self.error(f"No object available with ID {obj_id}")

            try:
                asyncio.get_event_loop()
            except Exception:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            IOLoop.current().run_in_executor(
                None,
                lambda: get_tns(
                    obj_id=obj.id,
                    radius=radius,
                    user_id=self.associated_user_object.id,
                ),
            )

            return self.success()
