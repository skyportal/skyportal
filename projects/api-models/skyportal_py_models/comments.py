"""Response models for source comments."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

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


__all__ = [
    "CommentAttachmentBatchResponse",
    "CommentAttachmentCountsResponse",
    "CommentAttachmentResponse",
    "CommentDetailResponse",
    "CommentResponse",
]
