from baselayer.app.access import auth_or_token, AccessError
from baselayer.app.env import load_env
from ..base import BaseHandler
from ...models import Obj

_, cfg = load_env()


class ObjHandler(BaseHandler):
    @auth_or_token  # ACLs will be checked below based on configs
    def delete(self, obj_id):
        """
        ---
        description: Delete an Obj
        tags:
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
            obj = session.scalars(
                Obj.select(session.user_or_token, mode='delete').where(Obj.id == obj_id)
            ).first()
            if obj is None:
                return self.error(f"Cannot find object with ID {obj_id}.")

            session.delete(obj)
            try:
                session.commit()
            except AccessError as e:
                error_msg = "Insufficient permissions: Objs may only be deleted by system admins"
                if cfg["misc.allow_nonadmins_delete_objs"]:
                    error_msg += " or by users who own all data associated with the Obj"
                return self.error(f"{error_msg}. (Original exception: {e})")
            return self.success()
