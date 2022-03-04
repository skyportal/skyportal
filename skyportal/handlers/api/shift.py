from sqlalchemy.orm import joinedload
from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token, AccessError
from ..base import BaseHandler
from ...models import (
    DBSession,
    Group,
    Shift,
    ShiftUser,
    User,
    Token,
    UserNotification,
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
        try:
            shift_admin_ids = [int(e) for e in data.get('shift_admins', [])]
        except ValueError:
            return self.error(
                "Invalid shift_admins field; unable to parse all items to int"
            )
        shift_admins = (
            User.query_records_accessible_by(self.current_user)
            .filter(User.id.in_(shift_admin_ids))
            .all()
        )
        if self.current_user not in shift_admins and not isinstance(
            self.current_user, Token
        ):
            shift_admins.append(self.current_user)

        schema = Shift.__schema__()

        try:
            shift = schema.load(data)
        except ValidationError as exc:
            return self.error(
                f"Invalid/missing parameters: {exc.normalized_messages()}"
            )

        DBSession().add(shift)
        DBSession().add_all(
            [ShiftUser(shift=shift, user=user, admin=True) for user in shift_admins]
        )
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
                    options=[
                        joinedload(Shift.group).joinedload(Group.users),
                        joinedload(Shift.users),
                    ],
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
                    options=[
                        joinedload(Shift.group).joinedload(Group.users),
                        joinedload(Shift.users),
                    ],
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


class ShiftUserHandler(BaseHandler):
    @permissions(["Manage shifts"])
    def post(self, shift_id, *ignored_args):
        """
        ---
        description: Add a shift user
        tags:
          - shifts
          - users
        parameters:
          - in: path
            name: shift_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  userID:
                    type: integer
                  admin:
                    type: boolean
                required:
                  - userID
                  - admin
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
                            shift_id:
                              type: integer
                              description: Shift ID
                            user_id:
                              type: integer
                              description: User ID
                            admin:
                              type: boolean
                              description: Boolean indicating whether user is shift admin
        """

        data = self.get_json()

        user_id = data.get("userID", None)
        if user_id is None:
            return self.error("userID parameter must be specified")
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            return self.error("Invalid userID parameter: unable to parse to integer")

        admin = data.get("admin", False)
        if not isinstance(admin, bool):
            return self.error(
                "Invalid (non-boolean) value provided for parameter `admin`"
            )
        shift_id = int(shift_id)

        shift = Shift.get_if_accessible_by(
            shift_id, self.current_user, raise_if_none=True, mode='read'
        )
        user = User.get_if_accessible_by(
            user_id, self.current_user, raise_if_none=True, mode='read'
        )

        # Add user to group
        su = (
            ShiftUser.query.filter(ShiftUser.shift_id == shift_id)
            .filter(ShiftUser.user_id == user_id)
            .first()
        )
        if su is not None:
            return self.error(
                f"User {user_id} is already a member of shift {shift_id}."
            )

        DBSession().add(ShiftUser(shift_id=shift_id, user_id=user_id, admin=admin))
        DBSession().add(
            UserNotification(
                user=user,
                text=f"You've been added to shift *{shift.name}*",
                url=f"/shift/{shift.id}",
            )
        )
        self.verify_and_commit()
        self.flow.push(user.id, "skyportal/FETCH_NOTIFICATIONS", {})

        self.push_all(action='skyportal/REFRESH_SHIFTS', payload={'shift_id': shift_id})
        return self.success(
            data={'shift_id': shift_id, 'user_id': user_id, 'admin': admin}
        )

    @permissions(["Manage shifts"])
    def patch(self, shift_id, *ignored_args):
        """
        ---
        description: Update a shift user's admin status
        tags:
          - shifts
          - users
        parameters:
          - in: path
            name: shift_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  userID:
                    type: integer
                  admin:
                    type: boolean
                    description: |
                      Boolean indicating whether user is shift admin.

                required:
                  - userID
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        data = self.get_json()
        try:
            shift_id = int(shift_id)
        except ValueError:
            return self.error("Invalid shift ID")

        user_id = data.get("userID")
        try:
            user_id = int(user_id)
        except ValueError:
            return self.error("Invalid userID parameter")

        shiftuser = (
            ShiftUser.query_records_accessible_by(self.current_user, mode='update')
            .filter(ShiftUser.shift_id == shift_id)
            .filter(ShiftUser.user_id == user_id)
            .first()
        )

        if shiftuser is None:
            return self.error(f"User {user_id} is not a member of shift {shift_id}.")

        admin = data.get("admin", shiftuser.admin)
        if not isinstance(admin, bool):
            return self.error(
                "Invalid (non-boolean) value provided for parameter `admin`"
            )
        shiftuser.admin = admin
        self.verify_and_commit()
        return self.success()

    @auth_or_token
    def delete(self, shift_id, user_id):
        """
        ---
        description: Delete a shift user
        tags:
          - shifts
          - users
        parameters:
          - in: path
            name: shift_id
            required: true
            schema:
              type: integer
          - in: path
            name: user_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        try:
            user_id = int(user_id)
        except ValueError:
            return self.error("Invalid user_id; unable to parse to integer")

        su = (
            ShiftUser.query_records_accessible_by(self.current_user, mode='delete')
            .filter(ShiftUser.shift_id == shift_id)
            .filter(ShiftUser.user_id == user_id)
            .first()
        )

        if su is None:
            raise AccessError("ShiftUser does not exist.")

        DBSession().delete(su)
        self.verify_and_commit()
        self.push_all(
            action='skyportal/REFRESH_SHIFTS', payload={'shift_id': int(shift_id)}
        )
        return self.success()
