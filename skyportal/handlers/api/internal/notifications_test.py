import sqlalchemy as sa
from pydantic import BaseModel, ConfigDict, Field
from twilio.rest import Client as TwilioClient

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env

from ....email_utils import send_email
from ....models import User
from ...base import BaseHandler

env, cfg = load_env()


class NotificationTestPostBody(BaseModel):
    """Request body for sending a test notification."""

    model_config = ConfigDict(extra="forbid")

    notification_type: str | None = Field(
        default=None,
        description="Type of notification to test. Should be email or SMS.",
    )
    user_id: int | None = Field(
        default=None,
        description="ID of user that you want to trigger a test notification for. "
        "If not given, will default to the associated user object that is posting.",
    )


account_sid = cfg["twilio.sms_account_sid"]
auth_token = cfg["twilio.sms_auth_token"]
from_number = cfg["twilio.from_number"]
client = None
if account_sid and auth_token and from_number:
    client = TwilioClient(account_sid, auth_token)

email = False
if cfg.get("email_service") == "sendgrid" or cfg.get("email_service") == "smtp":
    email = True


class NotificationTestHandler(BaseHandler):
    @auth_or_token
    async def post(self, *, body: NotificationTestPostBody = None):
        """
        ---
        description: Post user test notifications
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

        body = self.parse_body(NotificationTestPostBody)

        user_id = body.user_id
        notification_type = body.notification_type

        if user_id is None:
            user_id = self.associated_user_object.id

        if (
            user_id != self.associated_user_object.id
            and not self.associated_user_object.is_admin
        ):
            return self.error(
                "Only admins can test notifications to other users' accounts"
            )

        if notification_type not in ["email", "SMS"]:
            return self.error("notification_type must be email or SMS")

        if notification_type == "email" and not email:
            return self.error("email not enabled in application")

        if notification_type == "SMS" and client is None:
            return self.error("SMS not enabled in application")

        async with self.AsyncSession() as session:
            user = await session.scalar(sa.select(User).where(User.id == user_id))

            try:
                if notification_type == "email":
                    send_email(
                        recipients=[user.contact_email],
                        subject=f"{cfg['app.title']} - Test Email",
                        body="This is just a test.",
                    )
                elif notification_type == "SMS":
                    client.messages.create(
                        body=f"{cfg['app.title']} - Test SMS",
                        from_=from_number,
                        to=user.contact_phone.e164,
                    )
            except Exception as e:
                return self.error(f"Failed to send notification: {str(e)}")

            return self.success()
