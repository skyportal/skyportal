import sqlalchemy as sa
from marshmallow.exceptions import ValidationError
from sqlalchemy import or_

from baselayer.app.access import AccessError, auth_or_token, permissions
from baselayer.app.env import load_env
from baselayer.log import make_log

from ...models import (
    Group,
    GroupStream,
    GroupUser,
    Obj,
    Source,
    Token,
    User,
    UserNotification,
)
from ..base import BaseHandler

_, cfg = load_env()


def has_admin_access_for_group(user, group_id, session):
    groupuser = session.scalar(
        GroupUser.select(user).where(
            GroupUser.group_id == group_id, GroupUser.user_id == user.id
        )
    )
    return len(
        {"System admin", "Manage groups", "Manage_users"}.intersection(
            set(user.permissions)
        )
    ) > 0 or (groupuser is not None and groupuser.admin)


log = make_log("api/group")


class GroupHandler(BaseHandler):
    @auth_or_token
    def get(self, group_id=None):
        """
        ---
        single:
          summary: Get a group
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
                                      $ref: '#/components/schemas/User'
                                    description: List of group users
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          summary: Get all groups
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

        with self.Session() as session:
            if group_id is not None:
                group = session.scalars(
                    Group.select(session.user_or_token).where(Group.id == group_id)
                ).first()
                if group is None:
                    return self.error(f"Cannot find Group with id {group_id}")
                include_group_users = self.get_query_argument("includeGroupUsers", True)

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
                    group["users"] = users

                # grab streams:
                group["streams"] = streams

                group["filters"] = filters
                try:
                    # grab filters:
                    # this is in a try-except in case of deletions
                    session.commit()
                    group["filters"] = filters
                except AccessError as e:
                    log(f"Insufficient filter permissions: {e}.")

                return self.success(data=group)

            group_name = self.get_query_argument("name", None)
            if group_name is not None:
                groups = session.scalars(
                    Group.select(session.user_or_token).where(Group.name == group_name)
                ).all()
                return self.success(data=groups)

            include_single_user_groups = self.get_query_argument(
                "includeSingleUserGroups", False
            )
            info = {}
            info["user_groups"] = sorted(
                self.current_user.groups, key=lambda g: g.name.lower()
            )
            info["user_accessible_groups"] = sorted(
                (
                    g
                    for g in self.current_user.accessible_groups
                    if not g.single_user_group
                ),
                key=lambda g: g.name.lower(),
            )
            all_groups_query = Group.select(session.user_or_token)
            if not include_single_user_groups:
                all_groups_query = all_groups_query.where(
                    Group.single_user_group.is_(False)
                )
            info["all_groups"] = sorted(
                session.scalars(all_groups_query).unique().all(),
                key=lambda g: g.name.lower(),
            )

            return self.success(data=info)

    @permissions(["Upload data"])
    def post(self):
        """
        ---
        summary: Create a new group
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
            group_admin_ids = [int(e) for e in data.get("group_admins", [])]
        except ValueError:
            return self.error(
                "Invalid group_admins field; unable to parse all items to int"
            )

        with self.Session() as session:
            group_admins = session.scalars(
                User.select(self.current_user).where(User.id.in_(group_admin_ids))
            ).all()
            if self.current_user.id not in [
                u.id for u in group_admins
            ] and not isinstance(self.current_user, Token):
                group_admins.append(self.current_user)

            existing_group = session.scalars(
                Group.select(session.user_or_token).where(Group.name == data["name"])
            ).first()
            if existing_group is not None:
                return self.error(
                    f"Group with name {data['name']} already exists. Please select a new one."
                )

            g = Group(
                name=data["name"],
                nickname=data.get("nickname") or None,
                description=data.get("description") or None,
            )

            session.add(g)

            for user in group_admins:
                session.merge(user)

            session.add_all(
                [GroupUser(group=g, user=user, admin=True) for user in group_admins]
            )

            session.commit()
            return self.success(data={"id": g.id})

    @permissions(["Upload data"])
    def put(self, group_id):
        """
        ---
        summary: Update a group
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
        data["id"] = group_id

        with self.Session() as session:
            # permission check
            group = session.scalars(
                Group.select(session.user_or_token, mode="update").where(
                    Group.id == group_id
                )
            ).first()
            if group is None:
                return self.error(f"Cannot find Group with id {group_id}")
            schema = Group.__schema__()

            try:
                schema.load(data)
            except ValidationError as e:
                return self.error(
                    f"Invalid/missing parameters: {e.normalized_messages()}"
                )

            for k in data:
                setattr(group, k, data[k])

            session.commit()
            return self.success(action="skyportal/FETCH_GROUPS")

    @permissions(["Upload data"])
    def delete(self, group_id):
        """
        ---
        summary: Delete a group
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

        with self.Session() as session:
            # permission check
            group = session.scalars(
                Group.select(session.user_or_token, mode="delete").where(
                    Group.id == group_id
                )
            ).first()
            if group is None:
                return self.error(
                    f"Cannot find Group with id {group_id}",
                    status=403,
                )

            session.delete(group)
            session.commit()
            self.push_all(
                action="skyportal/REFRESH_GROUP", payload={"group_id": int(group_id)}
            )
            return self.success()


