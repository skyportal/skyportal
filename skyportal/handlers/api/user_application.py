import html
import uuid
from typing import ClassVar, Literal

import sqlalchemy as sa
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from baselayer.log import make_log

from ...models import (
    DBSession,
    Group,
    GroupStream,
    GroupUser,
    Invitation,
    Role,
    RoleACL,
    Stream,
    User,
    UserACL,
    UserApplication,
    UserNotification,
    UserRole,
)
from ...utils.app import get_app_base_url
from ...utils.email import send_email
from ...utils.naive_datetime import utcnow_naive
from ...utils.user_applications import (
    ADMIN_ACL,
    deciding_acls,
    may_decide,
    user_applications_enabled,
)
from ..base import BaseHandler

_, cfg = load_env()

log = make_log("user_applications")

# Generic on purpose: the submitter is unauthenticated, so the response must not
# say whether an address is already an account or an open application.
SUBMITTED_MESSAGE = (
    "Your application has been received. You will hear from us by email once "
    "an existing user has reviewed it."
)

DISABLED_MESSAGE = "Account applications are not enabled in this deployment."


def notify_deciders(session, application, endorser):
    """Tell whoever may act on the application it is waiting, and return their IDs.

    The named endorser only counts when they may decide; under the default
    admins-only mode they cannot, so it goes to the administrators instead.
    """
    if endorser is not None and may_decide(endorser):
        recipients = [endorser]
        notification = "has asked you to endorse their application for an account"
        email = "has applied for an account and named you as their endorser."
    else:
        holds_admin_acl = sa.or_(
            sa.select(UserACL.user_id)
            .where(UserACL.user_id == User.id, UserACL.acl_id == ADMIN_ACL)
            .exists(),
            sa.select(UserRole.user_id)
            .join(RoleACL, RoleACL.role_id == UserRole.role_id)
            .where(UserRole.user_id == User.id, RoleACL.acl_id == ADMIN_ACL)
            .exists(),
        )
        recipients = session.scalars(sa.select(User).where(holds_admin_acl)).all()
        notification = "has applied for an account"
        email = "has applied for an account."
    if not recipients:
        return []

    url = "/user_applications"
    for recipient in recipients:
        session.add(
            UserNotification(
                user_id=recipient.id,
                text=(
                    f"*{application.first_name} {application.last_name}* {notification}"
                ),
                notification_type="user_application",
                url=url,
            )
        )
    recipient_ids = [recipient.id for recipient in recipients]
    if cfg.get("user_applications.disable_emailing", False):
        return recipient_ids

    addresses = [r.contact_email for r in recipients if r.contact_email]
    if addresses:
        # The applicant is unauthenticated, so their words never reach the email as markup.
        applicant = html.escape(
            f"{application.first_name} {application.last_name} "
            f"({application.contact_email})"
        )
        try:
            send_email(
                recipients=addresses,
                subject=cfg["user_applications.email_subject"],
                body=(
                    f"{applicant} {email}<br /><br />"
                    f'Review the application <a href="{get_app_base_url()}{url}">here</a>.'
                ),
            )
        except Exception as e:
            # The application is recorded either way; the in-app notification stands.
            log(f"Failed to email {', '.join(addresses)}: {e}")
    return recipient_ids


class UserApplicationPostBody(BaseModel):
    """Request body for applying for an account."""

    model_config = ConfigDict(extra="forbid")

    # Lengths are capped: anyone can post here.
    firstName: str = Field(max_length=100, description="Applicant's first name.")
    lastName: str = Field(max_length=100, description="Applicant's last name.")
    email: str = Field(
        max_length=255,
        description="Address the invitation is sent to once the application is endorsed.",
    )
    affiliation: str | None = Field(
        default=None,
        max_length=255,
        description="Applicant's institution or affiliation.",
    )
    statement: str | None = Field(
        default=None, max_length=2000, description="Why the applicant wants access."
    )
    endorserEmail: str | None = Field(
        default=None,
        max_length=255,
        description="Address of an existing user the applicant asks to endorse them.",
    )


