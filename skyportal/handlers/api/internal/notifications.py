from baselayer.app.access import auth_or_token
from ...base import BaseHandler
from ....models import DBSession, UserNotification


class NotificationHandler(BaseHandler):
    @auth_or_token
    def get(self, notification_id=None):
        """Fetch notification(s)"""
        if notification_id is not None:
            notification = UserNotification.get_if_accessible_by(
                notification_id, self.current_user, raise_if_none=True
            )
            return self.success(data=notification)
        notifications = (
            UserNotification.query_records_accessible_by(self.current_user)
            .filter(UserNotification.user_id == self.associated_user_object.id)
            .order_by(UserNotification.created_at.desc())
            .all()
        )
        self.verify_and_commit()
        return self.success(data=notifications)

    @auth_or_token
    def patch(self, notification_id):
        """Update a notification"""
        UserNotification.get_if_accessible_by(
            notification_id, self.current_user, mode="update", raise_if_none=True
        )
        data = self.get_json()
        data["id"] = notification_id
        schema = UserNotification.__schema__()
        schema.load(data, partial=True)
        self.verify_and_commit()
        return self.success(action="skyportal/FETCH_NOTIFICATIONS")

    @auth_or_token
    def delete(self, notification_id):
        """Delete a notification"""
        if notification_id is None:
            return self.error("Missing required notification_id")
        notification = UserNotification.get_if_accessible_by(
            notification_id, self.current_user, mode="delete", raise_if_none=True
        )
        DBSession().delete(notification)
        self.verify_and_commit()
        return self.success(action="skyportal/FETCH_NOTIFICATIONS")


class BulkNotificationHandler(BaseHandler):
    """Handler for operating on all of requesting user's notifications, e.g.
    deleting all notifications or marking all notifications as read."""

    @auth_or_token
    def patch(self):
        """Update all notifications associated with requesting user."""
        data = self.get_json()
        notifications = (
            UserNotification.query_records_accessible_by(self.current_user)
            .filter(UserNotification.user_id == self.associated_user_object.id)
            .all()
        )
        for notification in notifications:
            for key in data:
                setattr(notification, key, data[key])
        self.verify_and_commit()
        return self.success(action="skyportal/FETCH_NOTIFICATIONS")

    @auth_or_token
    def delete(self):
        """Delete all notifications associated with requesting user"""
        notifications = (
            UserNotification.query_records_accessible_by(
                self.current_user, mode="delete"
            )
            .filter(UserNotification.user_id == self.associated_user_object.id)
            .all()
        )
        for notification in notifications:
            DBSession().delete(notification)
        self.verify_and_commit()
        return self.success(action="skyportal/FETCH_NOTIFICATIONS")
