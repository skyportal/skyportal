from marshmallow.exceptions import ValidationError

from baselayer.app.access import auth_or_token, permissions
from ..base import BaseHandler
from ...models import DBSession, Filter, Group, GroupUser, Stream


class FilterHandler(BaseHandler):
    @auth_or_token
    def get(self, filter_id=None):
        """
        ---
        single:
          description: Retrieve a filter
          parameters:
            - in: path
              name: filter_id
              required: true
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleFilter
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all filters
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfFilters
            400:
              content:
                application/json:
                  schema: Error
        """
        acls = [acl.id for acl in self.current_user.acls]

        if filter_id is not None:
            if "System admin" in acls or "Manage groups" in acls:
                f = DBSession().query(Filter).get(filter_id)
            else:
                f = (
                    DBSession()
                    .query(Filter)
                    .filter(
                        Filter.id == filter_id,
                        Filter.group_id.in_([g.id for g in self.current_user.accessible_groups])
                    )
                    .first()
                )
            if f is None:
                return self.error("Invalid filter ID.")
            # get stream:
            stream = DBSession().query(Stream).get(f.stream_id)
            f.stream = stream

            return self.success(data=f)

        filters = (
            DBSession()
            .query(Filter)
            .filter(
                Filter.group_id.in_([g.id for g in self.current_user.accessible_groups])
            )
            .all()
        )
        return self.success(data=filters)

    @auth_or_token
    def post(self):
        """
        ---
        description: POST a new filter.
        requestBody:
          content:
            application/json:
              schema: FilterNoID
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
                            id:
                              type: integer
                              description: New filter ID
        """
        data = self.get_json()
        schema = Filter.__schema__()
        try:
            fil = schema.load(data)
        except ValidationError as e:
            return self.error(
                "Invalid/missing parameters: " f"{e.normalized_messages()}"
            )

        acls = [acl.id for acl in self.current_user.acls]

        # check that user is su or group admin
        if "System admin" not in acls and "Manage groups" not in acls:
            gu = (
                GroupUser.query.filter(
                    GroupUser.group_id == fil.group_id,
                    GroupUser.user_id == self.associated_user_object.id,
                    GroupUser.admin == True
                )
                .first()
            )
            if gu is None:
                return self.error("Insufficient permissions.")

        # check that stream access is authorized
        # get group:
        group = DBSession().query(Group).get(fil.group_id)
        if group is None:
            return self.error("Invalid group ID.")
        # get stream:
        stream = DBSession().query(Stream).get(fil.stream_id)
        if stream is None:
            return self.error("Invalid stream ID.")
        if stream.id not in [gs.id for gs in group.streams]:
            return self.error("Access to stream unauthorized for group.")

        DBSession().add(fil)
        DBSession().commit()

        return self.success(data={"id": fil.id})

    @auth_or_token
    def patch(self, filter_id):
        """
        ---
        description: Update filter name
        parameters:
          - in: path
            name: filter_id
            required: True
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: FilterNoID
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
        acls = [acl.id for acl in self.current_user.acls]

        if "System admin" in acls or "Manage groups" in acls:
            f = DBSession().query(Filter).get(filter_id)
        else:
            f = (
                DBSession()
                .query(Filter)
                .filter(
                    Filter.id == filter_id,
                    Filter.group_id.in_([g.id for g in self.current_user.accessible_groups])
                )
                .first()
            )
        if f is None:
            return self.error("Invalid filter ID.")

        data = self.get_json()
        data["id"] = filter_id

        schema = Filter.__schema__()
        try:
            fil = schema.load(data, partial=True)
        except ValidationError as e:
            return self.error(
                'Invalid/missing parameters: ' f'{e.normalized_messages()}'
            )

        if fil.group_id != f.group_id or fil.stream_id != f.stream_id:
            return self.error("Cannot update group_id or stream_id.")

        DBSession().commit()
        return self.success()

    @auth_or_token
    def delete(self, filter_id):
        """
        ---
        description: Delete a filter
        parameters:
          - in: path
            name: filter_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        acls = [acl.id for acl in self.current_user.acls]

        if "System admin" in acls or "Manage groups" in acls:
            f = DBSession().query(Filter).get(filter_id)
        else:
            f = (
                DBSession()
                .query(Filter)
                .filter(
                    Filter.id == filter_id,
                    Filter.group_id.in_([g.id for g in self.current_user.accessible_groups])
                )
                .first()
            )
        if f is None:
            return self.error("Invalid filter ID.")

        DBSession().delete(Filter.query.get(filter_id))
        DBSession().commit()

        return self.success()