class UserApplicationGetQuery(BaseModel):
    """Query parameters for listing account applications."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset()

    status: Literal["pending", "endorsed", "declined"] | None = Field(
        default=None, description="Only return applications with this status."
    )
    mine: bool = Field(
        default=False,
        description="Only return applications naming the requesting user as endorser.",
    )
    numPerPage: int = Field(
        default=25, description="Number of applications per paginated request."
    )
    pageNumber: int = Field(default=1, description="Page number for paginated results.")


class UserApplicationPatchBody(BaseModel):
    """Request body for endorsing or declining an account application."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["endorsed", "declined"] = Field(
        description="One of either 'endorsed' or 'declined'."
    )
    groupIDs: list[int] | None = Field(
        default=None,
        description="IDs of groups to add the applicant to. The endorser must "
        "belong to each of them. Defaults to none, which still lands the "
        "applicant in the sitewide public group.",
    )
    role: Literal["Full user", "View only"] = Field(
        default="Full user",
        description="The role the new user will have in the system.",
    )
    declineReason: str | None = Field(
        default=None, description="Why the application was declined."
    )


class UserApplicationHandler(BaseHandler):
    # Unauthenticated: prospective users have no account to accept terms with.
    terms_of_service_exempt = ("POST",)

    def deny_non_decider(self):
        """Write an error and return True when the caller may not act on
        applications.

        Who that is depends on `user_applications.peer_endorsement`, so it
        cannot be a `@permissions` decorator.
        """
        if not user_applications_enabled():
            self.error(DISABLED_MESSAGE)
            return True
        if not may_decide(self.current_user):
            self.error(
                "Insufficient permissions: acting on account applications "
                f"requires one of {', '.join(deciding_acls())}.",
                status=403,
            )
            return True
        return False

    def post(self, *, body: UserApplicationPostBody = None):
        """
        ---
        summary: Apply for an account
        description: |
          Submit an application for an account, to be endorsed by an existing
          user. Open to unauthenticated callers.
        tags:
          - user_applications
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
        if not user_applications_enabled():
            return self.error(DISABLED_MESSAGE)
        body = self.parse_body(UserApplicationPostBody)

        contact_email = body.email.strip()
        endorser_email = (body.endorserEmail or "").strip() or None
        first_name = body.firstName.strip()
        last_name = body.lastName.strip()
        if "@" not in contact_email:
            return self.error("`email` must be an email address.")
        if not (first_name and last_name):
            return self.error("`firstName` and `lastName` are required.")

        with DBSession() as session:
            # One open application per address, so resubmitting does not flood
            # the queue. Reported as success either way (see SUBMITTED_MESSAGE).
            existing = session.scalar(
                sa.select(UserApplication).where(
                    UserApplication.contact_email == contact_email,
                    UserApplication.status == "pending",
                )
            )
            if existing is not None:
                return self.success(data={"message": SUBMITTED_MESSAGE})

            endorser = None
            if endorser_email is not None:
                endorser = session.scalar(
                    sa.select(User).where(User.contact_email == endorser_email)
                )

            application = UserApplication(
                first_name=first_name,
                last_name=last_name,
                contact_email=contact_email,
                affiliation=(body.affiliation or "").strip() or None,
                statement=(body.statement or "").strip() or None,
                endorser_email=endorser_email,
                endorser_id=endorser.id if endorser is not None else None,
                status="pending",
            )
            session.add(application)
            session.flush()
            notified = notify_deciders(session, application, endorser)
            session.commit()

            for user_id in notified:
                self.flow.push(user_id, "skyportal/FETCH_NOTIFICATIONS", {})
            return self.success(data={"message": SUBMITTED_MESSAGE})

    @auth_or_token
    async def get(
        self,
        application_id: int | None = None,
        *,
        query: UserApplicationGetQuery = None,
    ):
        """
        ---
        single:
          summary: Get an account application
          description: Retrieve an account application
          tags:
            - user_applications
          responses:
            200:
              content:
                application/json:
                  schema: Success
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          summary: Get account applications
          description: Retrieve account applications awaiting endorsement
          tags:
            - user_applications
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
        if self.deny_non_decider():
            return
        query = self.parse_query(UserApplicationGetQuery)

        async with self.AsyncSession() as session:
            stmt = UserApplication.select(session.user_or_token).options(
                selectinload(UserApplication.endorser),
                selectinload(UserApplication.endorsed_by),
            )
            if application_id is not None:
                application = await session.scalar(
                    stmt.where(UserApplication.id == application_id)
                )
                if application is None:
                    return self.error(
                        f"Cannot find application with ID {application_id}"
                    )
                return self.success(data=self.serialize(application))

            if query.status is not None:
                stmt = stmt.where(UserApplication.status == query.status)
            if query.mine:
                stmt = stmt.where(
                    UserApplication.endorser_id == self.associated_user_object.id
                )

            total_matches = await session.scalar(
                sa.select(func.count()).select_from(stmt)
            )
            stmt = (
                stmt.order_by(UserApplication.created_at.desc())
                .limit(query.numPerPage)
                .offset((query.pageNumber - 1) * query.numPerPage)
            )
            result = await session.scalars(stmt)
            applications = result.unique().all()
            return self.success(
                data={
                    "applications": [self.serialize(a) for a in applications],
                    "totalMatches": int(total_matches),
                }
            )

    @staticmethod
    def serialize(application):
        data = application.to_dict()
        for name in ("endorser", "endorsed_by"):
            user = getattr(application, name)
            data[name] = (
                None
                if user is None
                else {
                    "id": user.id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                }
            )
        return data

    @auth_or_token
    async def patch(
        self, application_id: int, *, body: UserApplicationPatchBody = None
    ):
        """
        ---
        summary: Endorse or decline an account application
        description: |
          Endorsing issues the invitation the applicant signs up with, and emails
          it to them. Groups are limited to those the endorser belongs to.
        tags:
          - user_applications
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
        if self.deny_non_decider():
            return
        body = self.parse_body(UserApplicationPatchBody)

        async with self.AsyncSession() as session:
            application = await session.scalar(
                UserApplication.select(session.user_or_token, mode="update").where(
                    UserApplication.id == application_id
                )
            )
            if application is None:
                return self.error(f"Cannot find application with ID {application_id}")
            # An endorsed application has already had its invitation emailed.
            if application.status == "endorsed":
                return self.error("This application has already been endorsed.")

            endorser = await session.scalar(
                User.select(session.user_or_token).where(
                    User.id == self.associated_user_object.id
                )
            )

            if body.status == "declined":
                application.status = "declined"
                application.endorsed_by_id = endorser.id
                application.decided_at = utcnow_naive()
                application.decline_reason = body.declineReason
                await session.commit()
                return self.success()

            group_ids = body.groupIDs or []
            groups, streams = [], []
            if group_ids:
                # Endorsers vouch into their own groups only; anything else
                # would let a Full user grant access they do not have.
                result = await session.scalars(
                    Group.select(self.current_user)
                    .join(GroupUser, GroupUser.group_id == Group.id)
                    .where(Group.id.in_(group_ids), GroupUser.user_id == endorser.id)
                )
                groups = result.unique().all()
                missing = set(group_ids).difference({g.id for g in groups})
                if missing:
                    return self.error(
                        "You may only endorse users into groups you belong to; "
                        f"not a member of group(s): {missing}"
                    )

                # Onboarding requires every group's streams to be on the
                # invitation, so they come from the groups rather than the caller.
                result = await session.scalars(
                    Stream.select(self.current_user)
                    .join(GroupStream)
                    .where(GroupStream.group_id.in_(group_ids))
                )
                streams = result.unique().all()

            role = await session.scalar(
                Role.select(self.current_user).where(Role.id == body.role)
            )

            invitation = Invitation(
                token=str(uuid.uuid4()),
                groups=groups,
                admin_for_groups=[False] * len(groups),
                can_save_to_groups=[True] * len(groups),
                can_share_photometry_for_groups=[False] * len(groups),
                streams=streams,
                user_email=application.contact_email,
                role=role,
                invited_by=endorser,
            )
            session.add(invitation)
            await session.flush()

            application.status = "endorsed"
            application.endorsed_by_id = endorser.id
            application.decided_at = utcnow_naive()
            application.invitation_id = invitation.id
            await session.commit()
            return self.success(data={"invitation_id": invitation.id})

    @auth_or_token
    async def delete(self, application_id: int):
        """
        ---
        summary: Delete an account application
        description: Delete an account application
        tags:
          - user_applications
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
        if self.deny_non_decider():
            return
        async with self.AsyncSession() as session:
            application = await session.scalar(
                UserApplication.select(session.user_or_token, mode="delete").where(
                    UserApplication.id == application_id
                )
            )
            if application is None:
                return self.error(f"Cannot find application with ID {application_id}")
            await session.delete(application)
            await session.commit()
            return self.success()
