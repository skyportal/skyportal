from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from baselayer.app.env import load_env
from ..base import BaseHandler
from ...models import (
    DBSession,
    Filter,
    Group,
    GroupStream,
    GroupUser,
    Obj,
    Source,
    Stream,
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
        {"System admin", "Manage groups"}.intersection(set(user.permissions))
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
            group = Group.query.get(group_id)
            if group is None:
                return self.error(f"Could not load group with ID {group_id}")
            # If not super admin or member of group
            if (
                not {"System admin", "Manage groups"}.intersection(
                    set(self.associated_user_object.permissions)
                )
            ) and group.id not in [g.id for g in self.current_user.accessible_groups]:
                return self.error('Insufficient permissions.')

            # Do not include User.groups to avoid circular reference
            users = [
                {
                    "id": user.id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "contact_email": user.contact_email,
                    "contact_phone": user.contact_phone,
                    "oauth_uid": user.oauth_uid,
                    "admin": has_admin_access_for_group(user, group_id),
                }
                for user in group.users
            ]
            group = group.to_dict()
            group['users'] = users
            # grab streams:
            streams = (
                DBSession()
                .query(Stream)
                .join(GroupStream)
                .filter(GroupStream.group_id == group_id)
                .all()
            )
            group['streams'] = streams
            # grab filters:
            filters = (
                DBSession().query(Filter).filter(Filter.group_id == group_id).all()
            )
            group['filters'] = filters

            self.verify_permissions()
            return self.success(data=group)
        group_name = self.get_query_argument("name", None)
        if group_name is not None:
            groups = Group.query.filter(Group.name == group_name).all()
            # Ensure access
            if not all(
                [group in self.current_user.accessible_groups for group in groups]
            ):
                return self.error("Insufficient permissions")
            self.verify_permissions()
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
        all_groups_query = Group.query
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
        self.verify_permissions()
        return self.success(data=info)

    @auth_or_token
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
        group_admins = User.query.filter(User.id.in_(group_admin_ids)).all()
        if self.current_user not in group_admins and not isinstance(
            self.current_user, Token
        ):
            group_admins.append(self.current_user)

        g = Group(name=data["name"], nickname=data.get("nickname") or None)
        DBSession().add(g)
        self.verify_permissions()
        DBSession().flush()
        DBSession().add_all(
            [GroupUser(group=g, user=user, admin=True) for user in group_admins]
        )
        self.finalize_transaction()

        return self.success(data={"id": g.id})

    @auth_or_token
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
        groupuser = (
            DBSession()
            .query(GroupUser)
            .filter(GroupUser.group_id == group_id)
            .filter(GroupUser.user_id == self.associated_user_object.id)
            .first()
        )
        if (
            "Manage groups" not in self.associated_user_object.permissions
            and not groupuser.admin
        ):
            return self.error(
                "Insufficient permissions. You must either be a group admin or have higher site-wide permissions."
            )

        data = self.get_json()
        data['id'] = group_id

        schema = Group.__schema__()
        try:
            schema.load(data)
        except ValidationError as e:
            return self.error(
                'Invalid/missing parameters: ' f'{e.normalized_messages()}'
            )
        self.finalize_transaction()

        return self.success(action='skyportal/FETCH_GROUPS')

    @auth_or_token
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
        g = Group.query.get(group_id)
        if g.name == cfg["misc"]["public_group_name"]:
            return self.error("Cannot delete site-wide public group.")
        groupuser = (
            DBSession()
            .query(GroupUser)
            .filter(GroupUser.group_id == group_id)
            .filter(GroupUser.user_id == self.associated_user_object.id)
            .first()
        )
        if (
            "Manage groups" not in self.associated_user_object.permissions
            and not groupuser.admin
        ):
            return self.error(
                "Insufficient permissions. You must either be a group admin or have higher site-wide permissions."
            )
        DBSession().delete(g)
        self.finalize_transaction()

        self.push_all(
            action='skyportal/REFRESH_GROUP', payload={'group_id': int(group_id)}
        )
        return self.success()


class GroupUserHandler(BaseHandler):
    @auth_or_token
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
        if not has_admin_access_for_group(self.associated_user_object, group_id):
            return self.error("Inadequate permissions.")

        data = self.get_json()

        user_id = data.pop("userID", None)
        if user_id is None:
            return self.error("userID parameter must be specified")
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            return self.error("Invalid userID parameter: unable to parse to integer")

        admin = data.pop("admin", False)
        group_id = int(group_id)
        group = Group.query.get(group_id)
        if group.single_user_group:
            return self.error("Cannot add users to single-user groups.")
        user = User.query.get(user_id)
        if user is None:
            return self.error(f"Invalid userID parameter: {user_id}")

        # Ensure user has sufficient stream access to be added to group
        if group.streams:
            if not all([stream in user.accessible_streams for stream in group.streams]):
                return self.error(
                    "User does not have sufficient stream access "
                    "to be added to this group."
                )
        # Add user to group
        gu = (
            GroupUser.query.filter(GroupUser.group_id == group_id)
            .filter(GroupUser.user_id == user_id)
            .first()
        )
        if gu is not None:
            return self.error("Specified user is already a member of this group.")

        DBSession().add(GroupUser(group_id=group_id, user_id=user_id, admin=admin))
        DBSession().add(
            UserNotification(
                user=user,
                text=f"You've been added to group {group.name}",
                url=f"/group/{group.id}",
            )
        )
        self.finalize_transaction()
        self.flow.push(user.id, "skyportal/FETCH_NOTIFICATIONS", {})

        self.push_all(action='skyportal/REFRESH_GROUP', payload={'group_id': group_id})
        return self.success(
            data={'group_id': group_id, 'user_id': user_id, 'admin': admin}
        )

    @permissions(["Manage users"])
    def patch(self, group_id, *ignored_args):
        """
        ---
        description: Update a group user's admin status
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
                required:
                  - userID
                  - admin
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
            DBSession()
            .query(GroupUser)
            .filter(GroupUser.group_id == group_id)
            .filter(GroupUser.user_id == user_id)
            .first()
        )
        if groupuser is None:
            return self.error("Specified user is not a member of specified group.")
        if data.get("admin") is None:
            return self.error("Missing required parameter: `admin`")
        admin = data.get("admin") in [True, "true", "True", "t", "T"]
        groupuser.admin = admin
        self.finalize_transaction()
        return self.success()

    @permissions(["Manage users"])
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
        if not has_admin_access_for_group(self.associated_user_object, group_id):
            return self.error("Inadequate permissions.")

        group = Group.query.get(group_id)
        if group.single_user_group:
            return self.error("Cannot delete users from single user groups.")
        try:
            user_id = int(user_id)
        except ValueError:
            return self.error("Invalid user_id; unable to parse to integer")
        (
            GroupUser.query.filter(GroupUser.group_id == group_id)
            .filter(GroupUser.user_id == user_id)
            .delete()
        )
        self.finalize_transaction()
        self.push_all(
            action='skyportal/REFRESH_GROUP', payload={'group_id': int(group_id)}
        )
        return self.success()


class GroupUsersFromOtherGroupsHandler(BaseHandler):
    @auth_or_token
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

        if not has_admin_access_for_group(self.associated_user_object, group_id):
            return self.error("Requesting user is not an admin of this group.")

        data = self.get_json()

        from_group_ids = data.get("fromGroupIDs")
        if from_group_ids is None:
            return self.error("Missing required parameter: fromGroupIDs")
        if not isinstance(from_group_ids, (list, tuple)):
            return self.error(
                "Improperly formatted fromGroupIDs parameter; "
                "must be an array of integers."
            )
        group = DBSession().query(Group).get(group_id)
        if group is None:
            return self.error("Invalid group_id value")
        from_groups = (
            DBSession().query(Group).filter(Group.id.in_(from_group_ids)).all()
        )
        if len(from_groups) != len(set(from_group_ids)):
            return self.error("One or more invalid IDs in fromGroupIDs parameter.")
        user_ids = set()
        for from_group in from_groups:
            for user in from_group.users:
                # Ensure user has sufficient stream access to be added to group
                if from_group.streams:
                    if not all(
                        [stream in user.streams for stream in from_group.streams]
                    ):
                        return self.error(
                            "Not all users have sufficient stream access "
                            "to be added to this group."
                        )
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
                        text=f"You've been added to group {group.name}",
                        url=f"/group/{group.id}",
                    )
                )

        self.finalize_transaction()

        self.push_all(action='skyportal/REFRESH_GROUP', payload={'group_id': group_id})
        for user_id in user_ids:
            self.flow.push(user_id, "skyportal/FETCH_NOTIFICATIONS", {})
        return self.success()


class GroupStreamHandler(BaseHandler):
    @permissions(['System admin'])
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
        # group = Group.query.filter(Group.id == group_id).first()
        group = (
            Group.query.options(joinedload(Group.users))
            .options(joinedload(Group.group_users))
            .get(group_id)
        )
        if group is None:
            return self.error("Specified group_id does not exist.")
        stream_id = data.get('stream_id')
        stream = Stream.query.filter(Stream.id == stream_id).first()
        if stream is None:
            return self.error("Specified stream_id does not exist.")
        # TODO ensure all current group users have access to this stream
        # TODO do the check
        # Add new GroupStream
        gs = GroupStream.query.filter(
            GroupStream.group_id == group_id, GroupStream.stream_id == stream_id
        ).first()
        if gs is None:
            DBSession.add(GroupStream(group_id=group_id, stream_id=stream_id))
        else:
            return self.error("Specified stream is already associated with this group.")
        self.finalize_transaction()

        self.push_all(action='skyportal/REFRESH_GROUP', payload={'group_id': group_id})
        return self.success(data={'group_id': group_id, 'stream_id': stream_id})

    @permissions(['System admin'])
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
        stream = Stream.query.filter(Stream.id == int(stream_id)).first()
        stream_id = stream.id
        if stream is None:
            return self.error("Specified stream_id does not exist.")
        else:
            (
                GroupStream.query.filter(GroupStream.group_id == group_id)
                .filter(GroupStream.stream_id == stream_id)
                .delete()
            )
            self.finalize_transaction()
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
        s = Obj.get_if_readable_by(obj_id, self.current_user)

        if s is None:
            return self.error("Source not found", status=404)

        source_info = s.to_dict()

        user_accessible_group_ids = [g.id for g in self.current_user.accessible_groups]

        query = (
            DBSession()
            .query(Group)
            .join(Source)
            .filter(
                Source.obj_id == source_info["id"],
                Group.id.in_(user_accessible_group_ids),
            )
        )
        query = query.filter(or_(Source.requested.is_(True), Source.active.is_(True)))
        groups = [g.to_dict() for g in query.all()]
        self.verify_permissions()
        return self.success(data=groups)
