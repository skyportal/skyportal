import os
import base64

# import traceback

import pandas as pd

import sqlalchemy as sa

from baselayer.app.access import permissions  # , auth_or_token
from marshmallow.exceptions import ValidationError

from baselayer.app.env import load_env

from ..base import BaseHandler

from ...models.photometric_series import (
    PhotometricSeries,
    # REQUIRED_ATTRIBUTES,
    # INFERABLE_ATTRIBUTES,
    # OPTIONAL_ATTRIBUTES,
    # DATA_TYPES,
    verify_data,
    infer_metadata,
    verify_metadata,
)
from ...models.group import Group
from ...models.stream import Stream
from ...models.obj import Obj
from ...models.instrument import Instrument
from ...models.followup_request import FollowupRequest
from ...models.assignment import ClassicalAssignment


_, cfg = load_env()


def get_group_ids(data, user, session):
    group_ids = data.pop("group_ids", [])
    if isinstance(group_ids, str) and group_ids == "all":
        public_group = session.scalars(
            sa.select(Group).where(Group.name == cfg["misc.public_group_name"])
        ).first()
        group_ids = [public_group.id]
    if isinstance(group_ids, (int, str)):
        group_ids = [group_ids]
    if not isinstance(group_ids, (list, tuple)):
        raise ValidationError(
            "Invalid group_ids parameter value. Must be a list of IDs "
            "(integers) or the string 'all'."
        )
    for group_id in group_ids:
        try:
            group_id = int(group_id)
        except TypeError:
            raise ValidationError(
                f"Invalid format for group id {group_id}, must be an integer."
            )
        group = session.scalars(Group.select(user).where(Group.id == group_id)).first()
        if group is None:
            raise ValidationError(f'Invalid group ID: {group_id}')

    # always add the single user group
    group_ids.append(user.single_user_group.id)
    group_ids = list(set(group_ids))
    return group_ids


def get_stream_ids(data, user, session):
    stream_ids = data.pop("stream_ids", [])
    if not isinstance(stream_ids, (list, tuple)):
        raise ValidationError(
            "Invalid stream_ids parameter value. Must be a list of IDs (integers)."
        )
    for stream_id in stream_ids:
        try:
            stream_id = int(stream_id)
        except TypeError:
            raise ValidationError(
                f"Invalid format for stream id {stream_id}, must be an integer."
            )
        stream = session.scalars(
            Stream.select(user).where(Stream.id == stream_id)
        ).first()

        if stream is None:
            raise ValidationError(f'No stream with ID {stream_id}')

    stream_ids = list(set(stream_ids))
    return stream_ids


class PhotometricSeriesHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---


        """
        json_data = self.get_json()
        data = json_data.pop('data')
        if data is None:
            return self.error(
                'Must supply data as a dictionary (JSON) or dataframe in HDF5 format. '
            )

        # do not allow user input to change the owner_id (current user id)
        json_data.pop('owner_id', None)

        attributes_metadata = {}
        if isinstance(data, dict):
            try:
                data = pd.DataFrame(data)
            except Exception as e:
                return self.error(f'Could not convert data to a DataFrame. {e} ')
        elif isinstance(data, str):
            try:
                # load the pandas data frame from a byte stream:
                # ref: https://github.com/pandas-dev/pandas/issues/9246#issuecomment-74041497
                with pd.HDFStore(
                    "data.h5",
                    mode="r",
                    driver="H5FD_CORE",
                    driver_core_backing_store=0,
                    driver_core_image=base64.b64decode(data),
                ) as store:
                    keys = store.keys()
                    if len(keys) != 1:
                        return self.error(
                            f'Expected 1 table in HDF5 file, got {len(keys)}. '
                        )
                    data = store[keys[0]]
                    attributes = store.get_storer(keys[0]).attrs
                    if 'metadata' in attributes and isinstance(
                        attributes['metadata'], dict
                    ):
                        attributes_metadata = attributes['metadata']

            except Exception as e:
                return self.error(f'Could not load DataFrame from HDF5 file. {e} ')
        else:
            return self.error(
                'Data must be a dictionary (JSON) or dataframe in HDF5 format. '
            )

        try:
            # make sure data has the minimal columns:
            verify_data(data)

            # check if any metadata can be inferred from the data:
            metadata = infer_metadata(data)

            # if we got any more data from the HDF5 file:
            metadata.update(attributes_metadata)

            # now load any additional metadata from the json_data:
            metadata.update(json_data)

        except Exception as e:
            return self.error(f'Problem parsing data/metadata: {e}')

        # check all the related DB objects are valid:
        with self.Session() as session:
            try:
                group_ids = get_group_ids(
                    json_data, self.associated_user_object, session
                )
            except Exception as e:
                return self.error(f'Could not parse group IDs: {e}')
            try:
                stream_ids = get_stream_ids(
                    json_data, self.associated_user_object, session
                )
            except Exception as e:
                return self.error(f'Could not parse stream IDs: {e}')

            obj_id = json_data.pop('obj_id', None)
            if obj_id is None:
                return self.error('Must supply an obj_id')
            obj = session.scalars(
                Obj.select(self.associated_user_object).where(Obj.id == obj_id)
            ).first()
            if obj is None:
                return self.error(f'Invalid obj_id: {obj_id}')

            instrument_id = json_data.get('instrument_id')
            if instrument_id is not None:
                instrument = session.scalars(
                    Instrument.select(self.current_user).where(
                        Instrument.id == instrument_id
                    )
                ).first()
                if instrument is None:
                    return self.error(f'Invalid instrument_id: {instrument_id}')

            followup_request_id = json_data.get('followup_request_id')
            if followup_request_id is not None:
                followup_request = session.scalars(
                    FollowupRequest.select(self.current_user).where(
                        FollowupRequest.id == followup_request_id
                    )
                ).first()
                if followup_request is None:
                    return self.error(
                        f'Invalid followup_request_id: {followup_request_id}'
                    )

            assignment_id = json_data.get('assignment_id')
            if assignment_id is not None:
                assignment = session.scalars(
                    ClassicalAssignment.select(self.current_user).where(
                        ClassicalAssignment.id == assignment_id
                    )
                ).first()
                if assignment is None:
                    return self.error(f'Invalid assignment_id: {assignment_id}')

        try:
            # load the group and stream IDs:
            metadata.update(
                {
                    'group_ids': group_ids,
                    'stream_ids': stream_ids,
                    'owner_id': self.associated_user_object.id,
                }
            )

            # make sure all required attributes are present
            # make sure no unknown attributes are present
            # parse all attributes into correct type
            metadata = verify_metadata(metadata)

        except Exception as e:
            return self.error(f'Problem parsing data/metadata: {e}')

        try:
            ps = PhotometricSeries(data, **metadata)
        except Exception as e:
            return self.error(f'Could not create PhotometricSeries object: {e}')

        try:
            # make sure we can get the file name:
            full_name, path = ps.make_full_name()

            # make sure the file does not exist:
            if os.path.isfile(full_name):
                return self.error(f'File already exists: {full_name}')

            # make sure this file is not already saved using the hash:
            with self.Session() as session:
                exiting_ps = session.scalars(
                    sa.select(PhotometricSeries).where(
                        PhotometricSeries.hash == ps.hash
                    )
                ).first()
                if exiting_ps is not None:
                    return self.error(
                        'A PhotometricSeries with the same hash already exists, '
                        f'with filename: {exiting_ps.make_full_name()[0]}'
                    )

        except Exception as e:
            return self.error(f'Errors when making file name or hash: {e}')

        with self.Session() as session:
            try:
                ps.save_data()
                session.add(ps)
                session.commit()

                return self.success(data={'id': ps.id})

            except Exception as e:
                session.rollback()
                ps.delete_data()  # make sure not to leave files behind
                return self.error(f'Could not save photometric series: {e}')
