import json

from handlers.base import BaseHandler
from marshmallow.exceptions import ValidationError
from models import (
    Group,
    Instrument,
    Stream,
    TNSRobot,
    TNSRobotGroup,
)
from sqlalchemy.orm import joinedload
from utils.tns import TNS_INSTRUMENT_IDS

from baselayer.app.access import auth_or_token, permissions
from baselayer.log import make_log

log = make_log("api/tns_robot")


PHOTOMETRY_OPTIONS = {
    "first_and_last_detections": bool,
    "autoreport_allow_archival": bool,
}


def validate_photometry_options(photometry_options, existing_photometry_options=None):
    """Validate the photometry options and their values

    Parameters
    ----------
    photometry_options : dict
        Dictionary containing the photometry options
    existing_photometry_options : dict, optional
        Dictionary containing the existing photometry options, by default None

    Returns
    -------
    dict
        Dictionary containing the validated photometry options
    """
    if photometry_options is None:
        photometry_options = {}
    if not isinstance(photometry_options, dict):
        raise ValueError("photometry_options must be a dictionary")

    # if existing_photometry_options is provided, add missing keys with the existing values
    if existing_photometry_options is not None and isinstance(
        existing_photometry_options, dict
    ):
        for key in PHOTOMETRY_OPTIONS:
            if key not in photometry_options and key in existing_photometry_options:
                photometry_options[key] = existing_photometry_options[key]

    # validate the photometry options and their values
    for key, value in photometry_options.items():
        if key not in PHOTOMETRY_OPTIONS:
            raise ValueError(f"Invalid photometry option: {key}")
        if not isinstance(value, PHOTOMETRY_OPTIONS[key]):
            raise ValueError(f"Invalid value for photometry option {key}: {value}")

    # add the missing keys with default values (default to True if not specified)
    for key in PHOTOMETRY_OPTIONS:
        if key not in photometry_options:
            photometry_options[key] = True

    return photometry_options


def create_tns_robot(
    data,
    owner_group_ids,
    instrument_ids,
    stream_ids,
    session,
):
    """Create a TNSRobot and its owner TNSRobotGroups

    Parameters
    ----------
    data : dict
        Dictionary containing the TNSRobot data passed in the PUT request
    owner_group_ids : list of int
        List of group IDs that will own the TNSRobot
    instrument_ids : list of int
        List of instrument IDs that can be used for TNS reporting
    stream_ids : list of int
        List of stream IDs that can be used for TNS reporting
    session : `baselayer.app.models.Session`
        Database session

    Returns
    -------
    int
        The ID of the newly created TNSRobot
    """

    # False if not specified
    report_existing = data.get("report_existing", False)
    if str(report_existing).lower().strip() in ["true", "t", "1"]:
        report_existing = True
    else:
        report_existing = False
    data["report_existing"] = report_existing

    # True if not specified
    testing = data.get("testing", True)
    if str(testing).lower().strip() in ["false", "f", "0"]:
        testing = False
    else:
        testing = True
    data["testing"] = testing

    data["photometry_options"] = validate_photometry_options(
        data.get("photometry_options", {})
    )

    try:
        tnsrobot = TNSRobot.__schema__().load(data=data)
    except ValidationError as e:
        raise ValueError(f'Error parsing posted tnsrobot: "{e.normalized_messages()}"')
    session.add(tnsrobot)

    # we create the owner group(s)
    owner_groups = [
        TNSRobotGroup(
            tnsrobot_id=tnsrobot.id,
            group_id=owner_group_id,
            owner=True,
            auto_report=False,
        )
        for owner_group_id in owner_group_ids
    ]
    for owner_group in owner_groups:
        session.add(owner_group)
        tnsrobot.groups.append(owner_group)

    # TNS AUTO-REPORTING INSTRUMENTS: ADD/MODIFY/DELETE
    if len(instrument_ids) == 0:
        raise ValueError("At least one instrument must be specified for TNS reporting")

    try:
        instrument_ids = [int(x) for x in instrument_ids]
        if isinstance(instrument_ids, str):
            instrument_ids = [int(x) for x in instrument_ids.split(",")]
        else:
            instrument_ids = [int(x) for x in instrument_ids]
    except ValueError:
        raise ValueError("instrument_ids must be a comma-separated list of integers")
    instrument_ids = list(set(instrument_ids))
    instruments = session.scalars(
        Instrument.select(session.user_or_token).where(
            Instrument.id.in_(instrument_ids)
        )
    ).all()
    if len(instruments) != len(instrument_ids):
        raise ValueError(f"One or more instruments not found: {instrument_ids}")
    for instrument in instruments:
        if instrument.name.lower() not in TNS_INSTRUMENT_IDS:
            raise ValueError(
                f"Instrument {instrument.name} not supported for TNS reporting"
            )
    tnsrobot.instruments = instruments

    # TNS AUTO-REPORTING STREAMS: ADD/MODIFY/DELETE
    if len(stream_ids) > 0:
        try:
            stream_ids = [int(x) for x in stream_ids]
            if isinstance(stream_ids, str):
                stream_ids = [int(x) for x in stream_ids.split(",")]
            else:
                stream_ids = [int(x) for x in stream_ids]
        except ValueError:
            raise ValueError("stream_ids must be a comma-separated list of integers")
        stream_ids = list(set(stream_ids))
        streams = session.scalars(
            Stream.select(session.user_or_token).where(Stream.id.in_(stream_ids))
        ).all()
        if len(streams) != len(stream_ids):
            raise ValueError(f"One or more streams not found: {stream_ids}")
        tnsrobot.streams = streams

    session.commit()
    return tnsrobot.id


