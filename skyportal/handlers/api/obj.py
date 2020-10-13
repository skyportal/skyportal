from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from ...models import Candidate, DBSession, Filter, Group, Obj, Photometry, Source


class ObjHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id=None):
        """
        ---
        single:
          description: Check if an Obj exists (either a Candidate or a Source)
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
                  schema: SingleObj
            400:
              content:
                application/json:
                  schema: Error
        """
        user_group_ids = [g.id for g in self.associated_user_object.accessible_groups]
        num_s = (
            DBSession()
            .query(Source)
            .filter(Source.obj_id == obj_id)
            .filter(Source.group_id.in_(user_group_ids))
            .count()
        )
        num_c = (
            DBSession()
            .query(Candidate)
            .filter(Candidate.obj_id == obj_id)
            .filter(
                Candidate.filter_id.in_(
                    DBSession.query(Filter.id).filter(
                        Filter.group_id.in_(user_group_ids)
                    )
                )
            )
            .count()
        )
        if num_s > 0 or num_c > 0:
            return self.success(
                data={"id": obj_id, "is_candidate": num_c > 0, "is_source": num_s > 0}
            )

        # There is no associated Source/Candidate, check if there is an Obj
        num_o = DBSession().query(Obj).filter(Obj.id == obj_id).count()
        # Do the check based on photometry
        if num_o > 0:

            num_p = (
                Photometry.query.filter(Photometry.obj_id == obj_id)
                .filter(Photometry.groups.any(Group.id.in_(user_group_ids)))
                .count()
            )
            if num_p > 0:
                return self.success(
                    data={"id": obj_id, "is_candidate": False, "is_source": False}
                )

        return self.error(message=f"Obj {obj_id} does not exist")
