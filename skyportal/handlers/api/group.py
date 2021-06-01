from sqlalchemy import or_
from marshmallow.exceptions import ValidationError
from baselayer.app.access import auth_or_token, permissions, AccessError
from baselayer.app.env import load_env
from ..base import BaseHandler
from ...models import (
    DBSession,
    Group,
    GroupStream,
    GroupUser,
    Obj,
    Source,
    User,
    Token,
    UserNotification,
)

_, cfg = load_env()


def has_admin_access_for_group(user, group_id):
    groupuser = (
        GroupUser.query.filter(GroupUser.group_id == group_id)
        .filter(GroupUser.user_id == user.id)
        .first()
    )
    return len(
        {"System admin", "Manage groups", "Manage_users"}.intersection(
            set(user.permissions)
        )
    ) > 0 or (groupuser is not None and groupuser.admin)


class GroupHandler(BaseHandler):
    @auth_or_token
    def get(self, group_id=None):
        """
        ---
        single:
          description: Retrieve a group
          tags:
            - groups
          parameters:
            - in: path
              name: group_id
              required: true
              schema:
                type: integer
            - in: query
              name: includeGroupUsers
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to include group users. Defaults to true.
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
                            allOf:
                              - $ref: '#/components/schemas/Group'
                              - type: object
                                properties:
                                  users:
                                    type: array
                                    items:
                                      - $ref: '#/components/schemas/User'
                                    description: List of group users
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all groups
          tags:
            - groups
          parameters:
            - in: query
              name: name
              schema:
                type: string
              description: Fetch by name (exact match)
            - in: query
              name: includeSingleUserGroups
              schema:
                type: boolean
              description: |
                Bool indicating whether to include single user groups.
                Defaults to false.
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
                              user_groups:
                                type: array
                                items:
                                  $ref: '#/components/schemas/Group'
                                description: List of groups current user is a member of.
                              user_accessible_groups:
                                type: array
                                items:
                                  $ref: '#/components/schemas/Group'
                                description: |
                                  List of groups current user can access, not including
                                  single user groups.
                              all_groups:
                                type: array
                                items:
                                  $ref: '#/components/schemas/Group'
                                description: |
                                  List of all groups, optionally including single user
                                  groups if query parameter `includeSingleUserGroups` is
                                  `true`.
            400:
              content:
                application/json:
                  schema: Error
        """
        if group_id is not None:
            group = Group.get_if_accessible_by(
                group_id, self.current_user, raise_if_none=True, mode='read'
            )

            if self.get_query_argument("includeGroupUsers", "true").lower() in (
                "f",
                "false",
            ):
                include_group_users = False
            else:
                include_group_users = True

            # Do not include User.groups to avoid circular reference
            users = (
                [
                    {
                        "id": gu.user.id,
                        "username": gu.user.username,
                        "first_name": gu.user.first_name,
                        "last_name": gu.user.last_name,
                        "contact_email": gu.user.contact_email,
                        "contact_phone": gu.user.contact_phone,
                        "oauth_uid": gu.user.oauth_uid,
                        "admin": gu.admin,
                        "can_save": gu.can_save,
                    }
                    for gu in group.group_users
                ]
                if include_group_users
                else None
            )

            streams = group.streams
            filters = group.filters

            group = group.to_dict()
            if users is not None:
                group['users'] = users

            # grab streams:
            group['streams'] = streams
            # grab filters:
            group['filters'] = filters

            self.verify_and_commit()
            return self.success(data=group)

        group_name = self.get_query_argument("name", None)
        if group_name is not None:
            groups = (
                Group.query_records_accessible_by(self.current_user)
                .filter(Group.name == group_name)
                .all()
            )
            # Ensure access
            self.verify_and_commit()
            return self.success(data=groups)

        include_single_user_groups = self.get_query_argument(
            "includeSingleUserGroups", False
        )
        info = {}
        info['user_groups'] = sorted(
            list(self.current_user.groups), key=lambda g: g.name.lower()
        )
        info['user_accessible_groups'] = sorted(
            [g for g in self.current_user.accessible_groups if not g.single_user_group],
            key=lambda g: g.name.lower(),
        )
        all_groups_query = Group.query_records_accessible_by(self.current_user)
        if (not include_single_user_groups) or (
            isinstance(include_single_user_groups, str)
            and include_single_user_groups.lower() == "false"
        ):
            all_groups_query = all_groups_query.filter(
                Group.single_user_group.is_(False)
            )
        info["all_groups"] = sorted(
            all_groups_query.all(), key=lambda g: g.name.lower()
        )
        self.verify_and_commit()

        return self.success(data=info)

    @permissions(["Upload data"])
    def post(self):
        """
        ---
        description: Create a new group
        tags:
          - groups
        requestBody:
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/GroupNoID'
                  - type: object
                    properties:
                      group_admins:
                        type: array
                        items:
                          type: integer
                        description: |
                          List of IDs of users to be group admins. Current user will
                          automatically be added as a group admin.
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
                              description: New group ID
        """
        data = self.get_json()
        if data.get("name") is None or (
            isinstance(data.get("name"), str) and data.get("name").strip() == ""
        ):
            return self.error("Missing required parameter: `name`")

        try:
            group_admin_ids = [int(e) for e in data.get('group_admins', [])]
        except ValueError:
            return self.error(
                "Invalid group_admins field; unable to parse all items to int"
            )
        group_admins = (
            User.query_records_accessible_by(self.current_user)
            .filter(User.id.in_(group_admin_ids))
            .all()
        )
        if self.current_user not in group_admins and not isinstance(
            self.current_user, Token
        ):
            group_admins.append(self.current_user)

        g = Group(name=data["name"], nickname=data.get("nickname") or None)
        DBSession().add(g)
        DBSession().add_all(
            [GroupUser(group=g, user=user, admin=True) for user in group_admins]
        )
        self.verify_and_commit()
        return self.success(data={"id": g.id})

    @permissions(["Upload data"])
    def put(self, group_id):
        """
        ---
        description: Update a group
        tags:
          - groups
        parameters:
          - in: path
            name: group_id
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: GroupNoID
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

        data = self.get_json()
        data['id'] = group_id

        # permission check
        _ = Group.get_if_accessible_by(
            group_id, self.current_user, raise_if_none=True, mode='update'
        )
        schema = Group.__schema__()

        try:
            schema.load(data)
        except ValidationError as e:
            return self.error(
                'Invalid/missing parameters: ' f'{e.normalized_messages()}'
            )

        self.verify_and_commit()
        return self.success(action='skyportal/FETCH_GROUPS')

    @permissions(["Upload data"])
    def delete(self, group_id):
        """
        ---
        description: Delete a group
        tags:
          - groups
        parameters:
          - in: path
            name: group_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        g = Group.get_if_accessible_by(
            group_id, self.current_user, raise_if_none=True, mode='delete'
        )
        DBSession().delete(g)
        self.verify_and_commit()
        self.push_all(
            action='skyportal/REFRESH_GROUP', payload={'group_id': int(group_id)}
        )
        return self.success()