def update_tns_robot(
    data,
    existing_id,
    instrument_ids,
    stream_ids,
    session,
):
    """Update a TNSRobot and its owner TNSRobotGroups

    Parameters
    ----------
    data : dict
        Dictionary containing the TNSRobot data passed in the PUT request, won't update missing or empty fields
    existing_id : int
        The ID of the TNSRobot to update
    instrument_ids : list of int
        List of instrument IDs that can be used for TNS reporting
    stream_ids : list of int
        List of stream IDs that can be used for TNS reporting
    session : `baselayer.app.models.Session`
        Database session

    Returns
    -------
    id : int
        The ID of the updated TNSRobot
    """

    tnsrobot = session.scalar(
        TNSRobot.select(session.user_or_token, mode="update").where(
            TNSRobot.id == existing_id
        )
    )
    if tnsrobot is None:
        raise ValueError(
            f"No TNS robot with specified ID: {existing_id}, or you are not authorized to update it"
        )

    if "bot_name" in data:
        tnsrobot.bot_name = data["bot_name"]
    if "bot_id" in data:
        tnsrobot.bot_id = data["bot_id"]
    if "source_group_id" in data:
        tnsrobot.source_group_id = data["source_group_id"]
    if "_altdata" in data:
        tnsrobot._altdata = data["_altdata"]
    if "acknowledgments" in data and data.get("acknowledgments", None) not in [
        None,
        "",
    ]:
        tnsrobot.acknowledgments = data["acknowledgments"]
    report_existing = data.get("report_existing", None)
    if str(report_existing).lower().strip() in ["true", "t", "1"]:
        report_existing = True
    elif str(report_existing).lower().strip() in ["false", "f", "0"]:
        report_existing = False
    if report_existing is not None:
        tnsrobot.report_existing = report_existing

    testing = data.get("testing", None)
    if str(testing).lower().strip() in ["true", "t", "1"]:
        testing = True
    elif str(testing).lower().strip() in ["false", "f", "0"]:
        testing = False
    if testing is not None:
        tnsrobot.testing = testing

    tnsrobot.photometry_options = validate_photometry_options(
        data.get("photometry_options", {}), tnsrobot.photometry_options
    )

    # TNS AUTO-REPORTING INSTRUMENTS: ADD/MODIFY/DELETE
    if len(instrument_ids) > 0:
        try:
            instrument_ids = [int(x) for x in instrument_ids]
            if isinstance(instrument_ids, str):
                instrument_ids = [int(x) for x in instrument_ids.split(",")]
            else:
                instrument_ids = [int(x) for x in instrument_ids]
        except ValueError:
            raise ValueError(
                "instrument_ids must be a comma-separated list of integers"
            )
        instrument_ids = list(set(instrument_ids))
        instruments = session.scalars(
            Instrument.select(session.user_or_token).where(
                Instrument.id.in_(instrument_ids)
            )
        ).all()
        if len(instruments) != len(instrument_ids):
            raise ValueError(f"One or more instruments not found: {instrument_ids}")
        for instrument in instruments:
            if instrument.name.lower() not in TNS_INSTRUMENT_IDS:
                raise ValueError(
                    f"Instrument {instrument.name} not supported for TNS reporting"
                )
        tnsrobot.instruments = instruments

    # TNS AUTO-REPORTING STREAMS: ADD/MODIFY/DELETE
    if len(stream_ids) > 0:
        try:
            stream_ids = [int(x) for x in stream_ids]
            if isinstance(stream_ids, str):
                stream_ids = [int(x) for x in stream_ids.split(",")]
            else:
                stream_ids = [int(x) for x in stream_ids]
        except ValueError:
            raise ValueError("stream_ids must be a comma-separated list of integers")
        stream_ids = list(set(stream_ids))
        streams = session.scalars(
            Stream.select(session.user_or_token).where(Stream.id.in_(stream_ids))
        ).all()
        if len(streams) != len(stream_ids):
            raise ValueError(f"One or more streams not found: {stream_ids}")
        tnsrobot.streams = streams

    session.commit()
    return tnsrobot.id


