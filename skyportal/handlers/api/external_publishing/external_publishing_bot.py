import json

from marshmallow.exceptions import ValidationError
from sqlalchemy.orm import joinedload

from baselayer.app.access import auth_or_token, permissions
from baselayer.log import make_log

from ....models import (
    Group,
)
from ....models.external_publishing_bot import (
    ExternalPublishingBot,
    ExternalPublishingBotGroup,
)
from ....utils.data_access import (
    process_instrument_ids,
    process_stream_ids,
    validate_photometry_options,
)
from ....utils.parse import get_list_typed, str_to_bool
from ...base import BaseHandler

log = make_log("api/external_publishing_bot")


def check_access_to_external_publishing_bot(session, external_publishing_bot_id):
    """Check if the user has access to the external_publishing_bot

    Parameters
    ----------
    session : `baselayer.app.models.Session`
        Database session
    external_publishing_bot_id : int
        The ID of the external_publishing_bot to check access for
    """
    external_publishing_bot = session.scalar(
        ExternalPublishingBot.select(session.user_or_token).where(
            ExternalPublishingBot.id == external_publishing_bot_id
        )
    )
    if external_publishing_bot is None:
        raise ValueError(
            f"No ExternalPublishingBot with ID {external_publishing_bot_id}, or inaccessible"
        )


