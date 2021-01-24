from baselayer.app.access import auth_or_token
from ...base import BaseHandler
from ....models import DBSession, UserNotification


class NotificationHandler(BaseHandler):
    @auth_or_token
    def get(self, notification_id=None):
        """Fetch notification(s)"""
        if notification_id is not None:
            notification = UserNotification.query.get(notification_id)
            if notification is None:
                return self.error("Invalid notification_id")
            if (
                notification.user_id != self.associated_user_object.id
                and not self.current_user.is_system_admin
            ):
                return self.error("Insufficient permissions")
            return self.success(data=notification)
        notifications = (
            UserNotification.query.filter(
                UserNotification.user_id == self.associated_user_object.id
            )
            .order_by(UserNotification.created_at.desc())
            .all()
        )
        return self.success(data=notifications)

    def patch(self, notification_id):
        """Update a notification"""
        if notification_id is None:
            return self.error("Missing notification ID")
        data = self.get_json()
        data["id"] = notification_id
        schema = UserNotification.__schema__()
        schema.load(data, partial=True)
        DBSession().commit()
        return self.success(action="skyportal/FETCH_NOTIFICATIONS")

    def delete(self, notification_id):
        """Delete a notification"""
        if notification_id is None:
            return self.error("Missing required notification_id")
        notification = UserNotification.query.get(notification_id)
        if notification is None:
            return self.error("Invalid notification_id")
        if (
            notification.user_id != self.associated_user_object.id
            and not self.current_user.is_system_admin
        ):
            return self.error("Insufficient permissions")
        DBSession().delete(notification)
        DBSession().commit()
        return self.success(action="skyportal/FETCH_NOTIFICATIONS")


class BulkNotificationHandler(BaseHandler):
    """Handler for operating on all of requesting user's notifications, e.g.
    deleting all notifications or marking all notifications as read."""

    def patch(self):
        """Update all notifications associated with requesting user."""
        data = self.get_json()
        for notification in self.associated_user_object.notifications:
            for key in data:
                setattr(notification, key, data[key])
        DBSession().commit()
        return self.success(action="skyportal/FETCH_NOTIFICATIONS")

    def delete(self):
        """Delete all notifications associated with requesting user"""
        DBSession().query(UserNotification).filter(
            UserNotification.user_id == self.associated_user_object.id
        ).delete()
        DBSession().commit()
        return self.success(action="skyportal/FETCH_NOTIFICATIONS")
