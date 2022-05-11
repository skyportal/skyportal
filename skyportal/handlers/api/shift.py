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
    CommentOnGCN,
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
        print(start_date, end_date)
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

        # get the groups of the current user
        groups = self.current_user.groups
        # get a list of group ids
        groups_ids = [group.id for group in groups if not group.single_user_group]

        print(groups_ids)

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

        # get the comments on gcn made by shift_users

        # generate the report of all gcn comments made during the period, shift by shift, user by user
        report = {}
        for shift in shifts:
            report[shift.id] = {}
            report[shift.id]['shift_info'] = {
                'shift_name': shift.name,
                'start_date': shift.start_date,
                'end_date': shift.end_date,
                'shift_description': shift.description,
            }
            report[shift.id]['shift_users'] = {}
            for shift_user in shift.shift_users:
                report[shift.id]['shift_users'][shift_user.user_id] = {
                    "user_name": f'{shift_user.user.first_name} {shift_user.user.last_name}',
                    "user_email": shift_user.user.contact_email,
                    "user_id": shift_user.user_id,
                }
            comments_on_gcn = (
                CommentOnGCN.query_records_accessible_by(self.current_user, mode='read')
                .filter(
                    CommentOnGCN.author_id.in_(
                        [shift_user.user_id for shift_user in shift.shift_users]
                    )
                )
                .filter(CommentOnGCN.created_at >= start_date)
                .filter(CommentOnGCN.created_at <= end_date)
                .all()
            )
            report[shift.id]["gcn_comments"] = []
            for comment in comments_on_gcn:
                if comment.author_id in [
                    shift_user.user_id for shift_user in shift.shift_users
                ]:
                    report[shift.id]["gcn_comments"].append(
                        {
                            "comment_id": comment.id,
                            "gcn_id": comment.gcn_id,
                            "comment": comment.text,
                            "author_id": comment.author_id,
                            "date": comment.created_at,
                        }
                    )

            comments_on_source = (
                Comment.query_records_accessible_by(self.current_user, mode='read')
                .filter(
                    Comment.author_id.in_(
                        [shift_user.user_id for shift_user in shift.shift_users]
                    )
                )
                .filter(Comment.created_at >= start_date)
                .filter(Comment.created_at <= end_date)
                .all()
            )

            report[shift.id]["source_comments"] = []
            for comment in comments_on_source:
                if comment.author_id in [
                    shift_user.user_id for shift_user in shift.shift_users
                ]:
                    report[shift.id]["source_comments"].append(
                        {
                            "comment_id": comment.id,
                            "source_id": comment.obj_id,
                            "comment": comment.text,
                            "author_id": comment.author_id,
                            "date": comment.created_at,
                        }
                    )

            # get all the gcns that have been created during each shift
            report[shift.id]["gcns"] = (
                GcnEvent.query_records_accessible_by(self.current_user, mode='read')
                .filter(GcnEvent.created_at >= shift.start_date)
                .filter(GcnEvent.created_at <= shift.end_date)
                .all()
            )

            # for each gcn, get the sources they contain
            # TO IMPLEMENT

            # get all the sources that have been created during each shift
            report[shift.id]["sources"] = (
                Source.query_records_accessible_by(self.current_user, mode='read')
                .filter(Source.created_at >= shift.start_date)
                .filter(Source.created_at <= shift.end_date)
                .all()
            )

        return self.success(report)
