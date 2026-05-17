from jsonschema.exceptions import ValidationError

from baselayer.app.access import auth_or_token

from ....models import UserNotification
from ...base import BaseHandler


class NotificationHandler(BaseHandler):
    @auth_or_token
    async def get(self, notification_id=None):
        """Fetch notification(s)"""

        if notification_id is not None:
            try:
                notification_id = int(notification_id)
            except (TypeError, ValueError):
                return self.error(f"Invalid notification_id: {notification_id}")

        async with self.AsyncSession() as session:
            if notification_id is not None:
                notification = await session.scalar(
                    UserNotification.select(session.user_or_token).where(
                        UserNotification.id == notification_id
                    )
                )
                if notification is None:
                    return self.error(
                        f"Cannot find UserNotification with ID: {notification_id}"
                    )
                return self.success(data=notification)
            result = await session.scalars(
                UserNotification.select(session.user_or_token)
                .where(UserNotification.user_id == self.associated_user_object.id)
                .order_by(UserNotification.created_at.desc())
            )
            return self.success(data=result.all())

    @auth_or_token
    async def patch(self, notification_id):
        """Update a notification"""

        try:
            notification_id = int(notification_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid notification_id: {notification_id}")

        data = self.get_json()
        data["id"] = notification_id

        async with self.AsyncSession() as session:
            notification = await session.scalar(
                UserNotification.select(session.user_or_token, mode="update").where(
                    UserNotification.id == notification_id
                )
            )
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
            await session.commit()

            return self.success(action="skyportal/FETCH_NOTIFICATIONS")

    @auth_or_token
    async def delete(self, notification_id):
        """Delete a notification"""
        if notification_id is None:
            return self.error("Missing required notification_id")

        try:
            notification_id = int(notification_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid notification_id: {notification_id}")

        async with self.AsyncSession() as session:
            notification = await session.scalar(
                UserNotification.select(session.user_or_token, mode="delete").where(
                    UserNotification.id == notification_id
                )
            )
            if notification is None:
                return self.error(
                    f"Cannot find UserNotification with ID: {notification_id}"
                )

            await session.delete(notification)
            await session.commit()
            return self.success(action="skyportal/FETCH_NOTIFICATIONS")


class BulkNotificationHandler(BaseHandler):
    """Handler for operating on all of requesting user's notifications, e.g.
    deleting all notifications or marking all notifications as read."""

    @auth_or_token
    async def patch(self):
        """Update all notifications associated with requesting user."""
        data = self.get_json()
        async with self.AsyncSession() as session:
            result = await session.scalars(
                UserNotification.select(session.user_or_token, mode="update").where(
                    UserNotification.user_id == self.associated_user_object.id
                )
            )
            for notification in result.all():
                for key in data:
                    setattr(notification, key, data[key])
            await session.commit()
            return self.success(action="skyportal/FETCH_NOTIFICATIONS")

    @auth_or_token
    async def delete(self):
        """Delete all notifications associated with requesting user"""
        async with self.AsyncSession() as session:
            result = await session.scalars(
                UserNotification.select(session.user_or_token, mode="delete").where(
                    UserNotification.user_id == self.associated_user_object.id
                )
            )
            for notification in result.all():
                await session.delete(notification)
            await session.commit()
            return self.success(action="skyportal/FETCH_NOTIFICATIONS")
