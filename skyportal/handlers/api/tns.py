import asyncio
import json
import tempfile
import urllib

import arrow
import astropy.units as u
import requests
from astropy.time import Time, TimeDelta
from marshmallow.exceptions import ValidationError
import sqlalchemy as sa
from sqlalchemy.orm import scoped_session, sessionmaker, joinedload
from tornado.ioloop import IOLoop

from baselayer.app.access import auth_or_token, permissions
from baselayer.app.env import load_env
from baselayer.app.model_util import recursive_to_dict
from baselayer.log import make_log

from ...models import (
    Group,
    Obj,
    Spectrum,
    SpectrumObserver,
    SpectrumReducer,
    TNSRobot,
    TNSRobotCoauthor,
    TNSRobotGroup,
    TNSRobotGroupAutoreporter,
    TNSRobotSubmission,
    Instrument,
    Stream,
    User,
    GroupUser,
)
from ...utils.tns import get_IAUname, get_tns, TNS_INSTRUMENT_IDS
from ..base import BaseHandler

_, cfg = load_env()

Session = scoped_session(sessionmaker())

TNS_URL = cfg['app.tns.endpoint']
upload_url = urllib.parse.urljoin(TNS_URL, 'api/file-upload')
report_url = urllib.parse.urljoin(TNS_URL, 'api/bulk-report')

log = make_log('api/tns')