def create_external_publishing_bot(
    data,
    owner_group_ids,
    instrument_ids,
    stream_ids,
    session,
):
    """Create a ExternalPublishingBot and its owner ExternalPublishingBotGroups

    Parameters
    ----------
    data : dict
        Dictionary containing the ExternalPublishingBot data passed in the PUT request
    owner_group_ids : list of int
        List of group IDs that will own the ExternalPublishingBot
    instrument_ids : list of int
        List of instrument IDs that can be used for publishing
    stream_ids : list of int
        List of stream IDs that can be used for publishing
    session : `baselayer.app.models.Session`
        Database session

    Returns
    -------
    int
        The ID of the newly created ExternalPublishingBot
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
        external_publishing_bot = ExternalPublishingBot.__schema__().load(data=data)
    except ValidationError as e:
        raise ValueError(
            f'Error parsing posted publishing bot: "{e.normalized_messages()}"'
        )
    session.add(external_publishing_bot)

    owner_groups = [
        ExternalPublishingBotGroup(
            external_publishing_bot_id=external_publishing_bot.id,
            group_id=owner_group_id,
            owner=True,
            auto_publish=False,
            auto_publish_allow_bots=False,
        )
        for owner_group_id in owner_group_ids
    ]
    for owner_group in owner_groups:
        session.add(owner_group)
        external_publishing_bot.groups.append(owner_group)

    instruments = process_instrument_ids(session, instrument_ids)
    if instruments:
        external_publishing_bot.instruments = instruments
    else:
        raise ValueError(
            "At least one instrument must be specified for external publishing"
        )

    streams = process_stream_ids(session, stream_ids)
    if streams:
        external_publishing_bot.streams = streams

    session.commit()
    return external_publishing_bot.id


def update_external_publishing_bot(
    data,
    existing_id,
    instrument_ids,
    stream_ids,
    session,
):
    """Update a ExternalPublishingBot and its owner ExternalPublishingBotGroups

    Parameters
    ----------
    data : dict
        Dictionary containing the ExternalPublishingBot data passed in the PUT request, won't update missing or empty fields
    existing_id : int
        The ID of the ExternalPublishingBot to update
    instrument_ids : list of int
        List of instrument IDs that can be used for publishing
    stream_ids : list of int
        List of stream IDs that can be used for publishing
    session : `baselayer.app.models.Session`
        Database session

    Returns
    -------
    id : int
        The ID of the updated ExternalPublishingBot
    """
    external_publishing_bot = session.scalar(
        ExternalPublishingBot.select(session.user_or_token, mode="update").where(
            ExternalPublishingBot.id == existing_id
        )
    )
    if external_publishing_bot is None:
        raise ValueError(
            f"No publishing bot with specified ID: {existing_id}, or you are not authorized to update it"
        )

    # Fields to update as-is if present
    for field in ["bot_name", "bot_id", "source_group_id", "_tns_altdata"]:
        if field in data:
            setattr(external_publishing_bot, field, data[field])

    # Fields requiring conversion
    for boolean_field in ["publish_existing_tns_objects", "testing"]:
        value = data.get(boolean_field)
        if value not in [None, ""]:
            setattr(external_publishing_bot, boolean_field, str_to_bool(str(value)))

    # Optional text field
    ack = data.get("acknowledgments")
    if ack not in [None, ""]:
        external_publishing_bot.acknowledgments = ack

    external_publishing_bot.photometry_options = validate_photometry_options(
        data.get("photometry_options", {}), external_publishing_bot.photometry_options
    )

    instruments = process_instrument_ids(session, instrument_ids)
    if instruments:
        external_publishing_bot.instruments = instruments

    streams = process_stream_ids(session, stream_ids)
    if streams:
        external_publishing_bot.streams = streams

    session.commit()
    return external_publishing_bot.id


class ExternalPublishingBotHandler(BaseHandler):
    @permissions(["Manage external publishing bots"])
    def put(self, existing_id=None):
        """
        ---
        summary: Create or update an external publishing bot
        description: Post or update an external publishing bot
        tags:
          - external publishing bot
        requestBody:
          content:
            application/json:
              schema: ExternalPublishingBotNoID
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
                              description: New External Publishing Bot ID
        """
        try:
            data = self.get_json()

            if "_tns_altdata" in data:
                if isinstance(data["_tns_altdata"], dict):
                    data["_tns_altdata"] = json.dumps(data["_tns_altdata"])
                data["_tns_altdata"] = data["_tns_altdata"].replace("'", '"')

        except Exception as e:
            return self.error(
                f"Failed to parse request for create/update publishing bot: {e}"
            )

        owner_group_ids = get_list_typed(data.pop("owner_group_ids", []), int)

        if len(owner_group_ids) > 0:
            owner_group_ids = list(set(owner_group_ids))

        instrument_ids = data.pop("instrument_ids", [])
        stream_ids = data.pop("stream_ids", [])

        with self.Session() as session:
            # Check for duplicates if we're creating a new bot
            if not existing_id:
                existing_external_publishing_bot = session.scalar(
                    ExternalPublishingBot.select(session.user_or_token).where(
                        ExternalPublishingBot.bot_id == data["bot_id"],
                        ExternalPublishingBot.bot_name == data["bot_name"],
                        ExternalPublishingBot.source_group_id
                        == data["source_group_id"],
                        ExternalPublishingBot.groups.any(
                            ExternalPublishingBotGroup.group_id.in_(owner_group_ids)
                        ),
                    )
                )
                if existing_external_publishing_bot:
                    return self.error(
                        f"A publishing bot with the same bot_id, bot_name, and source_group_id already exists with id: {existing_external_publishing_bot.id} (owned by group_ids: {owner_group_ids}), specify the ID to update it"
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

                    bot_id = create_external_publishing_bot(
                        data,
                        owner_group_ids,
                        instrument_ids,
                        stream_ids,
                        session,
                    )
                    self.push(
                        action="skyportal/REFRESH_EXTERNAL_PUBLISHING_BOTS",
                    )
                    return self.success(data={"id": bot_id})
                except Exception as e:
                    return self.error(f"Failed to create publishing bot: {e}")
            else:
                try:
                    bot_id = update_external_publishing_bot(
                        data,
                        existing_id,
                        instrument_ids,
                        stream_ids,
                        session,
                    )
                    self.push(
                        action="skyportal/REFRESH_EXTERNAL_PUBLISHING_BOTS",
                    )
                    return self.success(data={"id": bot_id})
                except Exception as e:
                    return self.error(f"Failed to update publishing bot: {e}")

    @auth_or_token
    def get(self, external_publishing_bot_id=None):
        """
        ---
        single:
          summary: Retrieve an external publishing bot
          description: Retrieve an external publishing bot
          tags:
            - external publishing bot
          parameters:
            - in: path
              name: external_publishing_bot_id
              required: true
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema: SingleExternalPublishingBot
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          summary: Retrieve all external publishing bots
          description: Retrieve all external publishing bots
          tags:
            - external publishing bot
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfExternalPublishingBots
            400:
              content:
                application/json:
                  schema: Error
        """
        with self.Session() as session:
            stmt = ExternalPublishingBot.select(
                session.user_or_token, mode="read"
            ).options(
                joinedload(ExternalPublishingBot.groups),
                joinedload(ExternalPublishingBot.coauthors),
                joinedload(ExternalPublishingBot.instruments),
                joinedload(ExternalPublishingBot.streams),
            )
            if external_publishing_bot_id:
                external_publishing_bot = session.scalar(
                    stmt.where(ExternalPublishingBot.id == external_publishing_bot_id)
                )
                if external_publishing_bot is None:
                    return self.error(
                        f"No publishing bot with ID {external_publishing_bot_id}"
                    )
                # for each of the groups, we load the users, and grab the list of owner groups
                owner_group_ids = []
                for group in external_publishing_bot.groups:
                    if group.owner:
                        owner_group_ids.append(group.group_id)
                    group.auto_publishers  # we just need to load the users by accessing the attribute
                external_publishing_bot.owner_group_ids = owner_group_ids
                return self.success(data=external_publishing_bot)
            else:
                external_publishing_bots = session.scalars(stmt).unique().all()
                # for each of the groups, we load the users
                for external_publishing_bot in external_publishing_bots:
                    owner_group_ids = []
                    for group in external_publishing_bot.groups:
                        if group.owner:
                            owner_group_ids.append(group.group_id)
                        group.auto_publishers  # we just need to load the users by accessing the attribute
                    external_publishing_bot.owner_group_ids = owner_group_ids
                return self.success(data=external_publishing_bots)

    @permissions(["Manage external publishing bots"])
    def delete(self, external_publishing_bot_id):
        """
        ---
        summary: Delete an external publishing bot
        description: Delete an external publishing bot
        tags:
          - external publishing bot
        parameters:
          - in: path
            name: external_publishing_bot_id
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
            external_publishing_bot = session.scalar(
                ExternalPublishingBot.select(
                    session.user_or_token, mode="delete"
                ).where(ExternalPublishingBot.id == external_publishing_bot_id)
            )
            if external_publishing_bot is None:
                return self.error(
                    f"No publishing bot with ID {external_publishing_bot_id}, or you are not authorized to delete it"
                )
            session.delete(external_publishing_bot)
            session.commit()
            self.push(
                action="skyportal/REFRESH_EXTERNAL_PUBLISHING_BOTS",
            )
            return self.success()
