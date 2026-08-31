from datetime import datetime
from typing import ClassVar, Literal

import arrow
import phonenumbers
import sqlalchemy as sa
from email_validator import EmailNotValidError, validate_email
from phonenumbers.phonenumberutil import NumberParseException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from baselayer.app.access import auth_or_token, permissions
from baselayer.app.env import load_env
from baselayer.log import make_log
from skyportal.model_util import all_acl_ids, role_acls

from ...models import (
    ACL,
    Group,
    GroupUser,
    Role,
    Stream,
    StreamUser,
    User,
    UserACL,
    UserRole,
)
from ..base import BaseHandler

log = make_log("api/user")
env, cfg = load_env()


class UserPostBody(BaseModel):
    """Request body for adding a new user."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(description="Username of the new user")
    first_name: str | None = Field(default=None, description="User's first name")
    last_name: str | None = Field(default=None, description="User's last name")
    affiliations: list[str] | None = Field(
        default=None, description="User's list of affiliations"
    )
    contact_email: str | None = Field(
        default=None, description="User's contact email address"
    )
    contact_phone: str | None = Field(
        default=None, description="User's contact phone number"
    )
    oauth_uid: str | None = Field(default=None, description="User's OAuth UID")
    roles: list[str] = Field(
        default_factory=list,
        description="List of user roles. Defaults to `[Full user]`. Will be "
        "overridden by `groupIDsAndAdmin` on a per-group basis.",
    )
    groupIDsAndAdmin: list[tuple[int, bool]] = Field(
        default_factory=list,
        description="Array of 2-element arrays `[groupID, admin]` where `groupID` "
        "is the ID of a group that the new user will be added to and `admin` is "
        "a boolean indicating whether they will be an admin in that group, "
        "e.g. `[[group_id_1, true], [group_id_2, false]]`",
    )


class UserPostResponse(BaseModel):
    """ID of the newly added user."""

    id: int = Field(description="New user ID")


class UserPatchBody(BaseModel):
    """Request body for updating a user."""

    model_config = ConfigDict(extra="forbid")

    expirationDate: str | None = Field(
        default=None,
        description="Arrow-parseable date string (e.g. 2020-01-01). Set a "
        "user's expiration date, after which the user's account will be "
        "deactivated and will be unable to access the application. An explicit "
        "null or empty string clears the expiration date.",
    )
    username: str | None = Field(default=None, description="New username")
    first_name: str | None = Field(default=None, description="User's first name")
    last_name: str | None = Field(default=None, description="User's last name")
    contact_email: str | None = Field(
        default=None, description="User's contact email address"
    )


# Mirrored by PUBLIC_FIELDS in static/js/components/user/UserProfileInfo.tsx
PUBLIC_PROFILE_FIELDS = {
    "affiliations": True,
    "bio": True,
    "contact_email": False,
    "contact_phone": False,
    "roles": False,
    "groups": False,
}


def shared_profile_fields(user):
    """The public profile fields this user chose to share, defaults applied."""
    preferences = (user.preferences or {}).get("publicProfile") or {}
    return {
        field: bool(preferences.get(field, default))
        for field, default in PUBLIC_PROFILE_FIELDS.items()
    }


def public_user_info(user):
    """Everything a user shares with others: identity, plus their opt-in fields.

    Single source of truth for what the API discloses about someone else.
    """
    shared = shared_profile_fields(user)
    info = {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "gravatar_url": user.gravatar_url,
        "is_bot": user.is_bot,
        "created_at": user.created_at,
    }
    if shared["affiliations"]:
        info["affiliations"] = user.affiliations or []
    if shared["bio"]:
        info["bio"] = user.bio
    if shared["contact_email"]:
        info["contact_email"] = user.contact_email
    if shared["contact_phone"]:
        info["contact_phone"] = user.contact_phone.e164 if user.contact_phone else None
    if shared["roles"]:
        info["roles"] = sorted(role.id for role in user.roles)
    if shared["groups"]:
        info["groups"] = sorted(
            group.name for group in user.groups if not group.single_user_group
        )
    return info


def set_default_role(user, session):
    """Add the config's default role to a user. The caller commits."""
    default_role = cfg["user.default_role"]
    if isinstance(default_role, str) and default_role in role_acls:
        role = session.scalars(sa.select(Role).where(Role.id == default_role)).first()
        if role is None:
            raise Exception(
                f"Invalid default_role configuration value: {default_role} does not exist"
            )
        session.add(UserRole(user_id=user.id, role_id=role.id))


