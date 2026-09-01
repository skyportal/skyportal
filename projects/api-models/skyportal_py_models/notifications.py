"""Request and response models for SkyPortal notifications."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class NotificationPatchBody(BaseModel):
    """Request body for updating a notification (or all of a user's
    notifications)."""

    model_config = ConfigDict(extra="forbid")

    viewed: bool = Field(description="Whether the notification has been viewed")


email = False


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


class NotificationPatchBody(BaseModel):
    """Request body for updating a notification (or all of a user's
    notifications)."""

    model_config = ConfigDict(extra="forbid")

    viewed: bool = Field(description="Whether the notification has been viewed")


email = False


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


class NotificationPatchBody(BaseModel):
    """Request body for updating a notification (or all of a user's
    notifications)."""

    model_config = ConfigDict(extra="forbid")

    viewed: bool = Field(description="Whether the notification has been viewed")


email = False


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


class NotificationPatchBody(BaseModel):
    """Request body for updating a notification (or all of a user's
    notifications)."""

    model_config = ConfigDict(extra="forbid")

    viewed: bool = Field(description="Whether the notification has been viewed")


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