class TNSRobotHandler(BaseHandler):
    @permissions(["Manage TNS robots"])
    def put(self, existing_id=None):
        """
        ---
        summary: Create or update a TNS robot
        description: Post or update a TNS robot
        tags:
          - tns robot
        requestBody:
          content:
            application/json:
              schema: TNSRobotNoID
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
                              description: New TNS robot ID
        """
        try:
            data = self.get_json()

            if "_altdata" in data:
                if isinstance(data["_altdata"], dict):
                    data["_altdata"] = json.dumps(data["_altdata"])
                data["_altdata"] = data["_altdata"].replace("'", '"')

            owner_group_ids = data.pop("owner_group_ids", [])

            if isinstance(owner_group_ids, str | int):
                owner_group_ids = [
                    int(owner_group_id)
                    for owner_group_id in str(owner_group_ids).split(",")
                ]
            elif isinstance(owner_group_ids, list):
                owner_group_ids = [
                    int(owner_group_id) for owner_group_id in owner_group_ids
                ]
            if len(owner_group_ids) > 0:
                owner_group_ids = list(set(owner_group_ids))

            instrument_ids = data.pop("instrument_ids", [])
            stream_ids = data.pop("stream_ids", [])

            with self.Session() as session:
                # CHECK FOR EXISTING TNS ROBOT
                if existing_id is None:
                    existing_tnsrobot = session.scalar(
                        TNSRobot.select(session.user_or_token).where(
                            TNSRobot.bot_id == data["bot_id"],
                            TNSRobot.bot_name == data["bot_name"],
                            TNSRobot.source_group_id == data["source_group_id"],
                            TNSRobot.groups.any(
                                TNSRobotGroup.group_id.in_(owner_group_ids)
                            ),
                        )
                    )
                    # if there is already a TNS robot with the same bot_id, bot_name, and source_group_id, we return an error
                    if existing_tnsrobot is not None:
                        return self.error(
                            f"A TNS robot with the same bot_id, bot_name, and source_group_id already exists with id: {existing_tnsrobot.id} (owned by group_ids: {owner_group_ids}), specify the ID to update it"
                        )

                if not existing_id:
                    try:
                        # OWNER GROUP: VERIFY THAT IT EXISTS
                        owner_groups = session.scalars(
                            Group.select(session.user_or_token).where(
                                Group.id.in_(owner_group_ids)
                            )
                        ).all()
                        if len(owner_groups) != len(owner_group_ids):
                            return self.error(
                                f"One or more owner groups not found: {owner_group_ids}"
                            )

                        robot_id = create_tns_robot(
                            data,
                            owner_group_ids,
                            instrument_ids,
                            stream_ids,
                            session,
                        )
                        self.push(
                            action="skyportal/REFRESH_TNSROBOTS",
                        )
                        return self.success(data={"id": robot_id})
                    except Exception as e:
                        return self.error(f"Failed to create TNS robot: {e}")
                else:
                    try:
                        robot_id = update_tns_robot(
                            data,
                            existing_id,
                            instrument_ids,
                            stream_ids,
                            session,
                        )
                        self.push(
                            action="skyportal/REFRESH_TNSROBOTS",
                        )
                        return self.success(data={"id": robot_id})
                    except Exception as e:
                        return self.error(f"Failed to update TNS robot: {e}")
        except Exception as e:
            return self.error(f"Failed to create/update TNS robot: {e}")

    @auth_or_token
    def get(self, tnsrobot_id=None):
        """
        ---
        summary: Retrieve a TNS robot
        description: Retrieve a TNS robot
        tags:
          - tns robot
        parameters:
          - in: path
            name: tnsrobot_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: SingleTNSRobot
          400:
            content:
              application/json:
                schema: Error
        """

        with self.Session() as session:
            stmt = TNSRobot.select(session.user_or_token, mode="read").options(
                joinedload(TNSRobot.groups),
                joinedload(TNSRobot.coauthors),
                joinedload(TNSRobot.instruments),
                joinedload(TNSRobot.streams),
            )
            if tnsrobot_id is not None:
                tnsrobot = session.scalar(stmt.where(TNSRobot.id == tnsrobot_id))
                if tnsrobot is None:
                    return self.error(f"No TNS robot with ID {tnsrobot_id}")
                # for each of the groups, we load the users, and grab the list of owner groups
                owner_group_ids = []
                for group in tnsrobot.groups:
                    if group.owner:
                        owner_group_ids.append(group.group_id)
                    group.autoreporters  # we just need to load the users by accessing the attribute
                tnsrobot.owner_group_ids = owner_group_ids
                return self.success(data=tnsrobot)
            else:
                tnsrobots = session.scalars(stmt).unique().all()
                # for each of the groups, we load the users
                for tnsrobot in tnsrobots:
                    owner_group_ids = []
                    for group in tnsrobot.groups:
                        if group.owner:
                            owner_group_ids.append(group.group_id)
                        group.autoreporters  # we just need to load the users by accessing the attribute
                    tnsrobot.owner_group_ids = owner_group_ids
                return self.success(data=tnsrobots)

    @permissions(["Manage TNS robots"])
    def delete(self, tnsrobot_id):
        """
        ---
        summary: Delete a TNS robot
        description: Delete a TNS robot
        tags:
          - tns robot
        parameters:
          - in: path
            name: tnsrobot_id
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
            tnsrobot = session.scalar(
                TNSRobot.select(session.user_or_token, mode="delete").where(
                    TNSRobot.id == tnsrobot_id
                )
            )
            if tnsrobot is None:
                return self.error(
                    f"No TNS robot with ID {tnsrobot_id}, or you are not authorized to delete it"
                )
            session.delete(tnsrobot)
            session.commit()
            self.push(
                action="skyportal/REFRESH_TNSROBOTS",
            )
            return self.success()