def set_default_acls(user, session):
    """Add the config's default ACLs to a user. The caller commits."""
    for acl_id in cfg["user.default_acls"]:
        if acl_id not in all_acl_ids:
            raise Exception(
                f"Invalid default_acl configuration value: {acl_id} does not exist"
            )
    for acl_id in cfg["user.default_acls"]:
        session.add(UserACL(user_id=user.id, acl_id=acl_id))


def set_default_group(user, session):
    """Add the config's default groups and their streams to a user. The caller commits."""
    default_groups = []
    if cfg["misc.public_group_name"] is not None:
        default_groups.append(cfg["misc.public_group_name"])
    default_groups.extend(cfg["user.default_groups"])
    default_groups = list(set(default_groups))
    for default_group_name in default_groups:
        group = session.scalars(
            sa.select(Group).where(Group.name == default_group_name)
        ).first()
        if group is None:
            raise Exception(
                f"Invalid default_group configuration value: {default_group_name} does not exist"
            )
        session.add(GroupUser(user_id=user.id, group_id=group.id, admin=False))
        for stream in group.streams:
            session.add(StreamUser(stream_id=stream.id, user_id=user.id))


# Async variants of the two helpers above that hit the DB; the sync versions
# stay for skyportal/onboarding.py, which runs in the sync social-auth pipeline.


async def set_default_role_async(user, session):
    """Async equivalent of `set_default_role`."""
    default_role = cfg["user.default_role"]
    if isinstance(default_role, str) and default_role in role_acls:
        role = await session.scalar(sa.select(Role).where(Role.id == default_role))
        if role is None:
            raise Exception(
                f"Invalid default_role configuration value: {default_role} does not exist"
            )
        session.add(UserRole(user_id=user.id, role_id=role.id))


async def set_default_group_async(user, session):
    """Async equivalent of `set_default_group`."""
    default_groups = []
    if cfg["misc.public_group_name"] is not None:
        default_groups.append(cfg["misc.public_group_name"])
    default_groups.extend(cfg["user.default_groups"])
    default_groups = list(set(default_groups))
    for default_group_name in default_groups:
        group = await session.scalar(
            sa.select(Group)
            .options(selectinload(Group.streams))
            .where(Group.name == default_group_name)
        )
        if group is None:
            raise Exception(
                f"Invalid default_group configuration value: {default_group_name} does not exist"
            )
        session.add(GroupUser(user_id=user.id, group_id=group.id, admin=False))
        for stream in group.streams:
            session.add(StreamUser(stream_id=stream.id, user_id=user.id))


async def add_user_and_setup_groups(
    session,
    username,
    first_name=None,
    last_name=None,
    affiliations=None,
    contact_phone=None,
    contact_email=None,
    role_ids=[],
    group_ids_and_admin=[],
    oauth_uid=None,
    expiration_date=None,
):
    """Create a user with its roles, groups and streams. The caller commits."""
    try:
        roles_result = await session.scalars(
            sa.select(Role).where(Role.id.in_(role_ids))
        )
        roles = roles_result.all()
        user = User(
            username=username.lower(),
            roles=roles,
            first_name=first_name,
            last_name=last_name,
            affiliations=affiliations,
            contact_phone=contact_phone,
            contact_email=contact_email,
            oauth_uid=oauth_uid,
            expiration_date=expiration_date,
        )
        session.add(user)
        await session.flush()

        if role_ids == []:
            await set_default_role_async(user, session)

        if group_ids_and_admin == []:
            await set_default_group_async(user, session)
        else:
            granted_stream_ids = set()
            group_with_streams = sa.select(Group).options(selectinload(Group.streams))

            def grant_streams(group):
                for stream in group.streams:
                    if stream.id not in granted_stream_ids:
                        session.add(StreamUser(stream_id=stream.id, user_id=user.id))
                        granted_stream_ids.add(stream.id)

            for group_id, admin in group_ids_and_admin:
                session.add(GroupUser(user_id=user.id, group_id=group_id, admin=admin))
                group = await session.scalar(
                    group_with_streams.where(Group.id == group_id)
                )
                if group is not None:
                    grant_streams(group)

            if cfg["misc.public_group_name"] is not None:
                public_group = await session.scalar(
                    group_with_streams.where(
                        Group.name == cfg["misc.public_group_name"]
                    )
                )
                if public_group is not None:
                    session.add(GroupUser(group_id=public_group.id, user_id=user.id))
                    grant_streams(public_group)

        set_default_acls(user, session)
        await session.flush()
    except Exception as e:
        await session.rollback()
        log(str(e))
        raise e
    return user.id


