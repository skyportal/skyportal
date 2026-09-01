"""Response models for source comments."""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from skyportal_py_models._cyclic import CommentResponse


class CommentDetailResponse(CommentResponse):
    """A single comment, as returned by the single-comment endpoint."""


class CommentAttachmentResponse(BaseModel):
    """The decoded contents of a comment attachment."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    comment_id: int = Field(alias="commentId")
    attachment: str | None = None
    attachment_name: str | None = Field(alias="attachmentName", default=None)


class CommentAttachmentCountsResponse(BaseModel):
    """How many comments still hold their attachment in the database."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    total_without_attachment_bytes: int = Field(
        alias="totalWithoutAttachmentBytes", default=0
    )
    total_with_attachment_bytes: int = Field(
        alias="totalWithAttachmentBytes", default=0
    )


class CommentAttachmentBatchResponse(BaseModel):
    """Result of moving one page of comment attachments to disk."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    total_matches: int = Field(alias="totalMatches", default=0)
    page_number: int = Field(alias="pageNumber", default=1)
    num_per_page: int = Field(alias="numPerPage", default=100)


class CommentAttachment(BaseModel):
    """A comment file attachment (name + base64-encoded body)."""

    model_config = ConfigDict(extra="forbid")

    body: str | None = Field(description="base64-encoded file contents")
    name: str = Field(description="Attachment file name")


class CommentPostBody(BaseModel):
    """Request body for posting a comment."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(description="Comment body text")
    group_ids: list[int] | None = Field(
        default=None,
        description="List of group IDs corresponding to which groups should be "
        "able to view comment. Defaults to the public group.",
    )
    attachment: CommentAttachment | None = Field(
        default=None, description="Optional file attachment."
    )
    channel: str | None = Field(
        default=None,
        description="Conversation the comment belongs to; the main thread if unset. "
        "Only used for comments on sources.",
    )


class CommentPostResponse(BaseModel):
    """Data payload returned when posting a comment."""

    comment_id: int = Field(description="New comment ID")


class CommentPutBody(BaseModel):
    """Request body for updating a comment."""

    model_config = ConfigDict(extra="forbid")

    text: str | None = Field(default=None, description="Comment body text")
    group_ids: list[int] | None = Field(
        default=None,
        description="List of group IDs corresponding to which groups should be "
        "able to view comment.",
    )
    attachment: CommentAttachment | None = Field(
        default=None, description="Optional file attachment."
    )


class CommentGetQuery(BaseModel):
    """Query parameters for retrieving comments."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset()

    text: str | None = Field(
        default=None,
        description="Filter comments by partial text match.",
    )
    pageNumber: int = Field(
        default=1,
        description="Page number for pagination.",
    )
    numPerPage: int = Field(
        default=25,
        description="Number of comments per page.",
    )
    channel: str | None = Field(
        default=None,
        description="Only return comments on this channel. Defaults to the "
        "comments with no channel set.",
    )


class CommentAttachmentGetQuery(BaseModel):
    """Query parameters for retrieving a comment attachment."""

    model_config = ConfigDict(extra="forbid")

    download: bool = Field(
        default=True,
        description="If true, download the attachment; else return file data as text. True by default.",
    )
    preview: bool = Field(
        default=False,
        description="If true, return an attachment preview. False by default.",
    )

    @model_validator(mode="after")
    def _preview_overrides_default_download(self):
        if self.preview and "download" not in self.model_fields_set:
            self.download = False
        return self


DEFAULT_COMMENTS_PER_PAGE = 100


MAX_COMMENTS_PER_PAGE = 500


class CommentAttachmentUpdatePostQuery(BaseModel):
    """Query parameters for the comment attachment migration."""

    model_config = ConfigDict(extra="forbid")

    pageNumber: int = Field(
        default=1,
        description="Page number for paginated query results. Defaults to 1.",
    )
    numPerPage: int = Field(
        default=DEFAULT_COMMENTS_PER_PAGE,
        description=(
            f"Number of comments to migrate per paginated request. Defaults to "
            f"{DEFAULT_COMMENTS_PER_PAGE}. Capped at {MAX_COMMENTS_PER_PAGE}."
        ),
    )


__all__ = [
    "CommentAttachment",
    "CommentPostBody",
    "CommentPostResponse",
    "CommentPutBody",
    "CommentGetQuery",
    "CommentAttachmentGetQuery",
    "DEFAULT_COMMENTS_PER_PAGE",
    "MAX_COMMENTS_PER_PAGE",
    "CommentAttachmentUpdatePostQuery",
    "CommentAttachmentBatchResponse",
    "CommentAttachmentCountsResponse",
    "CommentAttachmentResponse",
    "CommentDetailResponse",
    "CommentResponse",
]
