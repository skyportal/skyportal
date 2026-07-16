import sqlalchemy as sa
from marshmallow.exceptions import ValidationError
from sqlalchemy import or_
from sqlalchemy.orm import selectinload

from baselayer.app.access import AccessError, auth_or_token, permissions
from baselayer.app.env import load_env
from baselayer.app.models import RoleACL, UserACL, UserRole
from skyportal.log import make_log

from ...models import (
    Filter,
    Group,
    GroupStream,
    GroupUser,
    Obj,
    Source,
    StreamUser,
    Token,
    User,
    UserNotification,
)
from ..base import BaseHandler

_, cfg = load_env()


async def has_admin_access_for_group(user, group_id, session):
    """Async variant of has_admin_access_for_group. Looks up the user's
    permission set via an explicit query (instead of touching the lazy
    ``user.permissions`` property) so it works under an async session.
    """
    groupuser = await session.scalar(
        GroupUser.select(user).where(
            GroupUser.group_id == group_id, GroupUser.user_id == user.id
        )
    )
    if groupuser is not None and groupuser.admin:
        return True
    direct = sa.select(UserACL.acl_id).where(UserACL.user_id == user.id)
    via_role = (
        sa.select(RoleACL.acl_id)
        .join(UserRole, UserRole.role_id == RoleACL.role_id)
        .where(UserRole.user_id == user.id)
    )
    combined = sa.union(direct, via_role).subquery()
    sysadmin_like = await session.scalar(
        sa.select(sa.func.count())
        .select_from(combined)
        .where(combined.c.acl_id.in_({"System admin", "Manage groups", "Manage_users"}))
    )
    return bool(sysadmin_like)


async def _user_is_system_admin(user_id, session):
    direct = sa.select(UserACL.acl_id).where(UserACL.user_id == user_id)
    via_role = (
        sa.select(RoleACL.acl_id)
        .join(UserRole, UserRole.role_id == RoleACL.role_id)
        .where(UserRole.user_id == user_id)
    )
    combined = sa.union(direct, via_role).subquery()
    count = await session.scalar(
        sa.select(sa.func.count())
        .select_from(combined)
        .where(combined.c.acl_id == "System admin")
    )
    return bool(count)


log = make_log("api/group")


