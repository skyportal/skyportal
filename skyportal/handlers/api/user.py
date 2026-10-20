from datetime import datetime

import arrow
import phonenumbers
import sqlalchemy as sa
from email_validator import EmailNotValidError, validate_email
from phonenumbers.phonenumberutil import NumberParseException
from skyportal_py_models.users import (
    UserGetQuery,
    UserPatchBody,
    UserPostBody,
    UserPostResponse,
)
from slugify import slugify
from sqlalchemy import func
from sqlalchemy.orm import load_only, selectinload

from baselayer.app.access import auth_or_token, permissions
from baselayer.app.env import load_env
from baselayer.log import make_log
from skyportal.model_util import all_acl_ids, role_acls

from ...models import (
    ACL,
    Annotation,
    Classification,
    Comment,
    FollowupRequest,
    Group,
    GroupUser,
    Photometry,
    Role,
    Source,
    Spectrum,
    Stream,
    StreamUser,
    Thumbnail,
    User,
    UserACL,
    UserRole,
)
from ..base import BaseHandler
from .internal.source_views import t_index
from .photometry import get_bandpasses_to_colors
from .roles import includes_admin_role

log = make_log("api/user")
env, cfg = load_env()


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


class UserHandler(BaseHandler):
    def can_manage_users(self):
        # System admin satisfies any ACL, as it does on the write side.
        granted = self.current_user.permissions
        return "Manage users" in granted or "System admin" in granted

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
                                "gravatar_url": user.gravatar_url,
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
            if not self.current_user.is_system_admin and await includes_admin_role(
                session, role_ids
            ):
                return self.error("Only system admins can grant administrator roles.")
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

            if body.username is not None and body.username != user.username:
                user.username = body.username
                # Group names are unique, so a stale single-user group name
                # would block creating a new account with the old username.
                single_user_group_id = await session.scalar(
                    sa.select(Group.id)
                    .join(GroupUser, GroupUser.group_id == Group.id)
                    .where(
                        Group.single_user_group.is_(True),
                        GroupUser.user_id == user.id,
                    )
                )
                if single_user_group_id is not None:
                    group_name = slugify(body.username)
                    clashing_group_id = await session.scalar(
                        sa.select(Group.id).where(
                            Group.name == group_name,
                            Group.id != single_user_group_id,
                        )
                    )
                    if clashing_group_id is not None:
                        return self.error(
                            f"A group named {group_name} already exists. "
                            "Please choose another username."
                        )
                    await session.execute(
                        sa.update(Group)
                        .where(Group.id == single_user_group_id)
                        .values(name=group_name)
                    )
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


ACTIVITY_PAGE = 25
ACTIVITY_PAGE_MAX = 100
# The feed merges offset + limit rows of every kind in Python, so depth is capped.
ACTIVITY_OFFSET_MAX = 5000
ACTIVITY_PHOTOMETRY_POINTS = 200


def _comment_detail(row):
    text = (row.text or "").strip().replace("\n", " ")
    return text[:140] + ("..." if len(text) > 140 else "")


def _classification_detail(row):
    if row.probability is None:
        return row.classification
    return f"{row.classification} (p={row.probability:g})"


# What a profile shows, the column each kind of contribution is signed with,
# and the one line it is worth saying about one. Every read runs through the
# model's own policy, so a viewer sees the part of someone's work they could
# have found for themselves.
ACTIVITY = {
    "sources_saved": (Source, "saved_by_id", lambda row: None),
    "comments": (Comment, "author_id", _comment_detail),
    "classifications": (Classification, "author_id", _classification_detail),
    "annotations": (Annotation, "author_id", lambda row: row.origin),
    "spectra": (Spectrum, "owner_id", lambda row: None),
    "followup_requests": (FollowupRequest, "requester_id", lambda row: row.status),
}


# A spectrum carries its wavelengths, fluxes and errors, which a feed line
# never reads; the news feed loads its metadata only for the same reason.
ACTIVITY_LOADERS = {
    Spectrum: [
        load_only(
            Spectrum.obj_id,
            Spectrum.created_at,
            Spectrum.owner_id,
        )
    ],
}


def _mine(model, column, user_id, viewer):
    stmt = model.select(viewer, columns=[model.id]).where(
        getattr(model, column) == user_id
    )
    if model is Comment:
        # Channel comments are conversation rather than a record of work, and
        # the news feed leaves them out on the same grounds.
        stmt = stmt.where(Comment.channel.is_(None))
    return model.id.in_(stmt)


def shared_activity(user):
    preferences = (user.preferences or {}).get("publicProfile") or {}
    return [kind for kind in ACTIVITY if preferences.get(f"activity_{kind}", True)]


async def activity_counts(session, user_id, viewer, kinds):
    """How much of `user_id`'s work `viewer` can see, by kind."""
    counts = {}
    for name, (model, column, _detail) in ACTIVITY.items():
        if name not in kinds:
            counts[name] = 0
            continue
        # A source saved to several groups is one source, and one row per
        # group; counting the object says what a reader means by "saved".
        identity = Source.obj_id if model is Source else model.id
        counts[name] = await session.scalar(
            sa.select(func.count(func.distinct(identity))).where(
                _mine(model, column, user_id, viewer)
            )
        )
    return counts