class GroupUserHandler(BaseHandler):
    @permissions(["Upload data"])
    def post(self, group_id, *ignored_args):
        """
        ---
        summary: Add a group user
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

        with self.Session() as session:
            group = session.scalars(
                Group.select(session.user_or_token, mode="update").where(
                    Group.id == group_id
                )
            ).first()
            if group is None:
                return self.error(f"Group with ID {group_id} not accessible")
            if group.single_user_group:
                return self.error(
                    f"Cannot add users to group {group_id}. It is a single user group."
                )

            user = session.scalars(
                User.select(session.user_or_token).where(User.id == user_id)
            ).first()
            if user is None:
                return self.error(f"User with ID {user_id} not accessible")

            user_streams = [stream.id for stream in user.streams]
            for stream in group.streams:
                if stream.id not in user_streams:
                    return self.error(
                        f"User with ID {user_id} ({user.username}) does not have stream access with ID {stream.id} ({stream.name}). Please contact a super-admin to grant access.",
                        status=403,
                    )

            # Add user to group
            gu = session.scalars(
                GroupUser.select(session.user_or_token)
                .where(GroupUser.group_id == group_id)
                .where(GroupUser.user_id == user_id)
            ).first()
            if gu is not None:
                return self.error(
                    f"User {user_id} is already a member of group {group_id}."
                )

            session.add(
                GroupUser(
                    group_id=group_id, user_id=user_id, admin=admin, can_save=can_save
                )
            )
            session.add(
                UserNotification(
                    user=user,
                    text=f"You've been added to group *{group.name}*",
                    url=f"/group/{group.id}",
                )
            )
            session.commit()
            self.flow.push(user.id, "skyportal/FETCH_NOTIFICATIONS", {})

            self.push_all(
                action="skyportal/REFRESH_GROUP", payload={"group_id": group_id}
            )
            return self.success(
                data={"group_id": group_id, "user_id": user_id, "admin": admin}
            )

    @permissions(["Upload data"])
    def patch(self, group_id, *ignored_args):
        """
        ---
        summary: Update a group user
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

        with self.Session() as session:
            groupuser = session.scalars(
                GroupUser.select(session.user_or_token, mode="update")
                .where(GroupUser.group_id == group_id)
                .where(GroupUser.user_id == user_id)
            ).first()

            if groupuser is None:
                return self.error(
                    f"User {user_id} is not a member of group {group_id}."
                )

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
            session.commit()
            return self.success()

    @auth_or_token
    def delete(self, group_id, user_id):
        """
        ---
        summary: Delete a group user
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

        with self.Session() as session:
            gu = session.scalars(
                GroupUser.select(session.user_or_token, mode="delete")
                .where(GroupUser.group_id == group_id)
                .where(GroupUser.user_id == user_id)
            ).first()
            if gu is None:
                return self.error("GroupUser does not exist.", status=403)

            session.delete(gu)
            # Check for delete permissions
            try:
                session.commit()
            except AccessError as e:
                return self.error(f"Insufficient group permissions: {e}.", status=403)

            self.flow.push(user_id, "skyportal/FETCH_GROUPS")
            self.flow.push(user_id, "skyportal/FETCH_SOURCES")
            self.push_all(
                action="skyportal/REFRESH_GROUP", payload={"group_id": int(group_id)}
            )
            return self.success()


class GroupUsersFromOtherGroupsHandler(BaseHandler):
    @permissions(["Upload data"])
    def post(self, group_id, *ignored_args):
        """
        ---
        summary: Add users from other group(s)
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
        if not isinstance(from_group_ids, list | tuple):
            return self.error(
                "Improperly formatted fromGroupIDs parameter; "
                "must be an array of integers."
            )

        with self.Session() as session:
            group = session.scalars(
                Group.select(self.current_user).where(Group.id == group_id)
            ).first()
            if group is None:
                return self.error("Cannot access group with given ID.")

            from_groups = session.scalars(
                Group.select(self.current_user).where(Group.id.in_(from_group_ids))
            ).all()
            if set(from_group_ids) != {g.id for g in from_groups}:
                return self.error(
                    "Cannot access one or more groups with given by fromGroupIDs."
                )

            user_ids = set()
            for from_group in from_groups:
                for user in from_group.users:
                    user_ids.add(user.id)

            for user_id in user_ids:
                # Add user to group
                gu = session.scalars(
                    sa.select(GroupUser)
                    .where(GroupUser.group_id == group_id)
                    .where(GroupUser.user_id == user_id)
                ).first()
                user = session.scalars(
                    sa.select(User).where(User.id == user_id)
                ).first()
                if gu is None:
                    session.add(
                        GroupUser(group_id=group_id, user_id=user_id, admin=False)
                    )
                    session.add(
                        UserNotification(
                            user=user,
                            user_id=user_id,
                            text=f"You've been added to group *{group.name}*",
                            url=f"/group/{group.id}",
                        )
                    )

            session.commit()

        self.push_all(action="skyportal/REFRESH_GROUP", payload={"group_id": group_id})
        for user_id in user_ids:
            self.flow.push(user_id, "skyportal/FETCH_NOTIFICATIONS", {})
        return self.success()


