from sqlalchemy.orm import joinedload
from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token, AccessError
from ..base import BaseHandler
from ...models import (
    DBSession,
    Group,
    Shift,
)


class ShiftHandler(BaseHandler):
    @permissions(["Manage shifts"])
    def post(self):
        """
        ---
        description: Add a new shift
        tags:
          - shift
        requestBody:
          content:
            application/json:
              schema: ShiftNoID
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
                              description: New Shift
          400:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()

        schema = Shift.__schema__()

        try:
            shift = schema.load(data)
        except ValidationError as exc:
            return self.error(
                f"Invalid/missing parameters: {exc.normalized_messages()}"
            )

        DBSession().add(shift)
        self.verify_and_commit()

        self.push_all(action="skyportal/REFRESH_SHIFTS")
        return self.success(data={"id": shift.id})

    @auth_or_token
    def get(self, group_id=None):
        """
        ---
        description: Retrieve shifts
        tags:
          - shifts
        parameters:
          - in: path
            name: group_id
            required: false
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: ArrayOfShifts
          400:
            content:
              application/json:
                schema: Error
        """
        if group_id is not None:
            shifts = (
                Shift.query_records_accessible_by(
                    self.current_user,
                    mode="read",
                    options=[joinedload(Shift.group).joinedload(Group.users)],
                )
                .filter(Shift.group_id == group_id)
                .order_by(Shift.start_date.asc())
                .all()
            )
        else:
            shifts = (
                Shift.query_records_accessible_by(
                    self.current_user,
                    mode="read",
                    options=[joinedload(Shift.group).joinedload(Group.users)],
                )
                .order_by(Shift.start_date.asc())
                .all()
            )
        self.verify_and_commit()
        return self.success(data=shifts)

    @permissions(["Manage shifts"])
    def delete(self, shift_id):
        """
        ---
        description: Delete a shift
        tags:
          - shifts
        parameters:
          - in: path
            name: shift_id
            required: true
            schema:
              type: integer
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
        shift_id = int(shift_id)

        try:
            shift = Shift.get_if_accessible_by(
                shift_id, self.current_user, mode="delete", raise_if_none=True
            )
        except AccessError as e:
            return self.error(
                f"Only the owner of a shift can delete it. Original error: {e}"
            )

        DBSession().delete(shift)
        self.verify_and_commit()

        self.push_all(action="skyportal/REFRESH_SHIFTS")

        return self.success()
