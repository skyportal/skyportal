"""Response models for ``/api/sharing_service``."""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models.instruments import InstrumentResponse
from skyportal_py_models.sources import SourceResponse
from skyportal_py_models.streams import StreamResponse


class PhotometryOptionsResponse(BaseModel):
    """Which photometry a sharing service publishes (``PHOTOMETRY_OPTIONS``).

    The server fills in every option it knows about, defaulting each to true,
    so a stored value always carries the full set.
    """

    model_config = ConfigDict(extra="forbid")

    first_and_last_detections: bool | None = None
    auto_sharing_allow_archival: bool | None = None


class SharingServiceCoauthorResponse(BaseModel):
    """A coauthor of a service's submissions (``SharingServiceCoauthor``)."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    sharing_service_id: int | None = None
    user_id: int | None = None


class SharingServiceGroupAutoPublisherResponse(BaseModel):
    """An auto-publisher (``SharingServiceGroupAutoPublisher``).

    ``user_id`` is a column property derived from ``group_user_id`` rather
    than a stored column.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    sharing_service_group_id: int | None = None
    group_user_id: int | None = None
    user_id: int | None = None


class SharingServiceGroupResponse(BaseModel):
    """A group's access to a service (``SharingServiceGroup``).

    The ``group`` and ``sharing_service`` relationships are never eager-loaded
    by the endpoints, so they never appear and are not declared.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    sharing_service_id: int | None = None
    group_id: int | None = None
    owner: bool | None = None
    auto_share_to_tns: bool | None = None
    auto_share_to_hermes: bool | None = None
    auto_sharing_allow_bots: bool | None = None
    auto_publishers: list[SharingServiceGroupAutoPublisherResponse] = Field(
        default_factory=list
    )


class SharingServiceResponse(BaseModel):
    """A service publishing objects externally (``SharingService``).

    ``owner_group_ids`` is not a column: the endpoint derives it from the
    owning entries of ``groups`` and injects it. The encrypted TNS credentials
    (``_tns_altdata``) are never serialized, and the ``submissions``
    relationship is never eager-loaded, so neither is declared.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    name: str | None = None
    acknowledgments: str | None = None
    testing: bool | None = None
    photometry_options: PhotometryOptionsResponse | None = None
    enable_sharing_with_tns: bool | None = None
    enable_sharing_with_hermes: bool | None = None
    tns_bot_name: str | None = None
    tns_bot_id: int | None = None
    tns_source_group_id: int | None = None
    publish_existing_tns_objects: bool | None = None
    owner_group_ids: list[int] = Field(default_factory=list)
    groups: list[SharingServiceGroupResponse] = Field(default_factory=list)
    coauthors: list[SharingServiceCoauthorResponse] = Field(default_factory=list)
    instruments: list[InstrumentResponse] = Field(default_factory=list)
    streams: list[StreamResponse] = Field(default_factory=list)


class SharingServiceAutoPublishersPostResponse(BaseModel):
    """Result of adding auto-publishers to a sharing service group."""

    model_config = ConfigDict(extra="forbid")

    ids: list[int] = Field(default_factory=list)


class SharingServiceSubmissionResponse(BaseModel):
    """A publication request (``SharingServiceSubmission``).

    ``tns_name`` is not a column: the endpoint copies it off the submitted
    object. ``tns_payload``, ``tns_response`` and ``hermes_response`` are
    deferred and only appear when explicitly requested. The ``user`` and
    ``sharing_service`` relationships are never eager-loaded, so they are
    not declared.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    sharing_service_id: int | None = None
    obj_id: str | None = None
    obj: SourceResponse | None = None
    tns_name: str | None = None
    user_id: int | None = None
    custom_publishing_string: str | None = None
    custom_remarks_string: str | None = None
    publish_to_tns: bool | None = None
    tns_status: str | None = None
    tns_submission_id: int | None = None
    tns_payload: dict[str, Any] | None = None
    tns_response: dict[str, Any] | None = None
    publish_to_hermes: bool | None = None
    hermes_status: str | None = None
    hermes_response: dict[str, Any] | None = None
    archival: bool | None = None
    archival_comment: str | None = None
    auto_submission: bool | None = None
    instrument_ids: list[int] | None = None
    stream_ids: list[int] | None = None
    photometry_options: PhotometryOptionsResponse | None = None


class SharingServiceSubmissionsPageResponse(BaseModel):
    """One page of results from a sharing service submissions query."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    sharing_service_id: int | None = None
    submissions: list[SharingServiceSubmissionResponse] = Field(default_factory=list)
    total_matches: int = Field(alias="totalMatches", default=0)
    page_number: int = Field(alias="pageNumber", default=1)
    num_per_page: int = Field(alias="numPerPage", default=100)