class GroupStreamHandler(BaseHandler):
    @permissions(["Upload data"])
    def post(self, group_id, *ignored_args):
        """
        ---
        summary: Add alert stream to group
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
        stream_id = data.get("stream_id")

        with self.Session() as session:
            group = session.scalars(
                Group.select(session.user_or_token, mode="update").where(
                    Group.id == group_id
                )
            ).first()
            if group is None:
                return self.error(f"Group with ID {group_id} not accessible")
            if group.single_user_group:
                return self.error(
                    f"Cannot add users to group {group_id}. It is a single user group."
                )

            for user in group.users:
                user_streams = [stream.id for stream in user.streams]
                if stream_id not in user_streams:
                    return self.error(
                        f"Not all users have stream access with ID {stream_id}",
                        status=403,
                    )

            # Add new GroupStream
            gs = session.scalars(
                GroupStream.select(session.user_or_token).where(
                    GroupStream.group_id == group_id, GroupStream.stream_id == stream_id
                )
            ).first()
            if gs is None:
                session.add(GroupStream(group_id=group_id, stream_id=stream_id))
            else:
                return self.error(
                    "Specified stream is already associated with this group."
                )
            session.commit()

            self.push_all(
                action="skyportal/REFRESH_GROUP", payload={"group_id": group_id}
            )
            return self.success(data={"group_id": group_id, "stream_id": stream_id})

    @permissions(["Upload data"])
    def delete(self, group_id, stream_id):
        """
        ---
        summary: Delete alert stream from group
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

        with self.Session() as session:
            groupstreams = session.scalars(
                GroupStream.select(session.user_or_token, mode="delete")
                .where(GroupStream.group_id == group_id)
                .where(GroupStream.stream_id == stream_id)
            ).all()
            if len(groupstreams) == 0:
                return self.error(f"No stream IDs with ID {stream_id} accessible")
            for gs in groupstreams:
                session.delete(gs)

            session.commit()
            self.push_all(
                action="skyportal/REFRESH_GROUP", payload={"group_id": int(group_id)}
            )
            return self.success()


class ObjGroupsHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id):
        """
        ---
        summary: Get an object's groups
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

        with self.Session() as session:
            s = session.scalars(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            ).first()
            if s is None:
                return self.error("Source not found", status=404)

            source_info = s.to_dict()
            query = (
                Group.select(session.user_or_token)
                .join(Source)
                .where(Source.obj_id == source_info["id"])
            )
            query = query.where(
                or_(Source.requested.is_(True), Source.active.is_(True))
            )
            groups = [g.to_dict() for g in session.scalars(query).unique().all()]
            return self.success(data=groups)
