import arrow
from sqlalchemy.orm import joinedload
from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from skyportal.models.comment import CommentOnShift
from ..base import BaseHandler
from ...models import (
    Group,
    Shift,
    ShiftUser,
    User,
    Token,
    UserNotification,
    GcnEvent,
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
                            required_users_number:
                              type: integer
                              description: The number of users required to join this shift for it to be considered full
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

        with self.Session() as session:
            shift_admins = session.scalars(
                User.select(self.current_user).where(User.id.in_(shift_admin_ids))
            ).all()
            # get the list of ids from the shift_admins list
            if self.current_user.id not in [
                e.id for e in shift_admins
            ] and not isinstance(self.current_user, Token):
                shift_admins.append(self.current_user)
            schema = Shift.__schema__()

            try:
                shift = schema.load(data)
            except ValidationError as exc:
                return self.error(
                    f"Invalid/missing parameters: {exc.normalized_messages()}"
                )

            session.add(shift)
            session.add_all(
                [ShiftUser(shift=shift, user=user, admin=True) for user in shift_admins]
            )
            session.commit()

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

        with self.Session() as session:

            if group_id is not None:
                queried_shifts = (
                    session.scalars(
                        Shift.select(
                            session.user_or_token,
                            options=[
                                joinedload(Shift.group).joinedload(Group.group_users),
                                joinedload(Shift.shift_users),
                            ],
                        )
                        .where(Shift.group_id == group_id)
                        .order_by(Shift.start_date.asc())
                    )
                    .unique()
                    .all()
                )
            else:
                queried_shifts = (
                    session.scalars(
                        Shift.select(
                            session.user_or_token,
                            options=[
                                joinedload(Shift.group).joinedload(Group.group_users),
                                joinedload(Shift.shift_users),
                            ],
                        ).order_by(Shift.start_date.asc())
                    )
                    .unique()
                    .all()
                )
            shifts = []
            for shift in queried_shifts:
                susers = []
                for su in shift.shift_users:
                    user = su.user.to_dict()
                    user["admin"] = su.admin
                    user["needs_replacement"] = su.needs_replacement
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
                comments = (
                    session.scalars(
                        CommentOnShift.select(
                            self.current_user,
                            options=[
                                joinedload(CommentOnShift.author),
                                joinedload(CommentOnShift.groups),
                            ],
                        ).where(CommentOnShift.shift_id == shift["id"])
                    )
                    .unique()
                    .all()
                )
                shift["comments"] = sorted(
                    (
                        {
                            **{
                                k: v
                                for k, v in c.to_dict().items()
                                if k != "attachment_bytes"
                            },
                            "author": {
                                **c.author.to_dict(),
                                "gravatar_url": c.author.gravatar_url,
                            },
                        }
                        for c in comments
                    ),
                    key=lambda x: x["created_at"],
                    reverse=True,
                )
                shifts.append(shift)

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
        with self.Session() as session:
            shift = session.scalars(
                Shift.select(session.user_or_token).where(Shift.id == shift_id)
            ).first()
            if shift is None:
                return self.error(
                    "Only the admin of a shift or an admin of the shift's group can delete it."
                )

            session.delete(shift)
            session.commit()

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
                            needs_replacement:
                              type: boolean
                              description: Boolean indicating whether user needs replacement or not
        """

        data = self.get_json()

        user_id = data.get("userID", None)
        if user_id is None:
            return self.error("userID parameter must be specified")
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            return self.error("Invalid userID parameter: unable to parse to integer")

        needs_replacement = data.get("needs_replacement", False)
        # test if bool already
        if type(needs_replacement) != bool:
            try:
                needs_replacement = bool(needs_replacement)
            except (ValueError, TypeError):
                return self.error(
                    "Invalid needs_replacement parameter: unable to parse to boolean"
                )

        admin = data.get("admin", False)
        if not isinstance(admin, bool):
            return self.error(
                "Invalid (non-boolean) value provided for parameter `admin`"
            )
        # if the shift has no admins, we add the user as an admin
        try:
            shift_id = int(shift_id)
        except (ValueError, TypeError):
            return self.error("Invalid shift_id parameter: unable to parse to integer")

        with self.Session() as session:
            shift = session.scalars(
                Shift.select(
                    session.user_or_token,
                    options=[joinedload(Shift.shift_users)],
                ).where(Shift.id == shift_id)
            ).first()
            if not any(su.admin for su in shift.shift_users):
                admin = True

            user = session.scalars(
                User.select(session.user_or_token).where(User.id == user_id)
            ).first()

            su = session.scalars(
                ShiftUser.select(session.user_or_token)
                .where(ShiftUser.shift_id == shift_id)
                .where(ShiftUser.user_id == user_id)
            ).first()
            if su is not None:
                return self.error(
                    f"User {user_id} is already a member of shift {shift_id}."
                )
            if shift.required_users_number:
                if len(shift.shift_users) >= shift.required_users_number:
                    return self.error(
                        f"Shift {shift_id} has reached its maximum number of users."
                    )

            session.add(
                ShiftUser(
                    shift_id=shift_id,
                    user_id=user_id,
                    admin=admin,
                    needs_replacement=needs_replacement,
                )
            )
            session.add(
                UserNotification(
                    user=user,
                    text=f"You've been added to shift *{shift.name}*",
                    url=f"/shift/{shift.id}",
                )
            )
            session.commit()
            self.flow.push(user.id, "skyportal/FETCH_NOTIFICATIONS", {})

            self.push_all(
                action='skyportal/REFRESH_SHIFTS', payload={'shift_id': shift_id}
            )
            return self.success(
                data={'shift_id': shift_id, 'user_id': user_id, 'admin': admin}
            )

    @permissions(["Manage shifts"])
    def patch(self, shift_id, user_id):
        """
        ---
        description: Update a shift user's admin status, or needs_replacement status
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
                  needs_replacement:
                    type: boolean
                    description: |
                      Boolean indicating whether user needs replacement or not

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
        try:
            user_id = int(user_id)
        except ValueError:
            return self.error("Invalid userID parameter")

        with self.Session() as session:
            shiftuser = session.scalars(
                ShiftUser.select(session.user_or_token, mode='update')
                .where(ShiftUser.shift_id == shift_id)
                .where(ShiftUser.user_id == user_id)
            ).first()

            if shiftuser is None:
                return self.error(
                    f"User {user_id} is not a member of shift {shift_id}."
                )

            admin = data.get("admin", shiftuser.admin)
            if not isinstance(admin, bool):
                return self.error(
                    "Invalid (non-boolean) value provided for parameter `admin`"
                )
            shiftuser.admin = admin

            needs_replacement = data.get("needs_replacement", False)
            # test if bool already
            if type(needs_replacement) != bool:
                try:
                    needs_replacement = bool(needs_replacement)
                except (ValueError, TypeError):
                    return self.error(
                        "Invalid needs_replacement parameter: unable to parse to boolean"
                    )
            shiftuser.needs_replacement = needs_replacement

            if needs_replacement:
                # send a user notification to all members of the group associated to the shift
                # that the user needs to be replaced
                # recover all group users associated to the shift
                shift = session.scalars(
                    Shift.select(
                        session.user_or_token,
                        options=[
                            joinedload(Shift.group).joinedload(Group.group_users),
                        ],
                    ).where(Shift.id == shift_id)
                ).first()
                if shift is None:
                    return self.error('Could not find shift.')
                for group_user in shift.group.group_users:
                    if group_user.user_id != user_id:
                        session.add(
                            UserNotification(
                                user=group_user.user,
                                text=(
                                    f"*@{shiftuser.user.username}* needs a "
                                    f"replacement for shift: {shift.name} "
                                    f"from {shift.start_date} to {shift.end_date}."
                                ),
                                url=f"/shifts/{shift.id}",
                            )
                        )
                        self.flow.push(
                            group_user.user_id, "skyportal/FETCH_NOTIFICATIONS", {}
                        )

            session.commit()
            self.push_all(
                action='skyportal/REFRESH_SHIFTS', payload={'shift_id': shift_id}
            )
            return self.success()

    @permissions(["Manage shifts"])
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

        try:
            shift_id = int(shift_id)
        except ValueError:
            return self.error("Invalid shift_id; unable to parse to integer")

        with self.Session() as session:
            su = session.scalars(
                ShiftUser.select(session.user_or_token, mode='delete')
                .where(ShiftUser.shift_id == shift_id)
                .where(ShiftUser.user_id == user_id)
            ).first()
            if su is None:
                return self.error(
                    "ShiftUser does not exist, or you don't have the right to delete him.",
                    status=403,
                )

            session.delete(su)
            session.commit()
            self.push_all(
                action='skyportal/REFRESH_SHIFTS', payload={'shift_id': shift_id}
            )
            return self.success()


class ShiftSummary(BaseHandler):
    """
    This handler has a get method that returns a summary
    of all the activity of shift users on skyportal for a given period.
    It is used to generate a report.
    """

    @auth_or_token
    def get(self, shift_id=None):
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
            name: shift_id
            required: false
            schema:
              type: integer
          - in: query
            name: startDate
            required: false
            schema:
              type: string
            description: |
              Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by
              shift.start_date >= startDate
          - in: qyert
            name: end_date
            required: false
            schema:
              type: string
            description: |
              Arrow-parseable date string (e.g. 2020-01-01). If provided, filter by
              shift.start_date <=endDate
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        start_date = self.get_query_argument("startDate", None)
        end_date = self.get_query_argument("endDate", None)
        if (start_date is None or end_date is None) and shift_id is None:
            return self.error("Please provide start_date and end_date, or shift_id")

        if start_date is not None and end_date is not None:
            try:
                start_date = arrow.get(start_date).datetime
                end_date = arrow.get(end_date).datetime
            except ValueError:
                return self.error("Please provide valid start_date and end_date")
            if start_date > end_date:
                return self.error("Please provide start_date < end_date")
            if start_date > arrow.utcnow():
                return self.error("Please provide start_date < today")
            # if there is more than 4 weeks, we return an error
            if (end_date - start_date).days > 28:
                return self.error("Please provide a period of less than 4 weeks")

        with self.Session() as session:

            report = {}
            if start_date and end_date:
                s = (
                    session.scalars(
                        Shift.select(
                            session.user_or_token,
                            options=[
                                joinedload(Shift.shift_users),
                            ],
                        )
                        .where(Shift.start_date >= start_date)
                        .where(Shift.start_date <= end_date)
                        .order_by(Shift.start_date.asc())
                    )
                    .unique()
                    .all()
                )
            else:
                s = (
                    session.scalars(
                        Shift.select(
                            session.user_or_token,
                            options=[
                                joinedload(Shift.shift_users),
                            ],
                        ).where(Shift.id == shift_id)
                    )
                    .unique()
                    .all()
                )
            if len(s) == 0:
                return self.error("No shifts found")
            shifts = []
            for shift in s:
                susers = []
                for su in shift.shift_users:
                    user = su.user.to_dict()
                    user["admin"] = su.admin
                    user["needs_replacement"] = su.needs_replacement
                    del user["oauth_uid"]
                    susers.append(user)
                shift = shift.to_dict()
                shift["shift_users"] = susers
                shifts.append(shift)

            report['shifts'] = {}
            report['shifts']['total'] = len(shifts)
            report['shifts']['data'] = shifts
            if shift_id and not start_date and not end_date:
                start_date = shifts[0]['start_date']
                end_date = shifts[0]['end_date']

            gcns = (
                session.scalars(
                    GcnEvent.select(
                        session.user_or_token,
                    )
                    .where(GcnEvent.dateobs >= start_date)
                    .where(GcnEvent.dateobs <= end_date)
                    .order_by(GcnEvent.dateobs.asc())
                )
                .unique()
                .all()
            )
            gcn_added_during_shifts = []
            # get the gcns added during the shifts
            if len(gcns) > 0:
                for shift in shifts:
                    # get list of user_id who are shift_users
                    for gcn in gcns:
                        gcn = gcn.to_dict()
                        if (
                            gcn["dateobs"] >= shift["start_date"]
                            and gcn["dateobs"] <= shift["end_date"]
                        ):
                            if gcn["id"] not in [
                                gcn["id"] for gcn in gcn_added_during_shifts
                            ]:
                                gcn['shift_ids'] = [shift['id']]
                                gcn_added_during_shifts.append(gcn)

                            else:
                                for gcn_added in gcn_added_during_shifts:
                                    if gcn_added['id'] == gcn['id']:
                                        gcn_added['shift_ids'].append(shift['id'])
                                        break
                report['gcns'] = {'total': len(gcn_added_during_shifts)}
                report['gcns']['data'] = gcn_added_during_shifts

            self.push_all(action="skyportal/FETCH_SHIFT_SUMMARY", payload=report)
            return self.success(data=report)
