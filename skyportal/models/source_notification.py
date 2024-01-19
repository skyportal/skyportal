__all__ = ['SourceNotification']

import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy import event

from twilio.rest import Client as TwilioClient

from baselayer.app.models import (
    Base,
    DBSession,
    AccessibleIfRelatedRowsAreAccessible,
    AccessibleIfUserMatches,
)
from baselayer.app.env import load_env

from ..email_utils import send_email
from ..app_utils import get_app_base_url

from .obj import Obj
from .group import Group


_, cfg = load_env()


class SourceNotification(Base):
    create = read = AccessibleIfRelatedRowsAreAccessible(source='read')
    update = delete = AccessibleIfUserMatches('sent_by')

    groups = relationship(
        "Group",
        secondary="group_notifications",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
    )
    sent_by_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="The ID of the User who sent this notification.",
    )
    sent_by = relationship(
        "User",
        back_populates="source_notifications",
        foreign_keys=[sent_by_id],
        doc="The User who sent this notification.",
    )
    source_id = sa.Column(
        sa.ForeignKey("objs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the target Obj.",
    )
    source = relationship(
        'Obj', back_populates='obj_notifications', doc='The target Obj.'
    )

    additional_notes = sa.Column(sa.String(), nullable=True)
    level = sa.Column(sa.String(), nullable=False)


@event.listens_for(SourceNotification, 'after_insert')
def send_source_notification(mapper, connection, target):
    app_base_url = get_app_base_url()

    link_location = f'{app_base_url}/source/{target.source_id}'
    if target.sent_by.first_name is not None and target.sent_by.last_name is not None:
        sent_by_name = f'{target.sent_by.first_name} {target.sent_by.last_name}'
    else:
        sent_by_name = target.sent_by.username

    group_ids = map(lambda group: group.id, target.groups)
    groups = DBSession().query(Group).filter(Group.id.in_(group_ids)).all()

    target_users = set()
    for group in groups:
        # Use a set to get unique iterable of users
        target_users.update(group.users)

    source = DBSession().query(Obj).get(target.source_id)
    source_info = ""
    if source.ra is not None:
        source_info += f'RA={source.ra} '
    if source.dec is not None:
        source_info += f'Dec={source.dec}'
    source_info = source_info.strip()

    # Send SMS messages to opted-in users if desired
    if target.level == "hard":
        message_text = (
            f'{cfg["app.title"]}: {sent_by_name} would like to call your immediate'
            f' attention to a source at {link_location} ({source_info}).'
        )
        if target.additional_notes != "" and target.additional_notes is not None:
            message_text += f' Addtional notes: {target.additional_notes}'

        account_sid = cfg["twilio.sms_account_sid"]
        auth_token = cfg["twilio.sms_auth_token"]
        from_number = cfg["twilio.from_number"]
        client = TwilioClient(account_sid, auth_token)
        for user in target_users:
            # If user has a phone number registered and opted into SMS notifications
            if (
                user.contact_phone is not None
                and user.preferences is not None
                and "allowSMSAlerts" in user.preferences
                and user.preferences.get("allowSMSAlerts")
            ):
                client.messages.create(
                    body=message_text, from_=from_number, to=user.contact_phone.e164
                )

    # Send email notifications
    recipients = []
    for user in target_users:
        # If user has a contact email registered and opted into email notifications
        if (
            user.contact_email is not None
            and user.preferences is not None
            and "allowEmailAlerts" in user.preferences
            and user.preferences.get("allowEmailAlerts")
        ):
            recipients.append(user.contact_email)

    descriptor = "immediate" if target.level == "hard" else ""
    html_content = (
        f'{sent_by_name} would like to call your {descriptor} attention to'
        f' <a href="{link_location}">{target.source_id}</a> ({source_info})'
    )
    if target.additional_notes != "" and target.additional_notes is not None:
        html_content += f'<br /><br />Additional notes: {target.additional_notes}'

    if len(recipients) > 0:
        send_email(
            recipients=recipients,
            subject=f'{cfg["app.title"]}: Source Alert',
            body=html_content,
        )
