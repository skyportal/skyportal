from jsonschema.exceptions import ValidationError

from baselayer.app.access import auth_or_token

from ....models import UserNotification
from ...base import BaseHandler


class NotificationHandler(BaseHandler):
    @auth_or_token
    def get(self, notification_id=None):
        """Fetch notification(s)"""

        with self.Session() as session:
            if notification_id is not None:
                notification = session.scalars(
                    UserNotification.select(session.user_or_token).where(
                        UserNotification == notification_id
                    )
                ).first()
                if notification is None:
                    return self.error(
                        f"Cannot find UserNotification with ID: {notification_id}"
                    )
                return self.success(data=notification)
            notifications = session.scalars(
                UserNotification.select(session.user_or_token)
                .where(UserNotification.user_id == self.associated_user_object.id)
                .order_by(UserNotification.created_at.desc())
            ).all()
            return self.success(data=notifications)

    @auth_or_token
    def patch(self, notification_id):
        """Update a notification"""

        data = self.get_json()
        data["id"] = notification_id

        with self.Session() as session:
            notification = session.scalars(
                UserNotification.select(session.user_or_token, mode="update").where(
                    UserNotification.id == notification_id
                )
            ).first()
            if notification is None:
                return self.error(
                    f"Cannot find UserNotification with ID: {notification_id}"
                )
            schema = UserNotification.__schema__()
            try:
                schema.load(data, partial=True)
            except ValidationError as e:
                return self.error(
                    f"Invalid/missing parameters: {e.normalized_messages()}"
                )

            for k in data:
                setattr(notification, k, data[k])
            session.commit()

            return self.success(action="skyportal/FETCH_NOTIFICATIONS")

    @auth_or_token
    def delete(self, notification_id):
        """Delete a notification"""
        if notification_id is None:
            return self.error("Missing required notification_id")

        with self.Session() as session:
            notification = session.scalars(
                UserNotification.select(session.user_or_token, mode="delete").where(
                    UserNotification.id == notification_id
                )
            ).first()
            if notification is None:
                return self.error(
                    f"Cannot find UserNotification with ID: {notification_id}"
                )

            session.delete(notification)
            session.commit()
            return self.success(action="skyportal/FETCH_NOTIFICATIONS")


class BulkNotificationHandler(BaseHandler):
    """Handler for operating on all of requesting user's notifications, e.g.
    deleting all notifications or marking all notifications as read."""

    @auth_or_token
    def patch(self):
        """Update all notifications associated with requesting user."""
        data = self.get_json()
        with self.Session() as session:
            notifications = session.scalars(
                UserNotification.select(session.user_or_token, mode="update").where(
                    UserNotification.user_id == self.associated_user_object.id
                )
            ).all()
            for notification in notifications:
                for key in data:
                    setattr(notification, key, data[key])
            session.commit()
            return self.success(action="skyportal/FETCH_NOTIFICATIONS")

    @auth_or_token
    def delete(self):
        """Delete all notifications associated with requesting user"""
        with self.Session() as session:
            notifications = session.scalars(
                UserNotification.select(session.user_or_token, mode="delete").where(
                    UserNotification.user_id == self.associated_user_object.id
                )
            ).all()

            for notification in notifications:
                session.delete(notification)
            session.commit()
            return self.success(action="skyportal/FETCH_NOTIFICATIONS")