async def activity_feed(session, user_id, viewer, kinds, offset=0, limit=ACTIVITY_PAGE):
    """`user_id`'s contributions newest first, the page starting at `offset`.

    Each kind is read separately and merged here: six small reads on indexed
    attribution columns beat a union of six access-controlled queries.

    Paged by offset rather than by a timestamp cursor because a bulk save
    stamps many rows the same instant, and a cursor of "older than the last
    one" would step over the rest of them.
    """
    wanted = offset + limit
    items = []
    for name, (model, column, detail) in ACTIVITY.items():
        if name not in kinds:
            continue
        mine = _mine(model, column, user_id, viewer)
        if model is Source:
            created_at = func.min(Source.created_at).label("created_at")
            groups = func.json_agg(
                func.json_build_object("id", Group.id, "name", Group.name)
            ).label("groups")
            stmt = (
                sa.select(Source.obj_id, created_at, groups)
                .join(Group, Group.id == Source.group_id)
                .where(mine)
                .group_by(Source.obj_id)
                .order_by(created_at.desc(), Source.obj_id.desc())
            )
        else:
            stmt = (
                sa.select(model)
                .options(*ACTIVITY_LOADERS.get(model, []))
                .where(mine)
                .order_by(model.created_at.desc(), model.id.desc())
            )
        # One past the page, so a page filled by a single kind can still
        # tell that the kind has more behind it.
        stmt = stmt.limit(wanted + 1)
        result = await session.execute(stmt)
        rows = result.all() if model is Source else result.scalars().all()
        for row in rows:
            item = {
                "kind": name,
                "created_at": row.created_at,
                "obj_id": getattr(row, "obj_id", None),
                "detail": detail(row),
            }
            if model is Source:
                item["groups"] = sorted(row.groups, key=lambda group: group["name"])
            items.append(item)
    items.sort(key=lambda item: item["created_at"], reverse=True)
    return items[offset:wanted], len(items) > wanted


async def activity_objs(session, viewer, obj_ids):
    objs = {obj_id: {"thumbnails": [], "photometry": []} for obj_id in obj_ids}
    if not objs:
        return objs, {}

    thumbnails = await session.scalars(
        Thumbnail.select(viewer).where(Thumbnail.obj_id.in_(objs))
    )
    for t in sorted(thumbnails.unique().all(), key=lambda t: t_index(t.type)):
        objs[t.obj_id]["thumbnails"].append(
            {
                "type": t.type,
                "public_url": t.public_url,
                "is_grayscale": t.is_grayscale,
            }
        )

    readable = Photometry.select(viewer, columns=[Photometry.id]).where(
        Photometry.obj_id.in_(objs)
    )
    points = await session.execute(
        sa.select(Photometry.obj_id, Photometry.mjd, Photometry.mag, Photometry.filter)
        .where(
            Photometry.id.in_(readable),
            Photometry.snr >= cfg["misc.photometry_detection_threshold_nsigma"],
        )
        .order_by(Photometry.mjd)
    )
    for obj_id, mjd, mag, band in points.all():
        objs[obj_id]["photometry"].append([mjd, round(mag, 3), band])

    filters = set()
    for obj in objs.values():
        photometry = obj["photometry"]
        if len(photometry) > ACTIVITY_PHOTOMETRY_POINTS:
            step = len(photometry) / ACTIVITY_PHOTOMETRY_POINTS
            obj["photometry"] = [
                photometry[int(i * step)] for i in range(ACTIVITY_PHOTOMETRY_POINTS)
            ]
        filters.update(point[2] for point in obj["photometry"])
    return objs, get_bandpasses_to_colors(filters, "hex")


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


class UserActivityHandler(BaseHandler):
    @auth_or_token
    async def get(self, user_id: int):
        """
        ---
        summary: Get a user's contributions
        description: >
            The sources, comments, classifications, annotations, spectra and
            follow-up requests this user has to their name that the requester
            is allowed to see, newest first, with the totals by kind on the
            first page and the cutouts and detections of the sources on the
            page. Kinds the user hid from their public profile are left out
            for everyone else.
        tags:
          - users
        parameters:
          - in: path
            name: user_id
            required: true
            schema:
              type: integer
          - in: query
            name: limit
            schema:
              type: integer
            description: Items per page, capped at 100.
          - in: query
            name: offset
            schema:
              type: integer
            description: How many items to skip, for paging further back, at most 5000.
          - in: query
            name: kind
            schema:
              type: string
            description: Only list this kind of contribution.
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

            try:
                limit = min(
                    max(int(self.get_query_argument("limit", ACTIVITY_PAGE)), 1),
                    ACTIVITY_PAGE_MAX,
                )
                offset = max(int(self.get_query_argument("offset", 0)), 0)
            except ValueError:
                return self.error("limit and offset must be numbers.")
            if offset > ACTIVITY_OFFSET_MAX:
                return self.error(f"offset must be at most {ACTIVITY_OFFSET_MAX}.")
            kind = self.get_query_argument("kind", None)
            if kind is not None and kind not in ACTIVITY:
                return self.error(f"kind must be one of {', '.join(ACTIVITY)}.")

            viewer = session.user_or_token
            shared = shared_activity(user)
            counted = (
                list(ACTIVITY) if self.associated_user_object.id == user.id else shared
            )
            kinds = shared if kind is None else [k for k in shared if k == kind]
            items, has_more = await activity_feed(
                session, user_id, viewer, kinds, offset=offset, limit=limit
            )
            objs, filter_colors = await activity_objs(
                session, viewer, {item["obj_id"] for item in items if item["obj_id"]}
            )
            return self.success(
                data={
                    "counts": await activity_counts(session, user_id, viewer, counted)
                    if offset == 0
                    else None,
                    "items": items,
                    # A next page past the offset cap would be refused
                    "has_more": has_more and offset + limit <= ACTIVITY_OFFSET_MAX,
                    "objs": objs,
                    "filter_colors": filter_colors,
                }
            )