class UserGetQuery(BaseModel):
    """Query parameters for listing users."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset()

    numPerPage: int | None = Field(
        default=None,
        description="Number of users to return per paginated request. Defaults to all users.",
    )
    pageNumber: int = Field(
        default=1,
        description="Page number for paginated query results. Defaults to 1.",
    )
    firstName: str | None = Field(
        default=None,
        description="Get users whose first name contains this string.",
    )
    lastName: str | None = Field(
        default=None,
        description="Get users whose last name contains this string.",
    )
    username: str | None = Field(
        default=None,
        description="Get users whose username contains this string.",
    )
    email: str | None = Field(
        default=None,
        description="Get users whose email contains this string.",
    )
    role: str | None = Field(
        default=None,
        description="Get users with the role.",
    )
    acl: str | None = Field(
        default=None,
        description="Get users with this ACL.",
    )
    group: str | None = Field(
        default=None,
        description="Get users part of the group with name given by this parameter.",
    )
    stream: str | None = Field(
        default=None,
        description="Get users with access to the stream with name given by this parameter.",
    )
    slim: bool = Field(
        default=False,
        description=(
            "Return only what is needed to name a user (id, username, first "
            "and last name, is_bot). Callers that just label a comment, a "
            "redshift or an assignment do not need each user's groups, roles "
            "and ACLs, which are most of the response."
        ),
    )
    includeExpired: bool = Field(
        default=False,
        description="Include users with expired accounts in the results.",
    )
    sortBy: Literal["username", "createdAt"] = Field(
        default="username",
        description="Field to sort by. Options are 'username' (alphabetical, default) or 'createdAt' (creation date).",
    )
    sortOrder: Literal["asc", "desc"] = Field(
        default="asc",
        description="Sort order - 'asc' for ascending (default) or 'desc' for descending.",
    )


class UserHandler(BaseHandler):
    def can_manage_users(self):
        return "Manage users" in self.current_user.permissions

    def can_manage_user(self, user_id):
        """Whether the requester may see a user's record beyond its public profile."""
        return self.can_manage_users() or self.associated_user_object.id == user_id

    @auth_or_token
    async def get(self, user_id: int | None = None, *, query: UserGetQuery = None):
        """
        ---
        single:
          summary: Get a user
          description: >
            Retrieve a user. Without the Manage users ACL, only the user's own
            record is returned in full; other users are reduced to the profile
            they chose to share.
          tags:
            - users
          responses:
            200:
              content:
                application/json:
                  schema: SingleUser
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          summary: Get all users
          description: >
            Retrieve all users. Without the Manage users ACL, contact details
            not shared on a user's public profile are omitted.
          tags:
            - users
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
                              users:
                                type: array
                                items:
                                  $ref: '#/components/schemas/User'
                                description: List of users
                              totalMatches:
                                type: integer
                                description: The total number of users matching the query
            400:
              content:
                application/json:
                  schema: Error
        """
        query = self.parse_query(UserGetQuery)

        if user_id is not None:
            async with self.AsyncSession() as session:
                user = await session.scalar(
                    User.select(self.current_user).where(User.id == user_id)
                )
                if user is None:
                    return self.error(f"Cannot find user with ID {user_id}.")

                if not self.can_manage_user(user_id):
                    return self.success(data=public_user_info(user))

                user_info = user.to_dict()

                # return the phone number so it can be serialized
                if user_info.get("contact_phone"):
                    user_info["contact_phone"] = user_info["contact_phone"].e164

                user_info["permissions"] = sorted(user.permissions)
                user_info["roles"] = sorted(role.id for role in user.roles)
                user_info["acls"] = sorted(acl.id for acl in user.acls)

                return self.success(data=user_info)

        async with self.AsyncSession() as session:
            stmt = User.select(self.current_user).options(
                selectinload(User.groups),
                selectinload(User.streams),
            )

            if not query.includeExpired:
                stmt = stmt.where(
                    sa.or_(
                        User.expiration_date >= datetime.now(),
                        User.expiration_date.is_(None),
                    )
                )

            if query.firstName is not None:
                stmt = stmt.where(User.first_name.contains(query.firstName))
            if query.lastName is not None:
                stmt = stmt.where(User.last_name.contains(query.lastName))
            if query.username is not None:
                stmt = stmt.where(User.username.contains(query.username))
            if query.email is not None:
                # else a redacted contact_email stays guessable one substring at a time
                if not self.can_manage_users():
                    return self.error(
                        "Filtering users by email requires the Manage users ACL."
                    )
                stmt = stmt.where(User.contact_email.contains(query.email))
            if query.role is not None:
                stmt = stmt.join(UserRole).join(Role).where(Role.id == query.role)
            if query.acl is not None:
                stmt = stmt.join(UserACL).join(ACL).where(ACL.id == query.acl)
            if query.group is not None:
                stmt = stmt.join(GroupUser).join(Group).where(Group.name == query.group)
            if query.stream is not None:
                stmt = (
                    stmt.join(StreamUser)
                    .join(Stream)
                    .where(Stream.name == query.stream)
                )

            sort_field_map = {
                "username": User.username,
                "createdAt": User.created_at,
            }
            sort_field = sort_field_map[query.sortBy]

            if query.sortOrder == "desc":
                stmt = stmt.order_by(sort_field.desc())
            else:
                stmt = stmt.order_by(sort_field.asc())

            total_matches = await session.scalar(
                sa.select(func.count()).select_from(stmt)
            )

            if query.numPerPage is not None:
                stmt = stmt.limit(query.numPerPage).offset(
                    (query.pageNumber - 1) * query.numPerPage
                )
            return_values = []
            # accessible_groups' admin branch runs a sync Group.query.all(),
            # which cannot run here; non-admins reuse their selectin-loaded groups.
            if "System admin" in self.current_user.permissions:
                user_accessible_group_ids = set(
                    (
                        await session.scalars(
                            sa.select(Group.id).where(
                                Group.single_user_group.is_(False)
                            )
                        )
                    ).all()
                )
            else:
                user_accessible_group_ids = {
                    g.id for g in self.current_user.groups if not g.single_user_group
                }

            users_result = await session.scalars(stmt)
            if query.slim:
                return self.success(
                    data={
                        "users": [
                            {
                                "id": user.id,
                                "username": user.username,
                                "first_name": user.first_name,
                                "last_name": user.last_name,
                                "is_bot": user.is_bot,
                            }
                            for user in users_result.all()
                        ],
                        "totalMatches": int(total_matches),
                    }
                )

            for user in users_result.all():
                user_info = user.to_dict()
                user_info["permissions"] = sorted(user.permissions)
                user_info["roles"] = sorted(role.id for role in user.roles)
                user_info["acls"] = sorted(acl.id for acl in user.acls)
                if user.contact_phone:
                    user_info["contact_phone"] = user.contact_phone.e164
                user_info["contact_email"] = user.contact_email
                user_info["gravatar_url"] = user.gravatar_url
                if not self.can_manage_user(user.id):
                    shared = shared_profile_fields(user)
                    user_info.pop("oauth_uid", None)
                    for f in ("affiliations", "bio", "contact_email", "contact_phone"):
                        if not shared[f]:
                            user_info.pop(f, None)
                if self.current_user.is_system_admin:
                    user_info["groups"] = user.groups
                    user_info["streams"] = user.streams
                else:
                    user_info["groups"] = [
                        g for g in user.groups if g.id in user_accessible_group_ids
                    ]
                return_values.append(user_info)

            return self.success(
                data={"users": return_values, "totalMatches": int(total_matches)}
            )

    @permissions(["Manage users"])
    async def post(self, *, body: UserPostBody = None) -> UserPostResponse:
        """
        ---
        summary: Add a new user
        description: Add a new user
        tags:
          - users
        """
        body = self.parse_body(UserPostBody)
        role_ids = body.roles
        group_ids_and_admin = body.groupIDsAndAdmin

        phone = body.contact_phone
        if phone not in [None, ""]:
            try:
                if not phonenumbers.is_possible_number(phonenumbers.parse(phone, "US")):
                    return self.error("Phone number given is not valid")
            except NumberParseException:
                return self.error("Could not parse input as a phone number")
            contact_phone = phone
        else:
            contact_phone = None

        email = body.contact_email
        if email not in [None, ""]:
            try:
                emailinfo = validate_email(email, check_deliverability=False)
            except EmailNotValidError as e:
                return self.error(f"Email does not appear to be valid: {e}")
            contact_email = emailinfo.normalized
        else:
            contact_email = None

        async with self.AsyncSession() as session:
            try:
                user_id = await add_user_and_setup_groups(
                    session=session,
                    username=body.username,
                    first_name=body.first_name,
                    last_name=body.last_name,
                    affiliations=body.affiliations,
                    contact_phone=contact_phone,
                    contact_email=contact_email,
                    oauth_uid=body.oauth_uid,
                    role_ids=role_ids,
                    group_ids_and_admin=group_ids_and_admin,
                )
            except Exception as e:
                await session.rollback()
                return self.error(str(e))

            await session.commit()

        return self.success(data={"id": user_id})

    @permissions(["Manage users"])
    async def patch(self, user_id: int, *, body: UserPatchBody = None):
        """
        ---
        summary: Update a user
        description: Update a User record
        tags:
          - users
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        body = self.parse_body(UserPatchBody)

        if user_id is None:
            return self.error("User ID must be provided")

        async with self.AsyncSession() as session:
            user = await session.scalar(
                User.select(self.current_user, mode="update").where(User.id == user_id)
            )
            if user is None:
                return self.error(f"Cannot find user with ID {user_id}")

            if "expirationDate" in body.model_fields_set:
                expiration_date = body.expirationDate
                if expiration_date is not None and expiration_date != "":
                    try:
                        # .naive, not .datetime: the column is naive, so a
                        # tz-aware value gets shifted into the server's local
                        # zone and the account expires off the date that was set.
                        user.expiration_date = arrow.get(expiration_date.strip()).naive
                    except arrow.parser.ParserError:
                        return self.error("Unable to parse `expirationDate` parameter.")
                else:
                    user.expiration_date = None

            if body.username is not None:
                user.username = body.username
            if body.first_name is not None:
                user.first_name = body.first_name
            if body.last_name is not None:
                user.last_name = body.last_name
            if body.contact_email is not None:
                user.contact_email = body.contact_email

            await session.commit()
            self.push_all(action="skyportal/FETCH_USERS")
            self.push_all(action="skyportal/FETCH_USERS_MANAGEMENT")
            return self.success()

    @permissions(["Manage users"])
    async def delete(self, user_id: int | None = None):
        """
        ---
        summary: Delete a user
        description: Delete a user
        tags:
          - users
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
        if user_id is None:
            return self.error("User ID must be provided")
        async with self.AsyncSession() as session:
            user = await session.scalar(
                User.select(self.current_user, mode="delete").where(User.id == user_id)
            )
            if user is None:
                return self.error(f"Cannot find/delete user with ID {user_id}")
            await session.delete(user)
            await session.commit()

        return self.success()


class UserPublicProfileHandler(BaseHandler):
    @auth_or_token
    async def get(self, user_id: int):
        """
        ---
        summary: Get a user's public profile
        description: >
            Retrieve the profile a user shares with others: their name and
            avatar, plus the fields they chose to share in their settings.
        tags:
          - users
        parameters:
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
          400:
            content:
              application/json:
                schema: Error
        """
        async with self.AsyncSession() as session:
            user = await session.scalar(
                User.select(session.user_or_token).where(User.id == user_id)
            )
            if user is None:
                return self.error(f"Cannot find user with ID {user_id}.")

            return self.success(data=public_user_info(user))
