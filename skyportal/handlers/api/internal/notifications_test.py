import sqlalchemy as sa
from twilio.rest import Client as TwilioClient

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env

from ....email_utils import send_email
from ...base import BaseHandler

from ....models import User

env, cfg = load_env()

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
    def post(self):
        """
        ---
        description: Post user test notifications
        tags:
        - users
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  user_id:
                    type: integer
                    required: false
                    description: |
                      ID of user that you want to trigger a test notifcation for.
                      If not given, will default to the associated user object that is posting.
                  notification_type:
                    type: string
                    required: true
                    description: |
                      Type of notification to test. Should be email or SMS.
        responses:
          200:
            content:
              application/json:
                schema: SingleTaxonomy
          400:
            content:
              application/json:
                schema: Error
        """

        data = self.get_json()

        user_id = data.get('user_id', None)
        notification_type = data.get('notification_type', None)

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

        with self.Session() as session:
            user = session.scalar(sa.select(User).where(User.id == user_id))

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
