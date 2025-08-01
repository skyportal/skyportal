import json

from marshmallow.exceptions import ValidationError
from sqlalchemy.orm import joinedload

from baselayer.app.access import auth_or_token, permissions
from baselayer.log import make_log

from ....models import (
    Group,
    SharingService,
    SharingServiceGroup,
)
from ....utils.data_access import (
    process_instrument_ids,
    process_stream_ids,
    validate_photometry_options,
)
from ....utils.parse import get_list_typed, str_to_bool
from ...base import BaseHandler

log = make_log("api/sharing_service")


def validate_tns_fields(sharing_service):
    if sharing_service.enable_sharing_with_tns:
        # tns_source_group_id, tns_bot_id, and tns_api_key are required
        if sharing_service.tns_source_group_id is None:
            raise ValueError(
                "tns_source_group_id must be provided when enable_sharing_with_tns is True"
            )
        if sharing_service.tns_bot_id is None:
            raise ValueError(
                "tns_bot_id must be provided when enable_sharing_with_tns is True"
            )
        if not (
            isinstance(sharing_service.tns_altdata, dict)
            and "api_key" in sharing_service.tns_altdata
        ):
            raise ValueError(
                "TNS API key must be provided when enable_sharing_with_tns is True"
            )


def create_sharing_service(
    data,
    owner_group_ids,
    instrument_ids,
    stream_ids,
    session,
):
    """Create a SharingService and its owner SharingServiceGroups

    Parameters
    ----------
    data : dict
        Dictionary containing the SharingService data passed in the PUT request
    owner_group_ids : list of int
        List of group IDs that will own the SharingService
    instrument_ids : list of int
        List of instrument IDs that can be used for publishing
    stream_ids : list of int
        List of stream IDs that can be used for publishing
    session : `baselayer.app.models.Session`
        Database session

    Returns
    -------
    int
        The ID of the newly created SharingService
    """
    data = {
        **data,
        "publish_existing_tns_objects": str_to_bool(
            data.get("publish_existing_tns_objects", "false")
        ),
        "testing": str_to_bool(data.get("testing", "true")),
        "photometry_options": validate_photometry_options(
            data.get("photometry_options", {})
        ),
    }

    try:
        sharing_service = SharingService.__schema__().load(data=data)
        validate_tns_fields(sharing_service)
    except ValidationError as e:
        raise ValueError(
            f'Error parsing posted sharing service: "{e.normalized_messages()}"'
        )
    session.add(sharing_service)

    owner_groups = [
        SharingServiceGroup(
            sharing_service_id=sharing_service.id,
            group_id=owner_group_id,
            owner=True,
            auto_share_to_tns=False,
            auto_share_to_hermes=False,
            auto_sharing_allow_bots=False,
        )
        for owner_group_id in owner_group_ids
    ]
    for owner_group in owner_groups:
        session.add(owner_group)
        sharing_service.groups.append(owner_group)

    instruments = process_instrument_ids(session, session.user_or_token, instrument_ids)
    if instruments:
        sharing_service.instruments = instruments
    else:
        raise ValueError("At least one instrument must be specified for sharing")

    streams = process_stream_ids(session, session.user_or_token, stream_ids)
    if streams:
        sharing_service.streams = streams

    session.commit()
    return sharing_service.id


def update_sharing_service(
    data,
    existing_id,
    instrument_ids,
    stream_ids,
    session,
):
    """Update a SharingService and its owner SharingServiceGroups

    Parameters
    ----------
    data : dict
        Dictionary containing the SharingService data passed in the PUT request, won't update missing or empty fields
    existing_id : int
        The ID of the SharingService to update
    instrument_ids : list of int
        List of instrument IDs that can be used for publishing
    stream_ids : list of int
        List of stream IDs that can be used for publishing
    session : `baselayer.app.models.Session`
        Database session

    Returns
    -------
    id : int
        The ID of the updated SharingService
    """
    sharing_service = session.scalar(
        SharingService.select(session.user_or_token, mode="update").where(
            SharingService.id == existing_id
        )
    )
    if sharing_service is None:
        raise ValueError(
            f"No sharing service with specified ID: {existing_id}, or you are not authorized to update it"
        )

    if "enable_sharing_with_tns" in data or "enable_sharing_with_hermes" in data:
        for group in sharing_service.groups:
            if data.get("enable_sharing_with_tns") is False:
                group.auto_share_to_tns = False
            if data.get("enable_sharing_with_hermes") is False:
                group.auto_share_to_hermes = False
            if group.auto_share_to_hermes is False and group.auto_share_to_tns is False:
                group.auto_sharing_allow_bots = False

    # Fields to update as-is if present
    for field in [
        "name",
        "tns_bot_name",
        "tns_bot_id",
        "tns_source_group_id",
        "_tns_altdata",
        "enable_sharing_with_tns",
        "enable_sharing_with_hermes",
    ]:
        if field in data:
            setattr(sharing_service, field, data[field])

    # Fields requiring conversion
    for boolean_field in ["publish_existing_tns_objects", "testing"]:
        value = data.get(boolean_field)
        if value not in [None, ""]:
            setattr(sharing_service, boolean_field, str_to_bool(value))

    # Optional text field
    ack = data.get("acknowledgments")
    if ack not in [None, ""]:
        sharing_service.acknowledgments = ack

    sharing_service.photometry_options = validate_photometry_options(
        data.get("photometry_options", {}), sharing_service.photometry_options
    )

    instruments = process_instrument_ids(session, session.user_or_token, instrument_ids)
    if instruments:
        sharing_service.instruments = instruments

    sharing_service.streams = (
        process_stream_ids(session, session.user_or_token, stream_ids) or []
    )

    validate_tns_fields(sharing_service)

    session.commit()
    return sharing_service.id