class PhotometryOptions(BaseModel):
    """Which photometry a sharing service publishes (upstream ``PHOTOMETRY_OPTIONS``).

    The server fills in every option it knows about, defaulting each to true,
    so a stored value always carries the full set.
    """

    model_config = ConfigDict(extra="forbid")

    first_and_last_detections: bool | None = None
    auto_sharing_allow_archival: bool | None = None


class SharingServicePost(BaseModel):
    """Payload for creating or updating a sharing service."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    name: str
    owner_group_ids: list[int] | None = None
    instrument_ids: list[int] | None = None
    stream_ids: list[int] | None = None
    acknowledgments: str | None = None
    testing: bool | None = None
    photometry_options: PhotometryOptions | None = None
    enable_sharing_with_tns: bool | None = None
    enable_sharing_with_hermes: bool | None = None
    tns_bot_name: str | None = None
    tns_bot_id: int | None = None
    tns_source_group_id: int | None = None
    tns_altdata: dict[str, Any] | None = Field(default=None, alias="_tns_altdata")
    publish_existing_tns_objects: bool | None = None


class SharingServiceSubmissionPost(BaseModel):
    """Payload for requesting the publication of an object."""

    model_config = ConfigDict(extra="forbid")

    obj_id: str
    sharing_service_id: int
    publishers: str
    remarks: str | None = None
    archival: bool | None = None
    archival_comment: str | None = None
    instrument_ids: list[int] | None = None
    stream_ids: list[int] | None = None
    photometry_options: PhotometryOptions | None = None
    publish_to_tns: bool | None = None
    publish_to_hermes: bool | None = None


class SharingServicePutBody(BaseModel):
    """Request body for creating or updating a sharing service. On update, only
    the provided fields are changed."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, description="Sharing service name.")
    owner_group_ids: list[int] | str | None = Field(
        default=None,
        description="IDs of the groups that will own the sharing service (used "
        "on creation).",
    )
    instrument_ids: list[int] | str | None = Field(
        default=None,
        description="IDs of the instruments to restrict the photometry to when "
        "publishing.",
    )
    stream_ids: list[int] | str | None = Field(
        default=None,
        description="IDs of the streams to restrict the photometry to when publishing.",
    )
    acknowledgments: str | None = Field(
        default=None, description="Acknowledgments to use for sharing."
    )
    testing: bool | str | None = Field(
        default=None,
        description="If true, nothing will be shared but the request's payload "
        "will be stored.",
    )
    photometry_options: dict[str, Any] | None = Field(
        default=None,
        description="Photometry options to make some data optional or mandatory "
        "for manual and auto-publishing.",
    )
    enable_sharing_with_hermes: bool | None = Field(
        default=None, description="Whether to enable publishing to Hermes or not."
    )
    enable_sharing_with_tns: bool | None = Field(
        default=None, description="Whether to enable publishing to TNS or not."
    )
    tns_bot_name: str | None = Field(default=None, description="Name of the TNS bot.")
    tns_bot_id: int | None = Field(default=None, description="ID of the TNS bot.")
    tns_source_group_id: int | None = Field(
        default=None, description="Source group ID of the TNS bot."
    )
    tns_altdata: dict | str | None = Field(
        default=None,
        alias="_tns_altdata",
        description="TNS altdata (e.g. the API key), as a JSON object or string.",
    )
    publish_existing_tns_objects: bool | str | None = Field(
        default=None,
        description="Whether to publish objects that already exist in TNS but "
        "not reported under this internal name.",
    )


class SharingServicePutResponse(BaseModel):
    """Data payload returned when creating or updating a sharing service."""

    id: int = Field(description="New Sharing Service ID")


class SharingServiceCoauthorPostBody(BaseModel):
    """Request body for adding a coauthor to an external sharing service."""

    model_config = ConfigDict(extra="forbid")

    user_id: int | None = Field(
        default=None,
        description="ID of the user to add as a coauthor, if not specified in the URL",
    )