class GroupHandler(BaseHandler):
    @auth_or_token
    async def get(self, group_id: int | None = None):
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

        if group_id is not None:
            try:
                group_id = int(group_id)
            except (TypeError, ValueError):
                return self.error(f"Invalid group_id: {group_id}")
        async with self.AsyncSession() as session:
            if group_id is not None:
                group = await session.scalar(
                    Group.select(session.user_or_token)
                    .options(
                        selectinload(Group.group_users).selectinload(GroupUser.user),
                        selectinload(Group.streams),
                        selectinload(Group.filters),
                    )
                    .where(Group.id == group_id)
                )
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

                streams = list(group.streams)
                filters = list(group.filters)

                group = group.to_dict()

                if users is not None:
                    group["users"] = users

                group["streams"] = streams
                group["filters"] = filters
                try:
                    # commit to surface any access-control errors picked up on flush
                    await session.commit()
                    group["filters"] = filters
                except AccessError as e:
                    log.info(f"Insufficient filter permissions: {e}.")

                return self.success(data=group)

            group_name = self.get_query_argument("name", None)
            if group_name is not None:
                result = await session.scalars(
                    Group.select(session.user_or_token).where(Group.name == group_name)
                )
                return self.success(data=result.unique().all())

            include_single_user_groups = self.get_query_argument(
                "includeSingleUserGroups", False
            )

            user_id = self.associated_user_object.id

            # user_groups = groups the user is a direct member of
            user_groups_stmt = (
                sa.select(Group)
                .join(GroupUser, GroupUser.group_id == Group.id)
                .where(GroupUser.user_id == user_id)
            )
            user_groups_result = await session.scalars(user_groups_stmt)
            user_groups = sorted(
                user_groups_result.unique().all(), key=lambda g: g.name.lower()
            )

            # user_accessible_groups: all for sysadmin, member groups otherwise
            is_sysadmin = await _user_is_system_admin(user_id, session)
            if is_sysadmin:
                accessible_stmt = sa.select(Group).where(
                    Group.single_user_group.is_(False)
                )
            else:
                accessible_stmt = (
                    sa.select(Group)
                    .join(GroupUser, GroupUser.group_id == Group.id)
                    .where(
                        GroupUser.user_id == user_id,
                        Group.single_user_group.is_(False),
                    )
                )
            accessible_result = await session.scalars(accessible_stmt)
            user_accessible_groups = sorted(
                accessible_result.unique().all(), key=lambda g: g.name.lower()
            )

            all_groups_query = Group.select(session.user_or_token)
            if not include_single_user_groups:
                all_groups_query = all_groups_query.where(
                    Group.single_user_group.is_(False)
                )
            all_groups_result = await session.scalars(all_groups_query)
            all_groups = sorted(
                all_groups_result.unique().all(), key=lambda g: g.name.lower()
            )

            return self.success(
                data={
                    "user_groups": user_groups,
                    "user_accessible_groups": user_accessible_groups,
                    "all_groups": all_groups,
                }
            )

    @permissions(["Upload data"])
    async def post(self):
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

        async with self.AsyncSession() as session:
            group_admins_result = await session.scalars(
                User.select(self.current_user).where(User.id.in_(group_admin_ids))
            )
            group_admins = list(group_admins_result.unique().all())
            current_user_id = self.associated_user_object.id
            if current_user_id not in [u.id for u in group_admins] and not isinstance(
                self.current_user, Token
            ):
                group_admins.append(self.associated_user_object)

            existing_group = await session.scalar(
                Group.select(session.user_or_token).where(Group.name == data["name"])
            )
            if existing_group is not None:
                return self.error(
                    f"Group with name {data['name']} already exists. Please select a new one."
                )

            g = Group(
                name=data["name"],
                nickname=data.get("nickname") or None,
                description=data.get("description") or None,
                auto_accept_requests=data.get("auto_accept_requests", False),
            )

            session.add(g)
            await session.flush()  # populate g.id

            for user in group_admins:
                # Avoid cascade conflict by linking via foreign key, not by
                # attaching the detached user instance.
                session.add(GroupUser(group_id=g.id, user_id=user.id, admin=True))

            await session.commit()
            return self.success(data={"id": g.id})

    @permissions(["Upload data"])
    async def put(self, group_id: int):
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
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          $ref: '#/components/schemas/Group'
          400:
            content:
              application/json:
                schema: Error
        """

        try:
            group_id = int(group_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid group_id: {group_id}")
        data = self.get_json()
        data["id"] = group_id

        async with self.AsyncSession() as session:
            group = await session.scalar(
                Group.select(session.user_or_token, mode="update").where(
                    Group.id == group_id
                )
            )
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

            await session.commit()
            return self.success(action="skyportal/FETCH_GROUPS")

    @permissions(["Upload data"])
    async def delete(self, group_id: int):
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

        try:
            group_id = int(group_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid group_id: {group_id}")
        async with self.AsyncSession() as session:
            group = await session.scalar(
                Group.select(session.user_or_token, mode="delete").where(
                    Group.id == group_id
                )
            )
            if group is None:
                return self.error(
                    f"Cannot find Group with id {group_id}",
                    status=403,
                )

            await session.delete(group)
            await session.commit()
            self.push_all(
                action="skyportal/REFRESH_GROUP", payload={"group_id": int(group_id)}
            )
            return self.success()


class GroupUserHandler(BaseHandler):
    @permissions(["Upload data"])
    async def post(self, group_id: int, *ignored_args):
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
        try:
            group_id = int(group_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid group_id: {group_id}")

        async with self.AsyncSession() as session:
            group = await session.scalar(
                Group.select(session.user_or_token, mode="update").where(
                    Group.id == group_id
                )
            )
            if group is None:
                return self.error(f"Group with ID {group_id} not accessible")
            if group.single_user_group:
                return self.error(
                    f"Cannot add users to group {group_id}. It is a single user group."
                )

            user = await session.scalar(
                User.select(session.user_or_token).where(User.id == user_id)
            )
            if user is None:
                return self.error(f"User with ID {user_id} not accessible")

            # Validate the user has access to every stream of the group via SQL
            # (avoid lazy `group.streams`/`user.streams`, whose access-controlled
            # load raises AccessError for a requester lacking read access to a
            # stream — same pattern as GroupStreamHandler.post below).
            missing_stream_id = await session.scalar(
                sa.select(GroupStream.stream_id)
                .where(
                    GroupStream.group_id == group_id,
                    ~sa.exists().where(
                        sa.and_(
                            StreamUser.user_id == user_id,
                            StreamUser.stream_id == GroupStream.stream_id,
                        )
                    ),
                )
                .limit(1)
            )
            if missing_stream_id is not None:
                return self.error(
                    f"User with ID {user_id} ({user.username}) does not have "
                    f"stream access with ID {missing_stream_id}. Please contact "
                    f"a super-admin to grant access.",
                    status=403,
                )

            gu = await session.scalar(
                GroupUser.select(session.user_or_token)
                .where(GroupUser.group_id == group_id)
                .where(GroupUser.user_id == user_id)
            )
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
                    user_id=user.id,
                    text=f"You've been added to group *{group.name}*",
                    url=f"/group/{group.id}",
                )
            )
            await session.commit()
            self.flow.push(user.id, "skyportal/FETCH_NOTIFICATIONS", {})

            self.push_all(
                action="skyportal/REFRESH_GROUP", payload={"group_id": group_id}
            )
            return self.success(
                data={"group_id": group_id, "user_id": user_id, "admin": admin}
            )

    @permissions(["Upload data"])
    async def patch(self, group_id: int, *ignored_args):
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
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          $ref: '#/components/schemas/GroupUser'
        """
        data = self.get_json()
        try:
            group_id = int(group_id)
        except (TypeError, ValueError):
            return self.error("Invalid group ID")

        user_id = data.get("userID")
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return self.error("Invalid userID parameter")

        async with self.AsyncSession() as session:
            groupuser = await session.scalar(
                GroupUser.select(session.user_or_token, mode="update")
                .where(GroupUser.group_id == group_id)
                .where(GroupUser.user_id == user_id)
            )

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
            await session.commit()
            return self.success()

    @auth_or_token
    async def delete(self, group_id: int, user_id: int):
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
            group_id = int(group_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid group_id/user_id: {group_id}/{user_id}")

        async with self.AsyncSession() as session:
            # FIXME: GroupUser.delete's access control excludes single-user
            # groups, but the async verify path doesn't enforce it yet
            # (CustomUserAccessControl.select_accessible_rows projects columns
            # out of subquery scope in baselayer). Enforce explicitly here
            # until the baselayer select_accessible_rows fix lands.
            group = await session.scalar(
                Group.select(session.user_or_token).where(Group.id == group_id)
            )
            if group is not None and group.single_user_group:
                return self.error(
                    "Cannot remove a user from their single user group.", status=403
                )

            gu = await session.scalar(
                GroupUser.select(session.user_or_token, mode="delete")
                .where(GroupUser.group_id == group_id)
                .where(GroupUser.user_id == user_id)
            )
            if gu is None:
                return self.error("GroupUser does not exist.", status=403)

            await session.delete(gu)
            try:
                await session.commit()
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
    async def post(self, group_id: int, *ignored_args):
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
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          $ref: '#/components/schemas/GroupUser'
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

        async with self.AsyncSession() as session:
            group = await session.scalar(
                Group.select(self.current_user).where(Group.id == group_id)
            )
            if group is None:
                return self.error("Cannot access group with given ID.")

            from_groups_result = await session.scalars(
                Group.select(self.current_user).where(Group.id.in_(from_group_ids))
            )
            from_groups = from_groups_result.unique().all()
            if set(from_group_ids) != {g.id for g in from_groups}:
                return self.error(
                    "Cannot access one or more groups with given by fromGroupIDs."
                )

            # Fetch user IDs in the from-groups via SQL (don't use lazy
            # `from_group.users`).
            user_ids_result = await session.scalars(
                sa.select(GroupUser.user_id)
                .where(GroupUser.group_id.in_(from_group_ids))
                .distinct()
            )
            user_ids = set(user_ids_result.all())

            for user_id in user_ids:
                gu = await session.scalar(
                    sa.select(GroupUser)
                    .where(GroupUser.group_id == group_id)
                    .where(GroupUser.user_id == user_id)
                )
                if gu is None:
                    session.add(
                        GroupUser(group_id=group_id, user_id=user_id, admin=False)
                    )
                    session.add(
                        UserNotification(
                            user_id=user_id,
                            text=f"You've been added to group *{group.name}*",
                            url=f"/group/{group.id}",
                        )
                    )

            await session.commit()

        self.push_all(action="skyportal/REFRESH_GROUP", payload={"group_id": group_id})
        for user_id in user_ids:
            self.flow.push(user_id, "skyportal/FETCH_NOTIFICATIONS", {})
        return self.success()


class GroupStreamHandler(BaseHandler):
    @permissions(["Upload data"])
    async def post(self, group_id: int, *ignored_args):
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
        try:
            group_id = int(group_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid group_id: {group_id}")
        stream_id = data.get("stream_id")
        try:
            stream_id = int(stream_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid stream_id: {stream_id}")

        async with self.AsyncSession() as session:
            group = await session.scalar(
                Group.select(session.user_or_token, mode="update").where(
                    Group.id == group_id
                )
            )
            if group is None:
                return self.error(f"Group with ID {group_id} not accessible")
            if group.single_user_group:
                return self.error(
                    f"Cannot add users to group {group_id}. It is a single user group."
                )

            # Validate every group member has access to the stream via SQL
            # (avoid lazy `group.users`/`user.streams`).
            missing_count = await session.scalar(
                sa.select(sa.func.count())
                .select_from(GroupUser)
                .where(
                    GroupUser.group_id == group_id,
                    ~sa.exists().where(
                        sa.and_(
                            StreamUser.user_id == GroupUser.user_id,
                            StreamUser.stream_id == stream_id,
                        )
                    ),
                )
            )
            if missing_count and missing_count > 0:
                return self.error(
                    f"Not all users have stream access with ID {stream_id}",
                    status=403,
                )

            gs = await session.scalar(
                GroupStream.select(session.user_or_token).where(
                    GroupStream.group_id == group_id,
                    GroupStream.stream_id == stream_id,
                )
            )
            if gs is None:
                session.add(GroupStream(group_id=group_id, stream_id=stream_id))
            else:
                return self.error(
                    "Specified stream is already associated with this group."
                )
            await session.commit()

            self.push_all(
                action="skyportal/REFRESH_GROUP", payload={"group_id": group_id}
            )
            return self.success(data={"group_id": group_id, "stream_id": stream_id})

    @permissions(["Upload data"])
    async def delete(self, group_id: int, stream_id: int):
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
        try:
            group_id = int(group_id)
            stream_id = int(stream_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid group_id/stream_id: {group_id}/{stream_id}")

        async with self.AsyncSession() as session:
            # FIXME: GroupStream.delete excludes streams still operated on by a
            # group filter, but the async verify path doesn't enforce that
            # CustomUserAccessControl predicate yet (out-of-scope columns in
            # baselayer select_accessible_rows). Enforce explicitly until the
            # baselayer fix lands.
            actively_filtered = await session.scalar(
                Filter.select(session.user_or_token)
                .where(Filter.group_id == group_id)
                .where(Filter.stream_id == stream_id)
            )
            if actively_filtered is not None:
                return self.error(f"No stream IDs with ID {stream_id} accessible")

            groupstreams_result = await session.scalars(
                GroupStream.select(session.user_or_token, mode="delete")
                .where(GroupStream.group_id == group_id)
                .where(GroupStream.stream_id == stream_id)
            )
            groupstreams = groupstreams_result.all()
            if len(groupstreams) == 0:
                return self.error(f"No stream IDs with ID {stream_id} accessible")
            for gs in groupstreams:
                await session.delete(gs)

            await session.commit()
            self.push_all(
                action="skyportal/REFRESH_GROUP", payload={"group_id": group_id}
            )
            return self.success()


class ObjGroupsHandler(BaseHandler):
    @auth_or_token
    async def get(self, obj_id: str):
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

        async with self.AsyncSession() as session:
            s = await session.scalar(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            )
            if s is None:
                return self.error("Source not found", status=404)

            source_info = s.to_dict()
            query = (
                Group.select(session.user_or_token)
                .join(Source)
                .where(Source.obj_id == source_info["id"])
                .where(or_(Source.requested.is_(True), Source.active.is_(True)))
            )
            result = await session.scalars(query)
            groups = [g.to_dict() for g in result.unique().all()]
            return self.success(data=groups)