class GroupUserHandler(BaseHandler):
    @permissions(["Upload data"])
    def post(self, group_id, *ignored_args):
        """
        ---
        description: Add a group user
        tags:
          - groups
          - users
        parameters:
          - in: path
            name: group_id
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
                  canSave:
                    type: boolean
                    description: Boolean indicating whether user can save sources to group. Defaults to true.
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
                            group_id:
                              type: integer
                              description: Group ID
                            user_id:
                              type: integer
                              description: User ID
                            admin:
                              type: boolean
                              description: Boolean indicating whether user is group admin
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
        can_save = data.get("canSave", True)
        if not isinstance(can_save, bool):
            return self.error(
                "Invalid (non-boolean) value provided for parameter `canSave`"
            )
        group_id = int(group_id)
        group = Group.get_if_accessible_by(
            group_id, self.current_user, raise_if_none=True, mode='read'
        )
        user = User.get_if_accessible_by(
            user_id, self.current_user, raise_if_none=True, mode='read'
        )

        # Add user to group
        gu = (
            GroupUser.query.filter(GroupUser.group_id == group_id)
            .filter(GroupUser.user_id == user_id)
            .first()
        )
        if gu is not None:
            return self.error(
                f"User {user_id} is already a member of group {group_id}."
            )

        DBSession().add(
            GroupUser(
                group_id=group_id, user_id=user_id, admin=admin, can_save=can_save
            )
        )
        DBSession().add(
            UserNotification(
                user=user,
                text=f"You've been added to group *{group.name}*",
                url=f"/group/{group.id}",
            )
        )
        self.verify_and_commit()
        self.flow.push(user.id, "skyportal/FETCH_NOTIFICATIONS", {})

        self.push_all(action='skyportal/REFRESH_GROUP', payload={'group_id': group_id})
        return self.success(
            data={'group_id': group_id, 'user_id': user_id, 'admin': admin}
        )

    @permissions(["Upload data"])
    def patch(self, group_id, *ignored_args):
        """
        ---
        description: Update a group user's admin or save access status
        tags:
          - groups
          - users
        parameters:
          - in: path
            name: group_id
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
                      Boolean indicating whether user is group admin. Either this
                      or `canSave` must be provided in request body.
                  canSave:
                    type: boolean
                    description: |
                      Boolean indicating whether user can save sources to group. Either
                      this or `admin` must be provided in request body.
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
            group_id = int(group_id)
        except ValueError:
            return self.error("Invalid group ID")

        user_id = data.get("userID")
        try:
            user_id = int(user_id)
        except ValueError:
            return self.error("Invalid userID parameter")

        groupuser = (
            GroupUser.query_records_accessible_by(self.current_user, mode='update')
            .filter(GroupUser.group_id == group_id)
            .filter(GroupUser.user_id == user_id)
            .first()
        )

        if groupuser is None:
            return self.error(f"User {user_id} is not a member of group {group_id}.")

        if data.get("admin") is None and data.get("canSave") is None:
            return self.error(
                "Missing required parameter: at least one of `admin` or `canSave`"
            )
        admin = data.get("admin", groupuser.admin)
        if not isinstance(admin, bool):
            return self.error(
                "Invalid (non-boolean) value provided for parameter `admin`"
            )
        can_save = data.get("canSave", groupuser.can_save)
        if not isinstance(can_save, bool):
            return self.error(
                "Invalid (non-boolean) value provided for parameter `canSave`"
            )
        groupuser.admin = admin
        groupuser.can_save = can_save
        self.verify_and_commit()
        return self.success()

    @auth_or_token
    def delete(self, group_id, user_id):
        """
        ---
        description: Delete a group user
        tags:
          - groups
          - users
        parameters:
          - in: path
            name: group_id
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

        gu = (
            GroupUser.query_records_accessible_by(self.current_user, mode='delete')
            .filter(GroupUser.group_id == group_id)
            .filter(GroupUser.user_id == user_id)
            .first()
        )

        if gu is None:
            raise AccessError("GroupUser does not exist.")

        DBSession().delete(gu)
        self.verify_and_commit()
        self.push_all(
            action='skyportal/REFRESH_GROUP', payload={'group_id': int(group_id)}
        )
        return self.success()


class GroupUsersFromOtherGroupsHandler(BaseHandler):
    @permissions(["Upload data"])
    def post(self, group_id, *ignored_args):
        """
        ---
        description: Add users from other group(s) to specified group
        tags:
          - groups
          - users
        parameters:
          - in: path
            name: group_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  fromGroupIDs:
                    type: array
                    items:
                      type: integer
                    type: boolean
                required:
                  - fromGroupIDs
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        try:
            group_id = int(group_id)
        except (TypeError, ValueError):
            return self.error("Invalid group_id parameter: must be an integer")

        data = self.get_json()

        from_group_ids = data.get("fromGroupIDs")
        if from_group_ids is None:
            return self.error("Missing required parameter: fromGroupIDs")
        if not isinstance(from_group_ids, (list, tuple)):
            return self.error(
                "Improperly formatted fromGroupIDs parameter; "
                "must be an array of integers."
            )
        group = Group.get_if_accessible_by(
            group_id, self.current_user, mode="read", raise_if_none=True
        )
        from_groups = Group.get_if_accessible_by(
            from_group_ids, self.current_user, mode='read', raise_if_none=True
        )

        user_ids = set()
        for from_group in from_groups:
            for user in from_group.users:
                user_ids.add(user.id)

        for user_id in user_ids:
            # Add user to group
            gu = (
                GroupUser.query.filter(GroupUser.group_id == group_id)
                .filter(GroupUser.user_id == user_id)
                .first()
            )
            if gu is None:
                DBSession().add(
                    GroupUser(group_id=group_id, user_id=user_id, admin=False)
                )
                DBSession().add(
                    UserNotification(
                        user_id=user_id,
                        text=f"You've been added to group *{group.name}*",
                        url=f"/group/{group.id}",
                    )
                )

        self.verify_and_commit()

        self.push_all(action='skyportal/REFRESH_GROUP', payload={'group_id': group_id})
        for user_id in user_ids:
            self.flow.push(user_id, "skyportal/FETCH_NOTIFICATIONS", {})
        return self.success()