class SharingServiceCoauthorPostResponse(BaseModel):
    """Data payload returned when adding a coauthor."""

    id: int = Field(description="New SharingServiceCoauthor ID")


class SharingServiceGroupPutBody(BaseModel):
    """Request body for adding or editing a group of an external sharing service."""

    model_config = ConfigDict(extra="forbid")

    group_id: int | None = Field(default=None, description="ID of the group to add")
    auto_share_to_tns: bool | str | None = Field(
        default=None, description="Whether to automatically publish to TNS"
    )
    auto_share_to_hermes: bool | str | None = Field(
        default=None, description="Whether to automatically publish to Hermes"
    )
    auto_sharing_allow_bots: bool | str | None = Field(
        default=None, description="Whether to allow bots to automatically publish"
    )
    owner: bool | str | None = Field(
        default=None,
        description="Whether this group is the owner of the external sharing service",
    )


class SharingServiceGroupPutResponse(BaseModel):
    """Data payload returned when adding or editing a sharing service group."""

    id: int = Field(description="SharingServiceGroup ID")


class SharingServiceGroupAutoPublisherPostBody(BaseModel):
    """Request body for adding auto_publisher(s) to a SharingServiceGroup."""

    model_config = ConfigDict(extra="forbid")

    user_ids: list[int] | str | None = Field(
        default_factory=list,
        description="An array of user IDs to add as auto_publishers. If a "
        "string is provided, it will be split by commas.",
    )
    user_id: int | None = Field(
        default=None,
        description="ID of the user to add as an auto_publisher, used if "
        "user_ids is empty and no user_id is given in the URL.",
    )


class SharingServiceGroupAutoPublisherPostResponse(BaseModel):
    """Data payload returned when adding auto_publisher(s)."""

    ids: list[int] = Field(
        description="IDs of the new SharingServiceGroupAutoPublishers"
    )


class SharingServiceGroupAutoPublisherDeleteBody(BaseModel):
    """Request body for removing auto_publisher(s) from a SharingServiceGroup."""

    model_config = ConfigDict(extra="forbid")

    user_id: int | None = Field(
        default=None, description="The ID of the User to remove as an auto_publisher"
    )
    user_ids: list[int] | str | None = Field(
        default_factory=list,
        description="The IDs of the Users to remove as auto_publishers, overrides user_id",
    )


class SharingServiceSubmissionGetQuery(BaseModel):
    """Query parameters for retrieving sharing service submissions."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset({"sharing_service_id"})

    sharing_service_id: int = Field(
        description=(
            "The ID of the external sharing service to which the submissions belong"
        ),
    )
    pageNumber: int = Field(
        default=1,
        description="The page number to retrieve, starting at 1",
    )
    numPerPage: int = Field(
        default=100,
        description="The number of results per page, defaults to 100",
    )
    include_payload: bool = Field(
        default=False,
        description="Whether to include the payload in the response",
    )
    include_response: bool = Field(
        default=False,
        description="Whether to include the response in the response",
    )
    objectID: str | None = Field(
        default=None,
        description="The object ID of the submission",
    )


class SharingServiceSubmissionPostBody(BaseModel):
    """Request body for publishing an Obj to TNS or Hermes via a sharing service."""

    model_config = ConfigDict(extra="forbid")

    obj_id: str | None = Field(default=None, description="ID of the object to publish")
    sharing_service_id: int | None = Field(
        default=None,
        description="ID of the external sharing service to use for submission",
    )
    publishers: str | None = Field(
        default="", description="Custom string for publishers"
    )
    remarks: str | None = Field(default="", description="Custom remarks string")
    archival: bool | None = Field(
        default=False, description="Flag to indicate if the source is archival"
    )
    archival_comment: str | None = Field(
        default="",
        description="Comment for archival sources (required if archival is True)",
    )
    instrument_ids: list[int] | None = Field(
        default_factory=list,
        description="List of instrument IDs to associate with the submission",
    )
    stream_ids: list[int] | None = Field(
        default_factory=list,
        description="List of stream IDs to associate with the submission",
    )
    photometry_options: dict[str, Any] | None = Field(
        default_factory=dict, description="Options for photometry processing"
    )
    publish_to_tns: bool | None = Field(
        default=False,
        description="Flag to indicate if the submission should be published to TNS",
    )
    publish_to_hermes: bool | None = Field(
        default=False,
        description="Flag to indicate if the submission should be published to Hermes",
    )
