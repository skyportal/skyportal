from datetime import datetime
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
    Comment,
    GcnEvent,
    Source,
)


class ShiftHandler(BaseHandler):
    @permissions(["Manage shifts"])
    def post(self):
        """
        ---
        description: Add a new shift
        tags:
          - shifts
        requestBody:
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/ShiftNoID'
                  - type: object
                    properties:
                      shift_admins:
                        type: array
                        items:
                          type: integer
                        description: |
                          List of IDs of users to be shift admins. Current user will
                          automatically be added as a shift admin.
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
                            name:
                              type: string
                              description: New Shift's name
                            start_date:
                              type: string
                              description: New Shift's start date
                            end_date:
                              type: string
                              description: New Shift's end date
                            shift_admins:
                              type: array
                              description: New Shift's admins IDs
                            description:
                              type: string
                              description: New Shift's description
          400:
            content:
              application/json:
                schema: Error
        """

        data = self.get_json()
        if data.get("name") is None or (
            isinstance(data.get("name"), str) and data.get("name").strip() == ""
        ):
            return self.error("Missing required parameter: `name`")

        try:
            shift_admin_ids = [int(e) for e in data.pop('shift_admins', [])]
        except ValueError:
            return self.error(
                "Invalid shift_admins field; unable to parse all items to int"
            )
        shift_admins = (
            User.query_records_accessible_by(self.current_user)
            .filter(User.id.in_(shift_admin_ids))
            .all()
        )
        # get the list of ids from the shift_admins list
        if self.current_user.id not in [e.id for e in shift_admins] and not isinstance(
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
            queried_shifts = (
                Shift.query_records_accessible_by(
                    self.current_user,
                    mode="read",
                    options=[
                        joinedload(Shift.group).joinedload(Group.group_users),
                        joinedload(Shift.shift_users),
                    ],
                )
                .filter(Shift.group_id == group_id)
                .order_by(Shift.start_date.asc())
                .all()
            )
        else:
            queried_shifts = (
                Shift.query_records_accessible_by(
                    self.current_user,
                    mode="read",
                    options=[
                        joinedload(Shift.group).joinedload(Group.group_users),
                        joinedload(Shift.shift_users),
                    ],
                )
                .order_by(Shift.start_date.asc())
                .all()
            )
        shifts = []
        for shift in queried_shifts:
            susers = []
            for su in shift.shift_users:
                user = su.user.to_dict()
                user["admin"] = su.admin
                del user["oauth_uid"]
                susers.append(user)
            gusers = []
            for gu in shift.group.group_users:
                user = gu.user.to_dict()
                user["admin"] = gu.admin
                del user["oauth_uid"]
                gusers.append(user)

            shift = shift.to_dict()
            shift["shift_users"] = susers
            shift["group"] = shift["group"].to_dict()
            shift["group"]["group_users"] = gusers
            shifts.append(shift)

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
                f"Only the admin of a shift or an admin of the shift's group can delete it. Original error: {e}"
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
        # if the shift has no users, we need to make sure the user is an admin
        if not ShiftUser.query.filter_by(shift_id=shift_id).count():
            admin = True

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


class ShiftsSummary(BaseHandler):
    # this handler has a get method that returns a summary of all the activity of shift users on skyportal for a given period
    # it is used to generate a report

    @auth_or_token
    def get(self):
        """
        ---
        description: Get a summary of all the activity of shift users on skyportal for a given period
        tags:
          - shifts
          - users
          - sources
          - gcn
        parameters:
          - in: path
            name: start_date
            required: true
            schema:
              type: string
              format: date
          - in: path
            name: end_date
            required: true
            schema:
              type: string
              format: date
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        start_date = self.get_argument("start_date", None)
        end_date = self.get_argument("end_date", None)
        if start_date is None or end_date is None:
            return self.error("Please provide start_date and end_date")
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%S")
            end_date = datetime.strptime(end_date, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return self.error("Please provide valid start_date and end_date")
        if start_date > end_date:
            return self.error("Please provide start_date < end_date")
        if start_date.date() > datetime.today().date():
            return self.error("Please provide start_date < today")

        report = {}

        shifts = (
            Shift.query_records_accessible_by(
                self.current_user,
                mode="read",
                options=[
                    joinedload(Shift.shift_users),
                ],
            )
            .filter(Shift.start_date >= start_date)
            .filter(Shift.start_date <= end_date)
            .order_by(Shift.start_date.asc())
            .all()
        )
        if len(shifts) == 0:
            return self.error("No shifts found")
        else:
            report['shifts'] = shifts

        gcns = (
            GcnEvent.query_records_accessible_by(
                self.current_user,
                mode="read",
                options=[
                    # join to gcn comments made by shift_users
                    joinedload(GcnEvent.comments),
                ],
            )
            .filter(GcnEvent.created_at >= start_date)
            .filter(GcnEvent.created_at <= end_date)
            .order_by(GcnEvent.created_at.asc())
            .all()
        )
        gcn_added_during_shifts = []
        # get the gcns added during the shifts
        if len(gcns) > 0:
            for shift in shifts:
                shift = shift.to_dict()
                # get list of user_id who are shift_users
                for gcn in gcns:
                    gcn = gcn.to_dict()
                    if (
                        gcn["created_at"] >= shift["start_date"]
                        and gcn["created_at"] <= shift["end_date"]
                    ):
                        if gcn["id"] not in [
                            gcn["id"] for gcn in gcn_added_during_shifts
                        ]:
                            # check if gcn comments are made by shift_users
                            comments = gcn["comments"]
                            new_comments = []
                            if len(comments) > 0:
                                for comment in comments:
                                    comment = comment.to_dict()
                                    if (
                                        comment["created_at"] >= shift["start_date"]
                                        and comment["created_at"] <= shift["end_date"]
                                    ):
                                        if comment["author_id"] in [
                                            user.to_dict()["user_id"]
                                            for user in shift["shift_users"]
                                        ]:
                                            comment['made_by_shift_user'] = True
                                        else:
                                            comment['made_by_shift_user'] = False
                                        new_comments.append(comment)
                            gcn["comments"] = new_comments
                            gcn_added_during_shifts.append(gcn)
                        # if the gcn is already in the list, simply add the additional comment to the existing gcn
            report['gcns'] = {'total': len(gcn_added_during_shifts)}
            report['gcns']['data'] = gcn_added_during_shifts

        sources = (
            Source.query_records_accessible_by(
                self.current_user,
                mode="read",
            )
            .filter(Source.created_at >= start_date)
            .filter(Source.created_at <= end_date)
            .order_by(Source.created_at.asc())
            .all()
        )

        sources_with_comments = []
        for source in sources:
            source = source.to_dict()
            if (
                source["created_at"] >= shift["start_date"]
                and source["created_at"] <= shift["end_date"]
            ):
                source['comments'] = (
                    Comment.query_records_accessible_by(
                        self.current_user,
                        mode="read",
                    )
                    .filter(Comment.obj_id == source['obj_id'])
                    .filter(Comment.created_at >= start_date)
                    .filter(Comment.created_at <= end_date)
                    .all()
                )
                sources_with_comments.append(source)

        sources = sources_with_comments

        sources_added_during_shifts = []
        # get the sources added during the shifts
        if len(sources) > 0:
            for shift in shifts:
                shift = shift.to_dict()
                for source in sources:
                    if (
                        source["created_at"] >= shift["start_date"]
                        and source["created_at"] <= shift["end_date"]
                    ):
                        if source["obj_id"] not in [
                            source["obj_id"] for source in sources_added_during_shifts
                        ]:
                            # check if source comments are made by shift_users
                            comments = source["comments"]
                            new_comments = []
                            if len(comments) > 0:
                                for comment in comments:
                                    comment = comment.to_dict()
                                    if (
                                        comment["created_at"] >= shift["start_date"]
                                        and comment["created_at"] <= shift["end_date"]
                                    ):
                                        if comment["author_id"] in [
                                            user.to_dict()["user_id"]
                                            for user in shift["shift_users"]
                                        ]:
                                            comment['made_by_shift_user'] = True
                                        else:
                                            comment['made_by_shift_user'] = False
                                        new_comments.append(comment)
                            source["comments"] = new_comments
                            sources_added_during_shifts.append(source)
            report['sources'] = {'total': len(sources_added_during_shifts)}
            report['sources']['data'] = sources_added_during_shifts

        return self.success(report)