class GroupStreamHandler(BaseHandler):
    @permissions(["Upload data"])
    def post(self, group_id, *ignored_args):
        """
        ---
        description: Add alert stream access to group
        tags:
          - groups
          - streams
        parameters:
          - in: path
            name: group_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  stream_id:
                    type: integer
                required:
                  - stream_id
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
                            group_id:
                              type: integer
                              description: Group ID
                            stream_id:
                              type: integer
                              description: Stream ID
        """
        data = self.get_json()
        group_id = int(group_id)
        stream_id = data.get('stream_id')

        # Add new GroupStream
        gs = GroupStream.query.filter(
            GroupStream.group_id == group_id, GroupStream.stream_id == stream_id
        ).first()
        if gs is None:
            DBSession.add(GroupStream(group_id=group_id, stream_id=stream_id))
        else:
            return self.error("Specified stream is already associated with this group.")
        self.verify_and_commit()

        self.push_all(action='skyportal/REFRESH_GROUP', payload={'group_id': group_id})
        return self.success(data={'group_id': group_id, 'stream_id': stream_id})

    @permissions(["Upload data"])
    def delete(self, group_id, stream_id):
        """
        ---
        description: Delete an alert stream from group
        tags:
          - groups
          - streams
        parameters:
          - in: path
            name: group_id
            required: true
            schema:
              type: integer
          - in: path
            name: stream_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        groupstreams = (
            GroupStream.query_records_accessible_by(self.current_user)
            .filter(GroupStream.group_id == group_id)
            .filter(GroupStream.stream_id == stream_id)
            .all()
        )

        for gs in groupstreams:
            DBSession().delete(gs)

        self.verify_and_commit()
        self.push_all(
            action='skyportal/REFRESH_GROUP', payload={'group_id': int(group_id)}
        )
        return self.success()


class ObjGroupsHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id):
        """
        ---
        description: Retrieve basic info on Groups that an Obj is saved to
        tags:
          - groups
          - sources
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: ArrayOfGroups
          400:
            content:
              application/json:
                schema: Error
        """
        s = Obj.get_if_accessible_by(obj_id, self.current_user)

        if s is None:
            return self.error("Source not found", status=404)

        source_info = s.to_dict()

        query = (
            Group.query_records_accessible_by(self.current_user, mode="read")
            .join(Source)
            .filter(
                Source.obj_id == source_info["id"],
            )
        )
        query = query.filter(or_(Source.requested.is_(True), Source.active.is_(True)))
        groups = [g.to_dict() for g in query.all()]
        self.verify_and_commit()
        return self.success(data=groups)