class SharingServiceHandler(BaseHandler):
    @permissions(["Manage sharing services"])
    def put(self, existing_id=None):
        """
        ---
        summary: Create or update a sharing service
        description: Post or update a sharing service
        tags:
          - sharing service
        requestBody:
          content:
            application/json:
              schema: SharingServiceNoID
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          type: object
                          properties:
                            id:
                              type: integer
                              description: New Sharing Service ID
        """
        try:
            data = self.get_json()

            if "_tns_altdata" in data:
                if isinstance(data["_tns_altdata"], dict):
                    data["_tns_altdata"] = json.dumps(data["_tns_altdata"])
                data["_tns_altdata"] = data["_tns_altdata"].replace("'", '"')

        except Exception as e:
            return self.error(
                f"Failed to parse request for create/update sharing service: {e}"
            )

        owner_group_ids = get_list_typed(data.pop("owner_group_ids", []), int)

        if owner_group_ids:
            owner_group_ids = list(set(owner_group_ids))

        instrument_ids = data.pop("instrument_ids", [])
        stream_ids = data.pop("stream_ids", [])

        with self.Session() as session:
            # Check for duplicates if we're creating a new sharing service
            if not existing_id:
                existing_sharing_service = session.scalar(
                    SharingService.select(session.user_or_token).where(
                        SharingService.name == data["name"]
                    )
                )
                if existing_sharing_service:
                    return self.error(
                        f"A sharing service with the same name already exists (id: {existing_sharing_service.id})"
                    )

                try:
                    owner_groups = session.scalars(
                        Group.select(session.user_or_token).where(
                            Group.id.in_(owner_group_ids)
                        )
                    ).all()
                    if len(owner_groups) != len(owner_group_ids):
                        return self.error(
                            f"One or more owner groups not found: {owner_group_ids}"
                        )

                    sharing_service_id = create_sharing_service(
                        data,
                        owner_group_ids,
                        instrument_ids,
                        stream_ids,
                        session,
                    )
                    self.push(
                        action="skyportal/REFRESH_SHARING_SERVICES",
                    )
                    return self.success(data={"id": sharing_service_id})
                except Exception as e:
                    return self.error(f"Failed to create sharing service: {e}")
            else:
                try:
                    sharing_service_id = update_sharing_service(
                        data,
                        existing_id,
                        instrument_ids,
                        stream_ids,
                        session,
                    )
                    self.push(
                        action="skyportal/REFRESH_SHARING_SERVICES",
                    )
                    return self.success(data={"id": sharing_service_id})
                except Exception as e:
                    return self.error(f"Failed to update sharing service: {e}")

    @auth_or_token
    def get(self, sharing_service_id=None):
        """
        ---
        single:
          summary: Retrieve an external sharing service
          description: Retrieve an external sharing service
          tags:
            - external sharing service
          parameters:
            - in: path
              name: sharing_service_id
              required: true
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleSharingService
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          summary: Retrieve all external sharing services
          description: Retrieve all external sharing services
          tags:
            - external sharing service
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfSharingServices
            400:
              content:
                application/json:
                  schema: Error
        """
        with self.Session() as session:
            stmt = SharingService.select(session.user_or_token, mode="read").options(
                joinedload(SharingService.groups),
                joinedload(SharingService.coauthors),
                joinedload(SharingService.instruments),
                joinedload(SharingService.streams),
            )
            if sharing_service_id:
                sharing_service = session.scalar(
                    stmt.where(SharingService.id == sharing_service_id)
                )
                if sharing_service is None:
                    return self.error(
                        f"No sharing service with ID {sharing_service_id}"
                    )
                # for each of the groups, we load the users, and grab the list of owner groups
                owner_group_ids = []
                for group in sharing_service.groups:
                    if group.owner:
                        owner_group_ids.append(group.group_id)
                    group.auto_publishers  # we just need to load the users by accessing the attribute
                sharing_service.owner_group_ids = owner_group_ids
                return self.success(data=sharing_service)
            else:
                sharing_services = session.scalars(stmt).unique().all()
                # for each of the groups, we load the users
                for sharing_service in sharing_services:
                    owner_group_ids = []
                    for group in sharing_service.groups:
                        if group.owner:
                            owner_group_ids.append(group.group_id)
                        group.auto_publishers  # we just need to load the users by accessing the attribute
                    sharing_service.owner_group_ids = owner_group_ids
                return self.success(data=sharing_services)

    @permissions(["Manage sharing services"])
    def delete(self, sharing_service_id):
        """
        ---
        summary: Delete an external sharing service
        description: Delete an external sharing service
        tags:
          - external sharing service
        parameters:
          - in: path
            name: sharing_service_id
            required: true
            schema:
              type: integer
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

        with self.Session() as session:
            sharing_service = session.scalar(
                SharingService.select(session.user_or_token, mode="delete").where(
                    SharingService.id == sharing_service_id
                )
            )
            if sharing_service is None:
                return self.error(
                    f"No sharing service with ID {sharing_service_id}, or you are not authorized to delete it"
                )
            session.delete(sharing_service)
            session.commit()
            self.push(
                action="skyportal/REFRESH_SHARING_SERVICES",
            )
            return self.success()
