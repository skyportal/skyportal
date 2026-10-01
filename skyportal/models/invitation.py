__all__ = ["Invitation"]

import html

import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.dialects import postgresql as psql
from sqlalchemy.orm import relationship
from sqlalchemy_utils import EmailType

from baselayer.app.auth_backends import default_auth_backend
from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.app.models import AccessibleIfUserMatches, Base
from baselayer.log import make_log

from ..utils.app import get_app_base_url
from ..utils.email import send_email

_, cfg = load_env()

log = make_log("invitations")


class Invitation(Base):
    read = update = delete = AccessibleIfUserMatches("invited_by")

    token = sa.Column(sa.String(), nullable=False, unique=True)
    role_id = sa.Column(
        sa.ForeignKey("roles.id"),
        nullable=False,
    )
    role = relationship(
        "Role",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        uselist=False,
    )
    groups = relationship(
        "Group",
        secondary="group_invitations",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
    )
    streams = relationship(
        "Stream",
        secondary="stream_invitations",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
    )
    admin_for_groups = sa.Column(psql.ARRAY(sa.Boolean), nullable=False)
    can_save_to_groups = sa.Column(psql.ARRAY(sa.Boolean), nullable=False)
    can_share_photometry_for_groups = sa.Column(psql.ARRAY(sa.Boolean), nullable=False)
    user_email = sa.Column(EmailType(), nullable=True)
    invited_by = relationship(
        "User",
        secondary="user_invitations",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        uselist=False,
        overlaps="users",
    )
    used = sa.Column(sa.Boolean, nullable=False, default=False)
    user_expiration_date = sa.Column(sa.DateTime, nullable=True)


@event.listens_for(Invitation, "after_insert")
def send_user_invite_email(mapper, connection, target):
    app_base_url = get_app_base_url()
    link_location = (
        f"{app_base_url}/login/{default_auth_backend()}/?invite_token={target.token}"
    )
    if cfg.get("invitations.disable_emailing", False) is True:
        log(
            f"Invitation created with token {target.token}; invite link: {link_location}"
        )
        if target.invited_by:
            try:
                flow = Flow()
                flow.push(
                    target.invited_by.id,
                    "baselayer/SHOW_NOTIFICATION",
                    payload={
                        "note": f"Email sending is disabled, invitation email not sent.",
                        "type": "warning",
                    },
                )
            except Exception as e:
                log(f"Failed to send notification: {e}")
    else:
        send_email(
            recipients=[target.user_email],
            subject=cfg["invitations.email_subject"],
            body=invite_body(target, link_location),
        )


def invite_body(target, link_location):
    site = html.escape(cfg["app.title"])
    inviter = target.invited_by
    if inviter:
        who = html.escape(
            " ".join(p for p in (inviter.first_name, inviter.last_name) if p)
            or inviter.username
        )
        intro = f"{who} has invited you to join <b>{site}</b>."
    else:
        intro = f"You have been invited to join <b>{site}</b>."

    preamble = (cfg["invitations.email_body_preamble"] or "").strip()
    if preamble and not preamble.startswith("<"):
        preamble = f"<p>{preamble}</p>"

    return (
        f"<p>{intro}</p>"
        f"{preamble}"
        f'<p>To accept, open <a href="{link_location}">{link_location}</a></p>'
        f"<p>Signing in without opening that link will not work: it carries the "
        f"invitation itself.</p>"
        f"<p>The link is good for {cfg['invitations.days_until_expiry']} days.</p>"
        f"<p>If you were not expecting this, you can ignore the message; "
        f"nothing is created until the link is opened.</p>"
    )