PHOTOMETRY_OPTIONS = {
    'first_and_last_detections': bool,
    'autoreport_allow_archival': bool,
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
        raise ValueError('photometry_options must be a dictionary')

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
            raise ValueError(f'Invalid photometry option: {key}')
        if not isinstance(value, PHOTOMETRY_OPTIONS[key]):
            raise ValueError(f'Invalid value for photometry option {key}: {value}')

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
    report_existing = data.get('report_existing', False)
    if str(report_existing).lower().strip() in ['true', 't', '1']:
        report_existing = True
    else:
        report_existing = False
    data['report_existing'] = report_existing

    # True if not specified
    testing = data.get('testing', True)
    if str(testing).lower().strip() in ['false', 'f', '0']:
        testing = False
    else:
        testing = True
    data['testing'] = testing

    data['photometry_options'] = validate_photometry_options(
        data.get('photometry_options', {})
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
        raise ValueError('At least one instrument must be specified for TNS reporting')

    try:
        instrument_ids = [int(x) for x in instrument_ids]
        if isinstance(instrument_ids, str):
            instrument_ids = [int(x) for x in instrument_ids.split(",")]
        else:
            instrument_ids = [int(x) for x in instrument_ids]
    except ValueError:
        raise ValueError('instrument_ids must be a comma-separated list of integers')
    instrument_ids = list(set(instrument_ids))
    instruments = session.scalars(
        Instrument.select(session.user_or_token).where(
            Instrument.id.in_(instrument_ids)
        )
    ).all()
    if len(instruments) != len(instrument_ids):
        raise ValueError(f'One or more instruments not found: {instrument_ids}')
    for instrument in instruments:
        if instrument.name.lower() not in TNS_INSTRUMENT_IDS:
            raise ValueError(
                f'Instrument {instrument.name} not supported for TNS reporting'
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
            raise ValueError('stream_ids must be a comma-separated list of integers')
        stream_ids = list(set(stream_ids))
        streams = session.scalars(
            Stream.select(session.user_or_token).where(Stream.id.in_(stream_ids))
        ).all()
        if len(streams) != len(stream_ids):
            raise ValueError(f'One or more streams not found: {stream_ids}')
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
    None
    """

    tnsrobot = session.scalar(
        TNSRobot.select(session.user_or_token, mode="update").where(
            TNSRobot.id == existing_id
        )
    )
    if tnsrobot is None:
        raise ValueError(
            f'No TNS robot with specified ID: {existing_id}, or you are not authorized to update it'
        )

    if 'bot_name' in data:
        tnsrobot.bot_name = data['bot_name']
    if 'bot_id' in data:
        tnsrobot.bot_id = data['bot_id']
    if 'source_group_id' in data:
        tnsrobot.source_group_id = data['source_group_id']
    if '_altdata' in data:
        tnsrobot._altdata = data['_altdata']
    if 'acknowledgments' in data and data.get('acknowledgments', None) not in [
        None,
        '',
    ]:
        tnsrobot.acknowledgments = data['acknowledgments']
    report_existing = data.get('report_existing', None)
    if str(report_existing).lower().strip() in ['true', 't', '1']:
        report_existing = True
    elif str(report_existing).lower().strip() in ['false', 'f', '0']:
        report_existing = False
    if report_existing is not None:
        tnsrobot.report_existing = report_existing

    testing = data.get('testing', None)
    if str(testing).lower().strip() in ['true', 't', '1']:
        testing = True
    elif str(testing).lower().strip() in ['false', 'f', '0']:
        testing = False
    if testing is not None:
        tnsrobot.testing = testing

    tnsrobot.photometry_options = validate_photometry_options(
        data.get('photometry_options', {}), tnsrobot.photometry_options
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
                'instrument_ids must be a comma-separated list of integers'
            )
        instrument_ids = list(set(instrument_ids))
        instruments = session.scalars(
            Instrument.select(session.user_or_token).where(
                Instrument.id.in_(instrument_ids)
            )
        ).all()
        if len(instruments) != len(instrument_ids):
            raise ValueError(f'One or more instruments not found: {instrument_ids}')
        for instrument in instruments:
            if instrument.name.lower() not in TNS_INSTRUMENT_IDS:
                raise ValueError(
                    f'Instrument {instrument.name} not supported for TNS reporting'
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
            raise ValueError('stream_ids must be a comma-separated list of integers')
        stream_ids = list(set(stream_ids))
        streams = session.scalars(
            Stream.select(session.user_or_token).where(Stream.id.in_(stream_ids))
        ).all()
        if len(streams) != len(stream_ids):
            raise ValueError(f'One or more streams not found: {stream_ids}')
        tnsrobot.streams = streams

    session.commit()
    return tnsrobot.id


class TNSRobotHandler(BaseHandler):
    @permissions(['Manage TNS robots'])
    def put(self, existing_id=None):
        """
        ---
        description: Post or update a TNS robot
        tags:
          - tnsrobots
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

            if '_altdata' in data:
                if isinstance(data['_altdata'], dict):
                    data['_altdata'] = json.dumps(data['_altdata'])
                data['_altdata'] = data['_altdata'].replace("'", '"')

            owner_group_ids = data.pop('owner_group_ids', [])

            if isinstance(owner_group_ids, str) or isinstance(owner_group_ids, int):
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

            instrument_ids = data.pop('instrument_ids', [])
            stream_ids = data.pop('stream_ids', [])

            with self.Session() as session:
                # CHECK FOR EXISTING TNS ROBOT
                if existing_id is None:
                    existing_tnsrobot = session.scalar(
                        TNSRobot.select(session.user_or_token).where(
                            TNSRobot.bot_id == data['bot_id'],
                            TNSRobot.bot_name == data['bot_name'],
                            TNSRobot.source_group_id == data['source_group_id'],
                            TNSRobot.groups.any(
                                TNSRobotGroup.group_id.in_(owner_group_ids)
                            ),
                        )
                    )
                    # if there is already a TNS robot with the same bot_id, bot_name, and source_group_id, we return an error
                    if existing_tnsrobot is not None:
                        return self.error(
                            f'A TNS robot with the same bot_id, bot_name, and source_group_id already exists with id: {existing_tnsrobot.id} (owned by group_ids: {owner_group_ids}), specify the ID to update it'
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
                                f'One or more owner groups not found: {owner_group_ids}'
                            )

                        id = create_tns_robot(
                            data,
                            owner_group_ids,
                            instrument_ids,
                            stream_ids,
                            session,
                        )
                        self.push(
                            action='skyportal/REFRESH_TNSROBOTS',
                        )
                        return self.success(data={"id": id})
                    except Exception as e:
                        return self.error(f'Failed to create TNS robot: {e}')
                else:
                    try:
                        id = update_tns_robot(
                            data,
                            existing_id,
                            instrument_ids,
                            stream_ids,
                            session,
                        )
                        self.push(
                            action='skyportal/REFRESH_TNSROBOTS',
                        )
                        return self.success(data={"id": id})
                    except Exception as e:
                        return self.error(f'Failed to update TNS robot: {e}')
        except Exception as e:
            return self.error(f'Failed to create/update TNS robot: {e}')

    @auth_or_token
    def get(self, tnsrobot_id=None):
        """
        ---
        description: Retrieve a TNS robot
        tags:
          - tnsrobots
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
                    return self.error(f'No TNS robot with ID {tnsrobot_id}')
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

    @permissions(['Manage TNS robots'])
    def delete(self, tnsrobot_id):
        """
        ---
        description: Delete a TNS robot
        tags:
          - tnsrobots
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
                    f'No TNS robot with ID {tnsrobot_id}, or you are not authorized to delete it'
                )
            session.delete(tnsrobot)
            session.commit()
            self.push(
                action='skyportal/REFRESH_TNSROBOTS',
            )
            return self.success()


class TNSRobotCoauthorHandler(BaseHandler):
    @permissions(['Manage TNS robots'])
    def post(self, tnsrobot_id, user_id=None):
        """
        ---
        description: Add a coauthor to a TNS robot
        tags:
            - tnsrobots
        parameters:
            - in: path
              name: tnsrobot_id
              required: true
              schema:
                type: integer
              description: ID of the TNS robot
            - in: path
              name: user_id
              required: false
              schema:
                type: integer
              description: ID of the user to add as a coauthor
        requestBody:
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            user_id:
                                type: integer
                                description: ID of the user to add as a coauthor, if not specified in the URL
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
        if user_id is None:
            user_id = self.get_json().get('user_id')
        if user_id is None:
            return self.error(
                'You must specify a coauthor_id when adding a coauthor to a TNSRobot'
            )
        with self.Session() as session:
            # verify that the user has access to the tnsrobot
            tnsrobot = session.scalar(
                TNSRobot.select(session.user_or_token).where(TNSRobot.id == tnsrobot_id)
            )
            if tnsrobot is None:
                return self.error(f'No TNSRobot with ID {tnsrobot_id}')

            # verify that the user has access to the coauthor
            user = session.scalar(
                User.select(session.user_or_token).where(User.id == user_id)
            )
            if user is None:
                return self.error(f'No User with ID {user_id}')

            # if the coauthor already exists, return an error
            if user_id in [u.user_id for u in tnsrobot.coauthors]:
                return self.error(
                    f'User {user_id} is already a coauthor of TNSRobot {tnsrobot_id}'
                )

            # if the user has no affiliations, return an error (autoreporting would not work)
            if len(user.affiliations) == 0:
                return self.error(
                    f'User {user_id} has no affiliation(s), required to be a coauthor of TNSRobot {tnsrobot_id}. User must add one in their profile.'
                )

            # if the user is a bot, throw an error
            if user.is_bot:
                return self.error(
                    f'User {user_id} is a bot and cannot be a coauthor of TNSRobot {tnsrobot_id}'
                )

            # add the coauthor
            coauthor = TNSRobotCoauthor(tnsrobot_id=tnsrobot_id, user_id=user_id)
            session.add(coauthor)
            session.commit()
            self.push(
                action='skyportal/REFRESH_TNSROBOTS',
            )
            return self.success(data={"id": coauthor.id})

    @permissions(['Manage TNS robots'])
    def delete(self, tnsrobot_id, user_id):
        """
        ---
        description: Remove a coauthor from a TNS robot
        tags:
            - tnsrobots
        parameters:
            - in: path
              name: tnsrobot_id
              required: true
              schema:
                type: integer
              description: ID of the TNS robot
            - in: path
              name: user_id
              required: true
              schema:
                type: integer
              description: ID of the user to remove as a coauthor
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

        # the DELETE handler is used to remove a coauthor from a TNSRobot
        with self.Session() as session:
            # verify that the user has access to the tnsrobot
            tnsrobot = session.scalar(
                TNSRobot.select(session.user_or_token).where(TNSRobot.id == tnsrobot_id)
            )
            if tnsrobot is None:
                return self.error(f'No TNSRobot with ID {tnsrobot_id}, or unaccessible')

            # verify that the coauthor exists and/or can be deleted
            coauthor = session.scalar(
                TNSRobotCoauthor.select(session.user_or_token, mode="delete").where(
                    TNSRobotCoauthor.user_id == user_id,
                    TNSRobotCoauthor.tnsrobot_id == tnsrobot_id,
                )
            )
            if coauthor is None:
                return self.error(
                    f'No TNSRobotCoauthor with userID {user_id}, or unable to delete it'
                )

            session.delete(coauthor)
            session.commit()
            self.push(
                action='skyportal/REFRESH_TNSROBOTS',
            )
            return self.success()


class TNSRobotGroupHandler(BaseHandler):
    @permissions(['Manage TNS robots'])
    def put(self, tnsrobot_id, group_id=None):
        """
        ---
        description: Add or edit a group for a TNS robot
        tags:
            - tnsrobots
        parameters:
            - in: path
              name: tnsrobot_id
              required: true
              schema:
                type: integer
              description: ID of the TNS robot
            - in: path
              name: group_id
              required: false
              schema:
                type: integer
              description: ID of the group to edit
        requestBody:
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            group_id:
                                type: integer
                                description: ID of the group to add
                            auto_report:
                                type: boolean
                                description: Whether to automatically report to this group
                            owner:
                                type: boolean
                                description: Whether this group is the owner of the TNS robot
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
        # the PUT handler is used to add or edit a group
        data = self.get_json()
        auto_report = data.get('auto_report', None)
        auto_report_allow_bots = data.get('auto_report_allow_bots', None)
        owner = data.get('owner', None)
        if group_id is None:
            group_id = int(data.get('group_id', None))

        try:
            group_id = int(group_id)
        except ValueError:
            return self.error(f'Invalid group_id: {group_id}, must be an integer')

        if auto_report is not None:
            # try to convert the auto_report to a boolean
            if str(auto_report) in ['True', 'true', '1', 't']:
                auto_report = True
            elif str(auto_report) in ['False', 'false', '0', 'f']:
                auto_report = False
            else:
                return self.error(f'Invalid auto_report value: {auto_report}')

        if auto_report_allow_bots is not None:
            # try to convert the auto_report_allow_bots to a boolean
            if str(auto_report_allow_bots) in ['True', 'true', '1', 't']:
                auto_report_allow_bots = True
            elif str(auto_report_allow_bots) in ['False', 'false', '0', 'f']:
                auto_report_allow_bots = False
            else:
                return self.error(
                    f'Invalid auto_report_allow_bots value: {auto_report_allow_bots}'
                )

        if owner is not None:
            # try to convert the owner to a boolean
            if str(owner) in ['True', 'true', '1', 't']:
                owner = True
            elif str(owner) in ['False', 'false', '0', 'f']:
                owner = False
            else:
                return self.error(f'Invalid owner value: {owner}')

        with self.Session() as session:
            # verify that the user has access to the tnsrobot
            tnsrobot = session.scalar(
                TNSRobot.select(session.user_or_token).where(TNSRobot.id == tnsrobot_id)
            )
            if tnsrobot is None:
                return self.error(
                    f'No TNSRobot with ID {tnsrobot_id}, or unnaccessible'
                )

            if group_id is None:
                return self.error(
                    'You must specify a group_id when giving or editing the access to a TNSRobot for a group'
                )

            # verify that this group is accessible by the user
            if not self.current_user.is_system_admin and group_id not in [
                g.id for g in self.current_user.accessible_groups
            ]:
                return self.error(
                    f'Group {group_id} is not accessible by the current user'
                )

            # check if the group already has access to the tnsrobot
            tnsrobot_group = session.scalar(
                TNSRobotGroup.select(session.user_or_token, mode="update").where(
                    TNSRobotGroup.tnsrobot_id == tnsrobot_id,
                    TNSRobotGroup.group_id == group_id,
                )
            )

            if tnsrobot_group is not None:
                # the user wants to edit the tnsrobot_group
                if (
                    auto_report is None
                    and owner is None
                    and auto_report_allow_bots is None
                ):
                    return self.error(
                        'You must specify auto_report, owner and/or auto_report_allow_bots when editing a TNSRobotGroup'
                    )

                if (
                    auto_report is not None
                    and auto_report != tnsrobot_group.auto_report
                ):
                    tnsrobot_group.auto_report = auto_report
                if (
                    auto_report_allow_bots is not None
                    and auto_report_allow_bots != tnsrobot_group.auto_report_allow_bots
                ):
                    # if the user is trying to set auto_report_allow_bots to False,
                    # we need to verify that none of the existing autoreporter are bots
                    if auto_report_allow_bots is False:
                        autoreporters_group_users = session.scalars(
                            sa.select(GroupUser).where(
                                GroupUser.id.in_(
                                    [
                                        r.group_user_id
                                        for r in tnsrobot_group.autoreporters
                                    ]
                                )
                            )
                        )
                        if any(gu.user.is_bot for gu in autoreporters_group_users):
                            return self.error(
                                'Cannot set auto_report_allow_bots to False when one or more autoreporters are bots. Remove the bots from the autoreporters first.'
                            )
                    tnsrobot_group.auto_report_allow_bots = auto_report_allow_bots

                if owner is not None and owner != tnsrobot_group.owner:
                    # here we want to be careful not to remove the last owner
                    # so we check if the tnsrobot has any other groups that are owners.
                    # If this is the only one, we return an error
                    owners = []
                    for g in tnsrobot_group.tnsrobot.groups:
                        if g.owner is True:
                            owners.append(g.group_id)
                    if len(owners) == 1 and owners[0] == group_id:
                        return self.error(
                            'Cannot remove ownership from the only tnsrobot_group owning this robot, add another group as an owner first.'
                        )
                    tnsrobot_group.owner = owner

                session.commit()
                self.push(
                    action='skyportal/REFRESH_TNSROBOTS',
                )
                return self.success(data=tnsrobot_group)
            else:
                # verify that we don't actually have a tnsrobot_group with this group and tnsrobot
                # but the current user simply does not have access to it
                existing_tnsrobot_group = session.scalar(
                    sa.select(TNSRobotGroup).where(
                        TNSRobotGroup.tnsrobot_id == tnsrobot_id,
                        TNSRobotGroup.group_id == group_id,
                    )
                )
                if existing_tnsrobot_group is not None:
                    return self.error(
                        f'Group {group_id} already has access to TNSRobot {tnsrobot_id}, but user is not allowed to edit it'
                    )

                # create the new tnsrobot_group
                tnsrobot_group = TNSRobotGroup(
                    tnsrobot_id=tnsrobot_id,
                    group_id=group_id,
                    auto_report=bool(auto_report),
                    auto_report_allow_bots=bool(auto_report_allow_bots),
                    owner=bool(owner),
                )

                session.add(tnsrobot_group)
                session.commit()
                self.push(
                    action='skyportal/REFRESH_TNSROBOTS',
                )
                return self.success(data={"id": tnsrobot_group.id})

    @permissions(['Manage TNS robots'])
    def delete(self, tnsrobot_id, group_id):
        """
        ---
        description: Delete a group from a TNSRobot
        parameters:
            - in: path
              name: tnsrobot_id
              required: true
              schema:
                type: string
              description: The ID of the TNSRobot
            - in: path
              name: group_id
              required: true
              schema:
                type: string
              description: The ID of the group to remove from the TNSRobot
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
        # the DELETE handler is used to remove a group from a TNSRobot
        with self.Session() as session:
            # verify that the user has access to the tnsrobot
            tnsrobot = session.scalar(
                TNSRobot.select(session.user_or_token).where(TNSRobot.id == tnsrobot_id)
            )
            if tnsrobot is None:
                return self.error(
                    f'No TNSRobot with ID {tnsrobot_id}, or unnaccessible'
                )

            if group_id is None:
                return self.error(
                    'You must specify a group_id when giving or editing  the access to a TNSRobot for a group'
                )

            # verify that this group is accessible by the user
            if not self.current_user.is_system_admin and group_id not in [
                g.id for g in self.current_user.accessible_groups
            ]:
                return self.error(
                    f'Group {group_id} is not accessible by the current user'
                )

            # check if the group already has access to the tnsrobot
            tnsrobot_group = session.scalar(
                TNSRobotGroup.select(session.user_or_token, mode="delete").where(
                    TNSRobotGroup.tnsrobot_id == tnsrobot_id,
                    TNSRobotGroup.group_id == group_id,
                )
            )

            if tnsrobot_group is None:
                return self.error(
                    f'Group {group_id} does not have access to TNSRobot {tnsrobot_id}, or user is not allowed to remove it'
                )

            # here we want to be careful not to remove the last owner
            owners_nb = 0
            for g in tnsrobot_group.tnsrobot.groups:
                if g.owner is True:
                    owners_nb += 1
            if owners_nb == 1 and tnsrobot_group.owner is True:
                return self.error(
                    'Cannot delete the only tnsrobot_group owning this robot, add another group as an owner first.'
                )

            session.delete(tnsrobot_group)
            session.commit()
            self.push(
                action='skyportal/REFRESH_TNSROBOTS',
            )
            return self.success()


class TNSRobotGroupAutoreporterHandler(BaseHandler):
    @permissions(['Manage TNS robots'])
    def post(self, tnsrobot_id, group_id, user_id=None):
        """
        ---
        description: Add autoreporter(s) to a TNSRobotGroup
        parameters:
            - in: path
              name: tnsrobot_id
              required: true
              schema:
                type: string
              description: The ID of the TNSRobot
            - in: path
              name: group_id
              required: true
              schema:
                type: string
              description: The ID of the group to add autoreporter(s) to
            - in: query
              name: user_id
              required: false
              schema:
                type: string
              description: The ID of the user to add as an autoreporter
        requestBody:
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            user_ids:
                                type: array
                                items:
                                    type: string
                                description: |
                                    An array of user IDs to add as autoreporters.
                                    If a string is provided, it will be split by commas.
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

        if user_id is None:
            user_id = self.get_json().get('user_id', None)

        user_ids = [user_id]

        if "user_ids" in self.get_json():
            user_ids = self.get_json()["user_ids"]
            if isinstance(user_ids, str) or isinstance(user_ids, int):
                user_ids = [int(user_id) for user_id in str(user_ids).split(",")]
            elif isinstance(user_ids, list):
                user_ids = [int(user_id) for user_id in user_ids]

        if len(user_ids) == 0:
            return self.error(
                'You must specify at least one user_id when adding autoreporter(s) for a TNSRobotGroup'
            )

        with self.Session() as session:
            # verify that the user has access to the tnsrobot
            tnsrobot = session.scalar(
                TNSRobot.select(session.user_or_token).where(TNSRobot.id == tnsrobot_id)
            )
            if tnsrobot is None:
                return self.error(f'No TNSRobot with ID {tnsrobot_id}, or unaccessible')

            # verify that the user has access to the group
            if not self.current_user.is_system_admin and group_id not in [
                g.id for g in self.current_user.accessible_groups
            ]:
                return self.error(
                    f'Group {group_id} is not accessible by the current user'
                )

            # check if the group already has access to the tnsrobot
            tnsrobot_group = session.scalar(
                TNSRobotGroup.select(session.user_or_token).where(
                    TNSRobotGroup.tnsrobot_id == tnsrobot_id,
                    TNSRobotGroup.group_id == group_id,
                )
            )

            if tnsrobot_group is None:
                return self.error(
                    f'Group {group_id} does not have access to TNSRobot {tnsrobot_id}, cannot add autoreporter'
                )

            autoreporters = []
            for user_id in user_ids:
                # verify that the user has access to the user_id
                user = session.scalar(
                    User.select(session.user_or_token).where(User.id == user_id)
                )
                if user is None:
                    return self.error(f'No user with ID {user_id}, or unaccessible')

                # verify that the user specified is a group user of the group
                group_user = session.scalar(
                    GroupUser.select(session.user_or_token).where(
                        GroupUser.group_id == group_id, GroupUser.user_id == user_id
                    )
                )

                if group_user is None:
                    return self.error(
                        f'User {user_id} is not a member of group {group_id}'
                    )

                # verify that the user isn't already an autoreporter
                existing_autoreporter = session.scalar(
                    TNSRobotGroupAutoreporter.select(session.user_or_token).where(
                        TNSRobotGroupAutoreporter.tnsrobot_group_id
                        == tnsrobot_group.id,
                        TNSRobotGroupAutoreporter.group_user_id == group_user.id,
                    )
                )

                if existing_autoreporter is not None:
                    return self.error(
                        f'User {user_id} is already an autoreporter for TNSRobot {tnsrobot_id}'
                    )

                # if the user has no affiliations, return an error (autoreporting would not work)
                if len(user.affiliations) == 0:
                    return self.error(
                        f'User {user_id} has no affiliation(s), required to be an autoreporter of TNSRobot {tnsrobot_id}. User must add one in their profile.'
                    )

                # if the user is a bot user and the tnsrobot_group did not allow bot users, return an error
                if user.is_bot and not tnsrobot_group.auto_report_allow_bots:
                    return self.error(
                        f'User {user_id} is a bot user, which is not allowed to be an autoreporter for TNSRobot {tnsrobot_id}'
                    )

                autoreporter = TNSRobotGroupAutoreporter(
                    tnsrobot_group_id=tnsrobot_group.id, group_user_id=group_user.id
                )
                autoreporters.append(autoreporter)

            for a in autoreporters:
                session.add(a)
            session.commit()
            self.push(
                action='skyportal/REFRESH_TNSROBOTS',
            )
            return self.success(data={'ids': [a.id for a in autoreporters]})

    @permissions(['Manage TNS robots'])
    def delete(self, tnsrobot_id, group_id, user_id):
        """
        ---
        description: Delete an autoreporter from a TNSRobotGroup
        tags:
            - tnsrobot_groups
        parameters:
            - in: path
              name: tnsrobot_id
              required: true
              schema:
                type: integer
              description: The ID of the TNSRobot
            - in: path
              name: group_id
              required: true
              schema:
                type: integer
              description: The ID of the Group
            - in: path
              name: user_id
              required: false
              schema:
                type: integer
              description: The ID of the User to remove as an autoreporter. If not provided, the user_id will be taken from the request body.
        requestBody:
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            user_id:
                                type: integer
                                description: The ID of the User to remove as an autoreporter
                            user_ids:
                                type: array
                                items:
                                    type: integer
                                description: The IDs of the Users to remove as autoreporters, overrides user_id
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

        if user_id is None:
            user_id = self.get_json().get('user_id', None)

        user_ids = [user_id]

        if "user_ids" in self.get_json():
            user_ids = self.get_json()["user_ids"]
            if isinstance(user_ids, str) or isinstance(user_ids, int):
                user_ids = [int(user_id) for user_id in str(user_ids).split(",")]
            elif isinstance(user_ids, list):
                user_ids = [int(user_id) for user_id in user_ids]

        if len(user_ids) == 0:
            return self.error(
                'You must specify at least one user_id when removing autoreporter(s) from a TNSRobotGroup'
            )

        with self.Session() as session:
            # verify that the user has access to the tnsrobot
            tnsrobot = session.scalar(
                TNSRobot.select(session.user_or_token).where(TNSRobot.id == tnsrobot_id)
            )
            if tnsrobot is None:
                return self.error(f'No TNSRobot with ID {tnsrobot_id}, or unaccessible')

            # verify that the user has access to the group
            if not self.current_user.is_system_admin and group_id not in [
                g.id for g in self.current_user.accessible_groups
            ]:
                return self.error(
                    f'Group {group_id} is not accessible by the current user'
                )

            # check if the group already has access to the tnsrobot
            tnsrobot_group = session.scalar(
                TNSRobotGroup.select(session.user_or_token).where(
                    TNSRobotGroup.tnsrobot_id == tnsrobot_id,
                    TNSRobotGroup.group_id == group_id,
                )
            )

            if tnsrobot_group is None:
                return self.error(
                    f'Group {group_id} does not have access to TNSRobot {tnsrobot_id}, cannot remove autoreporter'
                )

            autoreporters = []
            for user_id in user_ids:
                # verify that the user has access to the user_id
                user = session.scalar(
                    User.select(session.user_or_token).where(User.id == user_id)
                )
                if user is None:
                    return self.error(f'No user with ID {user_id}, or unaccessible')

                # verify that the user specified is a group user of the group
                group_user = session.scalar(
                    GroupUser.select(session.user_or_token).where(
                        GroupUser.group_id == group_id, GroupUser.user_id == user_id
                    )
                )

                if group_user is None:
                    return self.error(
                        f'User {user_id} is not a member of group {group_id}'
                    )

                # verify that the user is an autoreporter
                autoreporter = session.scalar(
                    TNSRobotGroupAutoreporter.select(session.user_or_token).where(
                        TNSRobotGroupAutoreporter.tnsrobot_group_id
                        == tnsrobot_group.id,
                        TNSRobotGroupAutoreporter.group_user_id == group_user.id,
                    )
                )

                if autoreporter is None:
                    return self.error(
                        f'User {user_id} is not an autoreporter for TNSRobot {tnsrobot_id}'
                    )

                autoreporters.append(autoreporter)

            for a in autoreporters:
                session.delete(a)

            session.commit()
            self.push(
                action='skyportal/REFRESH_TNSROBOTS',
            )
            return self.success()


class TNSRobotSubmissionHandler(BaseHandler):
    @auth_or_token
    def get(self, tnsrobot_id, id=None):
        """
        ---
        single:
            description: Retrieve a TNSRobotSubmission
            parameters:
                - in: path
                  name: tnsrobot_id
                  required: true
                  schema:
                    type: integer
                  description: The ID of the TNSRobot
                - in: path
                  name: id
                  required: false
                  schema:
                    type: integer
                  description: The ID of the TNSRobotSubmission
            responses:
                200:
                    content:
                        application/json:
                            schema: TNSRobotSubmission
                400:
                    content:
                        application/json:
                            schema: Error
        multiple:
            description: Retrieve all TNSRobotSubmissions
            parameters:
                - in: path
                  name: tnsrobot_id
                  required: true
                  schema:
                    type: integer
                  description: The ID of the TNSRobot
                - in: query
                  name: pageNumber
                  required: false
                  schema:
                    type: integer
                  description: The page number to retrieve, starting at 1
                - in: query
                  name: numPerPage
                  required: false
                  schema:
                    type: integer
                  description: The number of results per page, defaults to 100
                - in: query
                  name: include_payload
                  required: false
                  schema:
                    type: boolean
                  description: Whether to include the payload in the response
                - in: query
                  name: include_response
                  required: false
                  schema:
                    type: boolean
                  description: Whether to include the response in the response
            responses:
                200:
                    content:
                        application/json:
                            schema: ArrayOfTNSRobotSubmissions
                400:
                    content:
                        application/json:
                            schema: Error
        """
        include_payload = self.get_query_argument('include_payload', False)
        include_response = self.get_query_argument('include_response', False)
        if str(include_payload).lower().strip() in ['true', 't', '1']:
            include_payload = True
        if str(include_response).lower().strip() in ['true', 't', '1']:
            include_response = True

        page_number = self.get_query_argument('pageNumber', 1)
        page_size = self.get_query_argument('numPerPage', 100)
        obj_id = self.get_query_argument('objectID', None)
        try:
            page_number = int(page_number)
            page_size = int(page_size)
            if page_number < 1 or page_size < 1:
                raise ValueError
        except ValueError:
            return self.error(
                'pageNumber and pageSize must be integers, with pageNumber starting at 1 and pageSize > 0'
            )

        if obj_id is not None:
            try:
                obj_id = str(obj_id)
                if len(obj_id) == 0:
                    obj_id = None
            except ValueError:
                return self.error('objectID must be a string')

        # for a given TNSRobot, return all the submissions (paginated)
        with self.Session() as session:
            tnsrobot = session.scalar(
                TNSRobot.select(session.user_or_token).where(TNSRobot.id == tnsrobot_id)
            )
            if tnsrobot is None:
                return self.error(f'TNSRobot {tnsrobot_id} not found')

            if id is not None:
                # we want to return a single submission
                submission = session.scalar(
                    TNSRobotSubmission.select(session.user_or_token).where(
                        TNSRobotSubmission.tnsrobot_id == tnsrobot_id,
                        TNSRobotSubmission.id == id,
                    )
                )
                if submission is None:
                    return self.error(
                        f'Submission {id} not found for TNSRobot {tnsrobot_id}'
                    )
                submission = {
                    "tns_name": submission.obj.tns_name,
                    **submission.to_dict(),
                }
                return self.success(data=submission)
            else:
                stmt = TNSRobotSubmission.select(session.user_or_token).where(
                    TNSRobotSubmission.tnsrobot_id == tnsrobot_id
                )
                if obj_id is not None:
                    stmt = stmt.where(TNSRobotSubmission.obj_id == obj_id)

                # run a count query to get the total number of results
                total_matches = session.execute(
                    sa.select(sa.func.count()).select_from(stmt)
                ).scalar()

                # order by created_at descending
                stmt = stmt.order_by(TNSRobotSubmission.created_at.desc())

                # undefer the payload and response columns if requested
                if include_payload:
                    stmt = stmt.options(sa.orm.undefer(TNSRobotSubmission.payload))
                if include_response:
                    stmt = stmt.options(sa.orm.undefer(TNSRobotSubmission.response))

                # get the paginated results
                submissions = session.scalars(
                    stmt.limit(page_size).offset((page_number - 1) * page_size)
                ).all()

                return self.success(
                    data={
                        'tnsrobot_id': tnsrobot.id,
                        'submissions': [
                            {"tns_name": s.obj.tns_name, **s.to_dict()}
                            for s in submissions
                        ],
                        'pageNumber': page_number,
                        'numPerPage': page_size,
                        'totalMatches': total_matches,
                    }
                )


class BulkTNSHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """
        ---
        description: Retrieve objects from TNS
        tags:
          - objs
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  tnsrobotID:
                    type: int
                    description: |
                      TNS Robot ID.
                  startDate:
                    type: string
                    description: |
                      Arrow-parseable date string (e.g. 2020-01-01).
                      Filter by public_timestamp >= startDate.
                      Defaults to one day ago.
                  groupIds:
                    type: array
                    items:
                      type: integer
                    description: |
                      List of IDs of groups to indicate labelling for
                required:
                  - tnsrobotID
                  - groupIds
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

        data = self.get_json()
        group_ids = data.get("groupIds", None)
        if group_ids is None:
            return self.error('group_ids is required')
        elif isinstance(group_ids, str):
            group_ids = [int(x) for x in group_ids.split(",")]
        elif not isinstance(group_ids, list):
            return self.error('group_ids type not understood')

        start_date = data.get('startDate', None)
        if start_date is None:
            start_date = Time.now() - TimeDelta(1 * u.day)
        else:
            start_date = Time(arrow.get(start_date.strip()).datetime)

        tnsrobot_id = data.get("tnsrobotID", None)
        if tnsrobot_id is None:
            return self.error('tnsrobotID is required')

        include_photometry = data.get("includePhotometry", False)
        include_spectra = data.get("includeSpectra", False)

        with self.Session() as session:
            tnsrobot = session.scalars(
                TNSRobot.select(session.user_or_token).where(TNSRobot.id == tnsrobot_id)
            ).first()
            if tnsrobot is None:
                return self.error(f'No TNSRobot available with ID {tnsrobot_id}')

            altdata = tnsrobot.altdata
            if not altdata:
                return self.error('Missing TNS information.')
            if 'api_key' not in altdata:
                return self.error('Missing TNS API key.')

            try:
                loop = asyncio.get_event_loop()
            except Exception:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            IOLoop.current().run_in_executor(
                None,
                lambda: get_tns(
                    tnsrobot.id,
                    self.associated_user_object.id,
                    include_photometry=include_photometry,
                    include_spectra=include_spectra,
                    start_date=start_date.isot,
                    group_ids=group_ids,
                ),
            )

            return self.success()


class ObjTNSHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id):
        """
        ---
        description: Retrieve an Obj from TNS
        tags:
          - objs
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
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

        radius = self.get_query_argument("radius", 2.0)

        try:
            radius = float(radius)
        except ValueError:
            return self.error('radius must be a number')
        else:
            if radius < 0:
                return self.error('radius must be non-negative')

        with self.Session() as session:
            obj = session.scalars(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            ).first()
            if obj is None:
                return self.error(f'No object available with ID {obj_id}')

            try:
                loop = asyncio.get_event_loop()
            except Exception:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            IOLoop.current().run_in_executor(
                None,
                lambda: get_tns(
                    obj_id=obj.id,
                    radius=radius,
                    user_id=self.associated_user_object.id,
                ),
            )

            return self.success()

    @auth_or_token
    def post(self, obj_id):
        """
        ---
        description: Post an Obj to TNS
        tags:
          - objs
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
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
            data = self.get_json()
            tnsrobotID = data.get('tnsrobotID')
            reporters = data.get('reporters', '')
            remarks = data.get('remarks', '')
            archival = data.get('archival', False)
            archival_comment = data.get('archivalComment', '')
            instrument_ids = data.get('instrument_ids', [])
            stream_ids = data.get('stream_ids', [])
            photometry_options = data.get('photometry_options', {})

            if tnsrobotID is None:
                return self.error('tnsrobotID is required')
            if reporters == '' or not isinstance(reporters, str):
                return self.error(
                    'reporters is required and must be a non-empty string'
                )
            if len(instrument_ids) > 0:
                try:
                    instrument_ids = [int(x) for x in instrument_ids]
                except ValueError:
                    return self.error(
                        'instrument_ids must be a comma-separated list of integers'
                    )
                instrument_ids = list(set(instrument_ids))
                instruments = session.scalars(
                    Instrument.select(session.user_or_token).where(
                        Instrument.id.in_(instrument_ids)
                    )
                ).all()
                if len(instruments) != len(instrument_ids):
                    return self.error(
                        f'One or more instruments not found: {instrument_ids}'
                    )

                for instrument in instruments:
                    if instrument.name.lower() not in TNS_INSTRUMENT_IDS:
                        return self.error(
                            f'Instrument {instrument.name} not supported for TNS reporting'
                        )

            if stream_ids is not None:
                try:
                    if isinstance(stream_ids, str):
                        stream_ids = [int(x) for x in stream_ids.split(",")]
                    else:
                        stream_ids = [int(x) for x in stream_ids]
                except ValueError:
                    return self.error(
                        'stream_ids must be a comma-separated list of integers'
                    )
                stream_ids = list(set(stream_ids))
                streams = session.scalars(
                    Stream.select(session.user_or_token).where(
                        Stream.id.in_(stream_ids)
                    )
                ).all()
                if len(streams) != len(stream_ids):
                    return self.error(f'One or more streams not found: {stream_ids}')

            obj = session.scalars(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            ).first()
            if obj is None:
                return self.error(f'No object available with ID {obj_id}')

            tnsrobot = session.scalars(
                TNSRobot.select(session.user_or_token).where(TNSRobot.id == tnsrobotID)
            ).first()
            if tnsrobot is None:
                return self.error(f'No TNSRobot available with ID {tnsrobotID}')

            if archival is True:
                if len(archival_comment) == 0:
                    return self.error(
                        'If source flagged as archival, archival_comment is required'
                    )

            altdata = tnsrobot.altdata
            if not altdata:
                return self.error('Missing TNS information.')
            if 'api_key' not in altdata:
                return self.error('Missing TNS API key.')

            photometry_options = validate_photometry_options(
                photometry_options, tnsrobot.photometry_options
            )

            # verify that there isn't already a TNSRobotSubmission for this object
            # and TNSRobot, that is:
            # 1. pending
            # 2. processing
            # 3. submitted
            # 4. complete
            # if so, do not add another request
            existing_submission_request = session.scalars(
                TNSRobotSubmission.select(session.user_or_token).where(
                    TNSRobotSubmission.obj_id == obj.id,
                    TNSRobotSubmission.tnsrobot_id == tnsrobot.id,
                    sa.or_(
                        TNSRobotSubmission.status == "pending",
                        TNSRobotSubmission.status == "processing",
                        TNSRobotSubmission.status.like("submitted%"),
                        TNSRobotSubmission.status.like("complete%"),
                    ),
                )
            ).first()
            if existing_submission_request is not None:
                return self.error(
                    f'TNSRobotSubmission request for obj_id {obj.id} and tnsrobot_id {tnsrobot.id} already exists and is: {existing_submission_request.status}'
                )
            # create a TNSRobotSubmission entry with that information
            tnsrobot_submission = TNSRobotSubmission(
                tnsrobot_id=tnsrobot.id,
                obj_id=obj.id,
                user_id=self.associated_user_object.id,
                custom_reporting_string=reporters,
                custom_remarks_string=remarks,
                archival=archival,
                archival_comment=archival_comment,
                instrument_ids=instrument_ids,
                stream_ids=stream_ids,
                photometry_options=photometry_options,
                auto_submission=False,
            )
            session.add(tnsrobot_submission)
            session.commit()
            log(
                f"Added TNSRobotSubmission request for obj_id {obj.id} (manual submission) with tnsrobot_id {tnsrobot.id} for user_id {self.associated_user_object.id}"
            )
            return self.success()


class SpectrumTNSHandler(BaseHandler):
    @auth_or_token
    def post(self, spectrum_id):
        """
        ---
        description: Submit a (classification) spectrum to TNS
        tags:
          - spectra
        parameters:
          - in: path
            name: spectrum_id
            required: true
            schema:
              type: integer
          - in: query
            name: tnsrobotID
            schema:
              type: int
            required: true
            description: |
                SkyPortal TNS Robot ID
          - in: query
            name: classificationID
            schema:
              type: string
            description: |
                Classification ID (see TNS documentation at
                https://www.wis-tns.org/content/tns-getting-started
                for options)
          - in: query
            name: classifiers
            schema:
              type: string
            description: |
                List of those performing classification.
          - in: query
            name: spectrumType
            schema:
              type: string
            description: |
                Type of spectrum that this is. Valid options are:
                ['object', 'host', 'sky', 'arcs', 'synthetic']
          - in: query
            name: spectrumComment
            schema:
              type: string
            description: |
                Comment on the spectrum.
          - in: query
            name: classificationComment
            schema:
              type: string
            description: |
                Comment on the classification.
        responses:
          200:
            content:
              application/json:
                schema: SingleSpectrum
          400:
            content:
              application/json:
                schema: Error
        """

        # for now this is deprecated, as the feature is not used by any user
        # + needs to be updated to use the new TNS submission queue
        return self.error('This feature is deprecated')

        data = self.get_json()
        tnsrobotID = data.get('tnsrobotID')
        classificationID = data.get('classificationID', None)
        classifiers = data.get('classifiers', '')
        spectrum_type = data.get('spectrumType', '')
        spectrum_comment = data.get('spectrumComment', '')
        classification_comment = data.get('classificationComment', '')

        if tnsrobotID is None:
            return self.error('tnsrobotID is required')

        with self.Session() as session:
            tnsrobot = session.scalars(
                TNSRobot.select(session.user_or_token).where(TNSRobot.id == tnsrobotID)
            ).first()
            if tnsrobot is None:
                return self.error(f'No TNSRobot available with ID {tnsrobotID}')

            altdata = tnsrobot.altdata
            if not altdata:
                return self.error('Missing TNS information.')

            spectrum = session.scalars(
                Spectrum.select(session.user_or_token).where(Spectrum.id == spectrum_id)
            ).first()
            if spectrum is None:
                return self.error(f'No spectrum with ID {spectrum_id}')

            spec_dict = recursive_to_dict(spectrum)
            spec_dict["instrument_name"] = spectrum.instrument.name
            spec_dict["groups"] = spectrum.groups
            spec_dict["reducers"] = spectrum.reducers
            spec_dict["observers"] = spectrum.observers
            spec_dict["owner"] = spectrum.owner

            external_reducer = session.scalars(
                SpectrumReducer.select(session.user_or_token).where(
                    SpectrumReducer.spectr_id == spectrum_id
                )
            ).first()
            if external_reducer is not None:
                spec_dict["external_reducer"] = external_reducer.external_reducer

            external_observer = session.scalars(
                SpectrumObserver.select(session.user_or_token).where(
                    SpectrumObserver.spectr_id == spectrum_id
                )
            ).first()
            if external_observer is not None:
                spec_dict["external_observer"] = external_observer.external_observer

            tns_headers = {
                'User-Agent': f'tns_marker{{"tns_id":{tnsrobot.bot_id},"type":"bot", "name":"{tnsrobot.bot_name}"}}'
            }

            tns_prefix, tns_name = get_IAUname(
                spectrum.obj.id, altdata['api_key'], tns_headers
            )
            if tns_name is None:
                return self.error('TNS name missing... please first post to TNS.')

            if spectrum.obj.redshift:
                redshift = spectrum.obj.redshift

            spectype_id = ['object', 'host', 'sky', 'arcs', 'synthetic'].index(
                spectrum_type
            ) + 1

            if spec_dict["altdata"] is not None:
                header = spec_dict["altdata"]
                exposure_time = header['EXPTIME']
            else:
                exposure_time = None

            wav = spec_dict['wavelengths']
            flux = spec_dict['fluxes']
            err = spec_dict['errors']

            filename = f'{spectrum.instrument.name}.{spectrum_id}'
            filetype = 'ascii'

            with tempfile.NamedTemporaryFile(
                prefix=filename,
                suffix=f'.{filetype}',
                mode='w',
            ) as f:
                if err is not None:
                    for i in range(len(wav)):
                        f.write(f'{wav[i]} \t {flux[i]} \t {err[i]} \n')
                else:
                    for i in range(len(wav)):
                        f.write(f'{wav[i]} \t {flux[i]}\n')
                f.flush()

                data = {'api_key': altdata['api_key']}

                if filetype == 'ascii':
                    files = [('files[]', (filename, open(f.name), 'text/plain'))]
                elif filetype == 'fits':
                    files = [
                        ('files[0]', (filename, open(f.name, 'rb'), 'application/fits'))
                    ]

                r = requests.post(
                    upload_url, headers=tns_headers, data=data, files=files
                )
                if r.status_code != 200:
                    return self.error(f'{r.content}')

                spectrumdict = {
                    'instrumentid': spectrum.instrument.tns_id,
                    'observer': spec_dict["observers"],
                    'reducer': spec_dict["reducers"],
                    'spectypeid': spectype_id,
                    'ascii_file': filename,
                    'fits_file': '',
                    'remarks': spectrum_comment,
                    'spec_proprietary_period': 0.0,
                    'obsdate': spec_dict['observed_at'],
                }
                if exposure_time is not None:
                    spectrumdict['exptime'] = exposure_time

                classification_report = {
                    'name': tns_name,
                    'classifier': classifiers,
                    'objtypeid': classificationID,
                    'groupid': tnsrobot.source_group_id,
                    'remarks': classification_comment,
                    'spectra': {'spectra-group': {'0': spectrumdict}},
                }
                if redshift is not None:
                    classification_report['redshift'] = redshift

                classificationdict = {
                    'classification_report': {'0': classification_report}
                }

                data = {
                    'api_key': altdata['api_key'],
                    'data': json.dumps(classificationdict),
                }

                r = requests.post(report_url, headers=tns_headers, data=data)
                if r.status_code == 200:
                    tns_id = r.json()['data']['report_id']
                    return self.success(data={'tns_id': tns_id})
                else:
                    return self.error(f'{r.content}')
