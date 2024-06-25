import os
import traceback

import pandas as pd
import arrow

from astropy.time import Time

import sqlalchemy as sa
from sqlalchemy import func
from sqlalchemy.sql.expression import case
import conesearch_alchemy as ca

from baselayer.app.access import permissions  # , auth_or_token
from marshmallow.exceptions import ValidationError

from baselayer.app.env import load_env
from baselayer.log import make_log

from ..base import BaseHandler
from ...enum_types import ALLOWED_BANDPASSES
from ...models.photometric_series import (
    PhotometricSeries,
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
from ...utils.hdf5_files import load_dataframe_from_bytestream

_, cfg = load_env()

body_schema_docstring = """
  content:
    application/json:
      schema:
        type: object
        properties:
          data:
            type: string or dict
            description: |
              The data to upload. Can be a string or a dict.
              If a dict (i.e., a json object) will assume each
              key is a column name and each value is a list of
              values for that column.
              That dictionary will be passed into a pandas
              DataFrame constructor, so the keys must be valid
              and the length of each value must be the same.
              If a string, will be converted to a bytes array
              and de-serialized by the pandas HDF5 reader.
              Use the HDFStore to create a file that includes
              a single key/group with the photometric data.
              Additional information, including any of the
              parameters specified below, can be stored in
              the HDFStore as well, inside the attributes
              under the key "metadata".
              In any case the DataFrame must have the following
              columns: "mjd", and either "flux" or "mag".
              Additional columns like "fluxerr" or "magerr" can be
              added, to plot errorbars on the frontend.
              Columns like "RA" or "exp_time" can be added to keep
              track of the values for individual observations,
              and the median value of these columns can be used
              instead of specifying the values in the metadata.
              Other information can be added as additional columns
              that will be saved to disk. That information will not
              be used by SkyPortal, but will be available for download.
            required: true
          series_name:
            type: string
            description: |
              Name of the photometric series. Each series can contain light curves
              for multiple objects, and is usually continuous in some sense.
              Each series has a single instrument/filter, and generally a single pointing.
              Some examples would be a TESS sector or a single pointing with a fast photometer.
              The series name is used as the path to the file containing the photometric data,
              and can contain slashes (can also include underscores, + and -).
            required: true
          series_obj_id:
            type: string
            description: |
              Name or number of the object inside the photometric series. This can
              be a global object ID from the specific survey (e.g., a TESS TIC ID),
              or a casual index of the object in the series (e.g., star number 3).
              This does not have to correspond to the object ID in SkyPortal.
              It must be a unique identifier inside the series to be able to upload
              multiple light curves for different objects in the same series.
            required: true
          obj_id:
            type: string
            description: SkyPortal object ID.
            required: true
          instrument_id:
            type: integer
            description: SkyPortal ID of the instrument used to take the photometric series.
            required: true
          group_ids:
            type: array
            items:
              type: integer
            description: |
              List of group IDs to associate with the photometric series.
              If not specified, defaults to the user's single user group.
              Can also specify "all" to share with all groups.
            required: false
          stream_ids:
            type: array
            items:
              type: integer
            description: |
              List of stream IDs to associate with the photometric series.
            required: false
          ra:
            type: number
            description: |
              Right ascension of the photometric series (degrees).
              Can specify the value for the entire series,
              or add an "RA" column to the data file.
              If not specified, the median RA from the data
              will be used as the coordinate for this object.
              If specified, will override the median value,
              but will not affect the individual measured RA.
              If no ra is given and no such column exists in the data file,
              the photometric series will not be posted.
            required: false
          dec:
            type: number
            description: |
              Declination of the photometric series (degrees).
              Same as the RA column, only using the Dec column.
            required: false
          exp_time:
            type: number
            description: |
              Exposure time of each measurement in the
              photometric series (seconds). If not specified,
              the median value of the "exp_time" column in
              the data file will be used instead.
              If no such column exists and the exp_time is not
              given, the photometric series will not be posted.
            required: false
          filter:
            type: string
            description: |
              Name of the filter used to take the photometric series.
              If not specified, the filter name will be inferred from the
              data file. If no filter name is given and no such column
              If no filter name is given and no such column exists in the data file,
              the photometric series will not be posted.
              Filter must be one of the allowed band passes.
            required: false
          channel:
            type: string
            description: |
              Name of the channel used to take the photometric series.
              This is useful for multi-band simultaneous photometry,
              or for mosiaced CCD images where each tile has its own channel ID.
              This allows multiple series to be saved with the same series name
              but different channels, without violating the uniqueness constraint.
              Series with different channels can have the same or different filters.
              This field is entirely optional.
            required: false
          limiting_mag:
            type: number
            description: |
              The limiting magnitude of the photometric series.
              Can specify the value for the entire series,
              or add an "limiting_mag" column to the data file.
              If not specified, the median limit from the data
              will be used as the representative limiting mag for this series.
              If specified, will override the median value,
              but will not affect the individual measured limits.
              If no limit is given and no such column exists in the data file,
              the photometric series will be posted with None as the limit.
          magref:
            type: number
            description: |
              Reference magnitude for the photometric series.
              This is used when the photometry is relative
              (e.g., based on subtraction images) and the magnitude
              of the object when it is not active is measured separately.
              This would be the magnitude before/after a transient,
              or the mean magnitude of a variable.
              For absolute photometry this is left as None.
            required: false
          e_magref:
            type: number
            description: uncertainty on the magref.
            required: false
          ra_unc:
            type: number
            description: uncertainty on the ra.
            required: false
          dec_unc:
            type: number
            description: uncertainty on the dec.
            required: false
          followup_request_id:
            type: integer
            description: |
                ID of the followup request that generated this photometric series.
                This is used to link the photometric series to the followup request
                in the SkyPortal database.
            required: false
          assignment_id:
            type: integer
            description: |
                ID of the assignment that generated this photometric series.
                This is used to link the photometric series to the assignment
                in the SkyPortal database.
            required: false
          time_stamp_alignment:
            type: string
            description: |
              Specify when the time stamp for each measurement was taken
              inside each exposure. Possible values are "start", "middle", "end".
              This is optional, and defaults to "middle".
            required: false
          altdata:
            type: object
            description: |
                Additional information to store in the photometric series.
                This can be any valid JSON object, and will be stored
                in the database as a JSON string.
                This can hold various information that does not fit into
                any of the other inputs, but will still be useful to keep track of.
            required: false
        """


log = make_log('api/photometric_series')

DEFAULT_SERIES_PER_PAGE = 100
MAX_SERIES_PER_PAGE = 500


def get_group_ids(data, user, session):
    """
    Get group IDs from the request data.

    Parameters
    ----------
    data: dict
        Dictionary that can contain a "group_ids" key.
    user: skyportal.models.User
        The user associated with the request.
    session: sqlalchemy.orm.Session
        The database session.

    Returns
    -------
    group_ids: list of int
        If input data['group_ids'] is "all",
        returns the public group ID.
        Otherwise will return the list of ints.
        In any case, it will append the user's
        single user group ID to the list,
        and return only unique values.
    """
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
    """
    Get stream IDs from the request data.

    Parameters
    ----------
    data: dict
        Dictionary that can contain a "stream_ids" key.
    user: skyportal.models.User
        The user associated with the request.
    session: sqlalchemy.orm.Session
        The database session.

    Returns
    -------
    stream_ids: list of int
        Verifies each of the stream IDs in the input list
        and returns the list of unique values.
    """
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


def individual_enum_checks(metadata):
    """
    Check that the metadata dictionary contains
    the correct values for columns that are enums.
    E.g., checks that the 'filter' column contains
    a valid filter name.
    If not, will raise a ValueError.
    """
    # check filter is legal
    if metadata['filter'] not in ALLOWED_BANDPASSES:
        raise ValueError(
            f'Filter {metadata["filter"]} is not allowed. '
            f'Allowed filters are: {ALLOWED_BANDPASSES}'
        )

    # check time_stamp_alignement is legal
    tsa = metadata.get('time_stamp_alignment', 'middle')
    if tsa not in ['start', 'middle', 'end']:
        raise ValueError(
            f'Time stamp alignment {tsa} is not allowed. '
            f'Allowed values are: start, middle, end'
        )


def check_objects_exist(metadata, user, session):
    """
    Check that the objects referenced by their IDs
    in the metadata dictionary exist and are accessible.
    Will raise a ValueError if any of the objects
    cannot be accessed by the user.

    Parameters
    ----------
    metadata: dict
        Dictionary containing the metadata for the photometric series.
        Must have at least an 'object_id' and 'instrument_id' keys.
    user: skyportal.models.User
        The user associated with the request.
    session: sqlalchemy.orm.Session
        The database session.

    """
    obj_id = metadata.get('obj_id', None)
    if obj_id is None:
        raise ValueError('Must supply an obj_id')
    obj = session.scalars(Obj.select(user).where(Obj.id == obj_id)).first()
    if obj is None:
        raise ValueError(f'Invalid obj_id: {obj_id}')

    instrument_id = metadata.get('instrument_id')

    if instrument_id is None:
        raise ValueError('Must supply an instrument_id')

    instrument = session.scalars(
        Instrument.select(user).where(Instrument.id == instrument_id)
    ).first()
    if instrument is None:
        raise ValueError(f'Invalid instrument_id: {instrument_id}')

    followup_request_id = metadata.get('followup_request_id')
    if followup_request_id is not None:
        followup_request = session.scalars(
            FollowupRequest.select(user).where(
                FollowupRequest.id == followup_request_id
            )
        ).first()
        if followup_request is None:
            raise ValueError(f'Invalid followup_request_id: {followup_request_id}')

    assignment_id = metadata.get('assignment_id')
    if assignment_id is not None:
        assignment = session.scalars(
            ClassicalAssignment.select(user).where(
                ClassicalAssignment.id == assignment_id
            )
        ).first()
        if assignment is None:
            raise ValueError(f'Invalid assignment_id: {assignment_id}')


def post_photometric_series(json_data, data, attributes_metadata, user, session):
    """
    Post the photometric series.

    Parameters
    ----------
    json_data : dict
        Dictionary containing any information, such as to be added to metadata.
    data : pandas.DataFrame
        Photometric series data set.
    attributes_metadata: dict
        Dictionary containing the metadata for the photometric series.
        Must have at least an 'object_id' and 'instrument_id' keys.
    user: skyportal.models.User
        The user associated with the request.
    session: sqlalchemy.orm.Session
        The database session.

    """

    try:
        # make sure data has the minimal columns:
        verify_data(data)

        # check if any metadata can be inferred from the data:
        metadata = infer_metadata(data)

        # if we got any more data from the HDF5 file:
        metadata.update(attributes_metadata)

        # now load any additional metadata from the json_data:
        metadata.update(json_data)

        # remove any metadata items that are None (equivalent to not given):
        for k, v in metadata.items():
            if v is None:
                metadata.pop(k)

    except Exception:
        raise ValueError(f'Problem parsing data/metadata: {traceback.format_exc()}')

    # check all the related DB objects are valid:
    try:
        group_ids = get_group_ids(metadata, user, session)
    except Exception:
        raise ValueError(f'Could not parse group IDs: {traceback.format_exc()}')
    try:
        stream_ids = get_stream_ids(metadata, user, session)
    except Exception:
        raise ValueError(f'Could not parse stream IDs: {traceback.format_exc()}')

    try:
        check_objects_exist(metadata, user, session)
    except Exception:
        raise ValueError(
            f'Problems accessing database objects: {traceback.format_exc()}'
        )

    try:
        # load the group, stream and owner IDs:
        metadata.update(
            {
                'group_ids': group_ids,
                'stream_ids': stream_ids,
                'owner_id': user.id,
            }
        )

        # make sure all required attributes are present
        # make sure no unknown attributes are present
        # parse all attributes into correct type
        metadata = verify_metadata(metadata)

    except Exception:
        raise ValueError(f'Problem parsing data/metadata: {traceback.format_exc()}')

    try:
        individual_enum_checks(metadata)
    except Exception:
        raise ValueError(f'Problem parsing metadata: {traceback.format_exc()}')

    try:
        ps = PhotometricSeries(data, **metadata)
        # allow the config to change the default behavior:
        ps.autodelete = cfg.get('photometric_series_autodelete', True)

    except Exception:
        raise ValueError(
            f'Could not create PhotometricSeries object: {traceback.format_exc()}'
        )

    try:
        # make sure we can get the file name:
        full_name, path = ps.make_full_name()
    except Exception:
        raise ValueError(f'Errors when making file name: {traceback.format_exc()}')

    # make sure the file does not exist:
    if os.path.isfile(full_name):
        # check if there are any entries in the DB that point to this file:
        existing_ps = session.scalars(
            sa.select(PhotometricSeries).where(PhotometricSeries.filename == full_name)
        ).first()
        if existing_ps is not None:
            raise ValueError(
                f'PhotometricSeries with filename {full_name} already exists'
            )
        else:
            # if the file exists but is not in the DB, we can overwrite it
            os.remove(full_name)

    # make sure this file is not already saved using the hash:
    existing_ps = session.scalars(
        sa.select(PhotometricSeries).where(PhotometricSeries.hash == ps.hash)
    ).first()
    if existing_ps is not None:
        raise ValueError(
            'A PhotometricSeries with the same hash already exists, '
            f'with filename: {existing_ps.make_full_name()[0]}'
        )

    try:
        ps.save_data()
        session.add(ps)
        session.commit()

        return ps.id

    except Exception:
        session.rollback()
        ps.delete_data()  # make sure not to leave files behind
        raise ValueError(f'Could not save photometric series: {traceback.format_exc()}')


def update_photometric_series(ps, json_data, data, attributes_metadata, user, session):
    """
    Update the photometric series.

    Parameters
    ----------
    ps : skyportal.models.PhotometricSeries
        Photometric series to update.
    json_data : dict
        Dictionary containing any information, such as to be added to metadata.
    data : pandas.DataFrame
        Photometric series data set.
    attributes_metadata: dict
        Dictionary containing the metadata for the photometric series.
        Must have at least an 'object_id' and 'instrument_id' keys.
    user: skyportal.models.User
        The user associated with the request.
    session: sqlalchemy.orm.Session
        The database session.

    """

    # check that the data is valid:
    inferred_metadata = {}
    if data is not None:
        try:
            verify_data(data)
            inferred_metadata = infer_metadata(data)
        except Exception:
            raise ValueError(f'Problem parsing data/metadata: {traceback.format_exc()}')

    prev_filename = ps.filename

    # apply parameters from existing, inferred, bytes stream, and json body.
    existing_metadata = ps.get_metadata()
    metadata = {}
    metadata.update(existing_metadata)
    metadata.update(inferred_metadata)
    metadata.update(attributes_metadata)
    metadata.update(json_data)

    # check all the related DB objects are valid:
    try:
        group_ids = get_group_ids(metadata, user, session)
    except Exception:
        raise ValueError(f'Could not parse group IDs: {traceback.format_exc()}')
    try:
        stream_ids = get_stream_ids(metadata, user, session)
    except Exception:
        raise ValueError(f'Could not parse stream IDs: {traceback.format_exc()}')

    try:
        check_objects_exist(metadata, user, session)
    except Exception:
        raise ValueError(
            f'Problems accessing database objects: {traceback.format_exc()}'
        )

    try:
        # load the group and stream IDs:
        metadata.update(
            {
                'group_ids': group_ids,
                'stream_ids': stream_ids,
                'owner_id': ps.owner_id,  # does not change on PATCH
            }
        )

        # make sure all required attributes are present
        # make sure no unknown attributes are present
        # parse all attributes into correct type
        metadata = verify_metadata(metadata)

    except Exception:
        raise ValueError(f'Problem parsing data/metadata: {traceback.format_exc()}')

    try:
        individual_enum_checks(metadata)
    except Exception:
        raise ValueError(f'Problem parsing metadata: {traceback.format_exc()}')

    # update the underlying data (if given)
    if data is not None:
        try:
            ps.data = data  # also run calc_flux_mag() and calc_stats()
        except Exception:
            raise ValueError(f'Could not update data: {traceback.format_exc()}')

    # update the metadata on the PhotometricSeries object
    for k, v in metadata.items():
        setattr(ps, k, v)

    try:
        # make sure we can get the file name:
        full_name, path = ps.make_full_name()
    except Exception:
        raise ValueError(f'Errors when making file name: {traceback.format_exc()}')

    # make sure the file does not exist:
    if prev_filename != full_name and os.path.isfile(full_name):
        raise ValueError(f'New filename already exists: {full_name}')

    # make sure this file is not already saved using the hash:
    # this includes only objects different from the one being updated
    existing_ps = session.scalars(
        sa.select(PhotometricSeries).where(
            PhotometricSeries.hash == ps.hash, PhotometricSeries.id != ps.id
        )
    ).first()
    if existing_ps is not None:
        raise ValueError(
            'Another PhotometricSeries with the same hash already exists, '
            f'with filename: {existing_ps.make_full_name()[0]}'
        )

    try:
        # save the new data as temporary file:
        ps.save_data(temp=True)
        session.add(ps)
        session.commit()

    except Exception:
        session.rollback()
        ps.delete_data(temp=True)  # make sure not to leave files behind
        raise ValueError(f'Could not save photometric series: {traceback.format_exc()}')

    # get rid of the old data, regardless of new name
    try:
        if os.path.isfile(prev_filename):
            os.remove(prev_filename)
    except Exception:
        log(f'Could not remove old file {prev_filename}: {traceback.format_exc()}')
    ps.move_temp_data()  # make the temp file permanent

    return ps.id


class PhotometricSeriesHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        f"""
        ---
        description: Upload a photometric series.
        tags:
          - photometry
          - photometric series
        requestBody:
          {body_schema_docstring}
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
                              description: New photometric series ID
        """
        json_data = self.get_json()
        data = json_data.pop('data', None)
        if data is None:
            return self.error(
                'Must supply data as a dictionary (JSON) or dataframe in HDF5 format. '
            )

        attributes_metadata = {}
        if isinstance(data, dict):
            try:
                data = pd.DataFrame(data)
            except Exception:
                return self.error(
                    f'Could not convert data to a DataFrame. {traceback.format_exc()} '
                )
        elif isinstance(data, str):
            try:
                data, attributes_metadata = load_dataframe_from_bytestream(data)
            except Exception:
                return self.error(
                    f'Could not load DataFrame from HDF5 file. {traceback.format_exc()} '
                )
        else:
            return self.error(
                'Data must be a dictionary (JSON) or dataframe in HDF5 format. '
            )

        with self.Session() as session:
            try:
                photometric_series_id = post_photometric_series(
                    json_data,
                    data,
                    attributes_metadata,
                    self.associated_user_object,
                    session,
                )
            except Exception as e:
                return self.error(f'Unable to post photometric series: {str(e)}')

        return self.success(data={'id': photometric_series_id})

    @permissions(['Upload data'])
    def patch(self, photometric_series_id):
        f"""
        ---
        description: |
          Update a photometric series.
          All the inputs in the request body are optional.
          In any case the series is loaded, metadata or data are updated,
          and the series is saved again to disk.
          If new data is given, the RA/Dec, exposure time and filter
          will be inferred from the data columns (if the exist),
          and will override the existing values for the photometric series
          in the database. To avoid this, supply those values explicitly
          in the request body parameters.
        tags:
          - photometry
          - photometric series
        parameters:
          - in: path
            name: photometric_series_id
            required: true
            schema:
              type: integer
        requestBody:
          {body_schema_docstring.replace("required: true", "required: false")}
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
                              description: New photometric series ID
        """
        with self.Session() as session:
            ps = session.scalars(
                PhotometricSeries.select(self.current_user).where(
                    PhotometricSeries.id == photometric_series_id
                )
            ).first()

            if ps is None:
                return self.error('Invalid photometric series ID.')

            json_data = self.get_json()
            data = json_data.pop('data', None)  # allowed to be None

            attributes_metadata = {}
            if isinstance(data, dict):
                try:
                    data = pd.DataFrame(data)
                except Exception:
                    return self.error(
                        f'Could not convert data to a DataFrame. {traceback.format_exc()} '
                    )
            elif isinstance(data, str):
                try:
                    data, attributes_metadata = load_dataframe_from_bytestream(data)
                except Exception:
                    return self.error(
                        f'Could not load DataFrame from HDF5 file. {traceback.format_exc()} '
                    )

            try:
                photometric_series_id = update_photometric_series(
                    ps,
                    json_data,
                    data,
                    attributes_metadata,
                    self.associated_user_object,
                    session,
                )
            except Exception as e:
                return self.error(f'Unable to update photometric series: {str(e)}')

            return self.success(data={'id': photometric_series_id})

    @permissions(['Upload data'])
    def get(self, photometric_series_id=None):
        """
        ---
        single:
          description: Retrieve a photometric series
          tags:
            - photometry
            - photometric series
          parameters:
            - in: path
              name: photometric_series_id
              required: true
              schema:
                type: integer
            - in: query
              name: dataFormat
              required: false
              default: 'json'
              schema:
                type: string
                enum: [json, hdf5, none]
              description: |
                Format of the data to return. If `none`, the data will not be returned.
                If `hdf5`, the data will be returned as a bytestream in HDF5 format.
                (to see how to unpack this data format, look at `photometric_series.md`)
                If `json`, the data will be returned as a JSON object, where each key
                is a list of values for that column.
          responses:
            200:
              content:
                application/json:
                  schema: SinglePhotometricSeries
        multiple:
          description: Retrieve all photometric series, based on various cuts.
          tags:
            - photometry
            - photometric series
          parameters:
            - in: query
              name: dataFormat
              required: false
              default: 'none'
              schema:
                type: string
                enum: [json, hdf5, none]
              description: |
                Format of the data to return. If `none`, the data will not be returned.
                If `hdf5`, the data will be returned as a bytestream in HDF5 format.
                (to see how to unpack this data format, look at `photometric_series.md`)
                If `json`, the data will be returned as a JSON object, where each key
                is a list of values for that column.
                Note that when querying multiple series, the actual data is not returned
                by default. To specifically request the data, use `dataFormat=json`
                or `dataFormat=hdf5`. Keep in mind this could be a large amount of data
                if the query arguments do not filter down the number of returned series.
            - in: query
              name: ra
              nullable: true
              schema:
                type: number
              description: RA for spatial filtering (in decimal degrees)
            - in: query
              name: dec
              nullable: true
              schema:
                type: number
              description: Declination for spatial filtering (in decimal degrees)
            - in: query
              name: radius
              nullable: true
              schema:
                type: number
              description: |
                Radius for spatial filtering if ra & dec
                are provided (in decimal degrees)
            - in: query
              name: objectID
              nullable: true
              schema:
                type: string
              description: Portion of ID to filter on
            - in: query
              name: rejectedObjectIDs
              nullable: true
              schema:
                type: str
              description: |
                Comma-separated string of object IDs not to be returned,
                useful in cases where you are looking for new objects passing a query.
            - in: query
              name: seriesName
              nullable: true
              schema:
                type: string
              description: |
                Get series that match this name.
                The match must be exact.
                This is useful when getting photometry
                for multiple objects taken at the same time
                (e.g., for calibrating against each other).
                The series name can be, e.g., a TESS sector,
                or a date/field name identifier.
                Generally a series name is shared only
                by data taken over that same time period.
            - in: query
              name: seriesObjID
              nullable: true
              schema:
                type: string
              description: |
                Get only photometry for the objects named by this object id.
                This is the internal naming used inside each photometric series,
                i.e., the index used for each source in the images that were
                used to create the photometric series. Not the same as the SkyPortal
                object ID. E.g., this could be a TESS TIC ID, or some internal numbering
                used in the specific field that was observed.
            - in: query
              name: filter
              nullable: true
              schema:
                type: string
              description: Retrieve only series matching this filter, e.g., "ztfg".
            - in: query
              name: channel
              nullable: true
              schema:
                type: string
              description: The channel name/id to filter on.
            - in: query
              name: origin
              nullable: true
              schema:
                type: string
              description: |
                The origin can be anything that gives an idea of the
                provenance of the photometric series.
                This can be, e.g., the name of the pipeline that
                produced the photometry from the images,
                or the level of calibration,
                or any other pre-defined string that identifies
                where the data came from that isn't covered by
                the other fields (like channel or filter or instrument).
            - in: query
              name: filename
              nullable: true
              schema:
                type: string
              description: |
                Portion of filename to filter on.
                If the filename is a relative path, will
                append the data directory from the config file
                to the beginning of the filename.
                (by default that is 'persistentdata/phot_series').
            - in: query
              name: startBefore
              nullable: true
              schema:
                type: string
              description: |
                Arrow-parseable date string (e.g. 2020-01-01). If provided, return
                only series that started before this time.
            - in: query
              name: startAfter
              nullable: true
              schema:
                type: string
              description: |
                Arrow-parseable date string (e.g. 2020-01-01). If provided, return
                only series that started after this time.
            - in: query
              name: midTimeBefore
              nullable: true
              schema:
                type: string
              description: |
                Arrow-parseable date string (e.g. 2020-01-01). If provided, return
                only series where the middle of the series was observed before this time.
            - in: query
              name: midTimeAfter
              nullable: true
              schema:
                type: string
              description: |
                Arrow-parseable date string (e.g. 2020-01-01). If provided, return
                only series where the middle of the series was observed after this time.
            - in: query
              name: endBefore
              nullable: true
              schema:
                type: string
              description: |
                Arrow-parseable date string (e.g. 2020-01-01). If provided, return
                only series that ended before this time.
            - in: query
              name: endAfter
              nullable: true
              schema:
                type: string
              description: |
                Arrow-parseable date string (e.g. 2020-01-01). If provided, return
                only series that ended after this time.
            - in: query
              name: detected
              nullable: true
              schema:
                type: boolean
              description: |
                If true, get only series with one or more detections.
                If false, get only series with no detections.
                If left out, do not filter at all on detection status.
            - in: query
              name: expTime
              nullable: true
              schema:
                type: number
              description: Get only series with this exact exposure time (seconds).
            - in: query
              name: minExpTime
              nullable: true
              schema:
                type: number
              description: |
                Get only series with an exposure time above/equal to this.
                If the series was not uploaded with one specific number,
                the exposure time for the series is the median of the
                exposure times of the individual images.
            - in: query
              name: maxExpTime
              nullable: true
              schema:
                type: number
              description: |
                Get only series with an exposure time under/equal to this.
                If the series was not uploaded with one specific number,
                the exposure time for the series is the median of the
                exposure times of the individual images.
            - in: query
              name: minFrameRate
              nullable: true
              schema:
                type: number
              description: |
                Get only series with a frame rate higher/equal to than this.
                Frame rates are the inverse of the median time between
                exposures, in units of 1/s (Hz).
            - in: query
              name: maxFrameRate
              nullable: true
              schema:
                type: number
              description: |
                Get only series with a frame rate lower/equal to than this.
                Frame rates are the inverse of the median time between
                exposures, in units of 1/s (Hz).
            - in: query
              name: minNumExposures
              nullable: true
              schema:
                type: number
              description: |
                Get only series with this many exposures, or more.
            - in: query
              name: maxNumExposures
              nullable: true
              schema:
                type: number
              description: |
                Get only series with this many exposures, or less.
            - in: query
              name: instrumentID
              nullable: true
              schema:
                type: number
              description: get only series taken with this instrument.
            - in: query
              name: followupRequestID
              nullable: true
              schema:
                type: number
              description: get only series taken with this followup request.
            - in: query
              name: assignmentID
              nullable: true
              schema:
                type: number
              description: get only series taken with this assignment.
            - in: query
              name: ownerID
              nullable: true
              schema:
                type: number
              description: get only series uploaded by this user.
            - in: query
              name: magBrighterThan
              nullable: true
              schema:
                type: number
              description: get only series with mean_mag brighter or equal to this value.
            - in: query
              name: magFainterThan
              nullable: true
              schema:
                type: number
              description: get only series with mean_mag fainter or equal to this value.
            - in: query
              name: limitingMagBrighterThan
              nullable: true
              schema:
                type: number
              description: |
                Retrieve only series with limiting mags brighter or equal to this value.
            - in: query
              name: limitingMagFainterThan
              nullable: true
              schema:
                type: number
              description: |
                Retrieve only series with limiting mags fainter or equal to this value.
            - in: query
              name: limitingMagIsNone
              nullable: true
              schema:
                  type: boolean
              description: |
                  Retrieve only series that do not have limiting mag.
            - in: query
              name: magrefBrighterThan
              nullable: true
              schema:
                type: number
              description: |
                Get only series that have a magref,
                and that the magref is brighter or equal to this value.
            - in: query
              name: magrefFainterThan
              nullable: true
              schema:
                type: number
              description: |
                Get only series that have a magref,
                and that the magref is fainter or equal to this value.
            - in: query
              name: maxRMS
              nullable: true
              schema:
                type: number
              description: get only series with rms_mag less than this.
            - in: query
              name: minRMS
              nullable: true
              schema:
                type: number
              description: get only series with rms_mag more than this.
            - in: query
              name: useRobustMagAndRMS
              nullable: true
              default: false
              schema:
                type: boolean
              description: |
                If true, will use the robust_mag and robust_rms values
                instead of mean_mag and rms_mag when filtering on mean
                magnitude or RMS. Does not affect the magref query.
            - in: query
              name: maxMedianSNR
              nullable: true
              schema:
                type: number
              description: |
                Get only series where the median S/N is less than this.
                The S/N is calculated using the robust RMS.
            - in: query
              name: minMedianSNR
              nullable: true
              schema:
                type: number
              description: |
                Get only series where the median S/N is more than this.
                The S/N is calculated using the robust RMS.
            - in: query
              name: maxBestSNR
              nullable: true
              schema:
                type: number
              description: |
                Get only series where the maximum S/N is less than this.
                The S/N is calculated using the robust RMS.
            - in: query
              name: minBestSNR
              nullable: true
              schema:
                type: number
              description: |
                Get only series where the maximum S/N is more than this.
                The S/N is calculated using the robust RMS.
            - in: query
              name: maxWorstSNR
              nullable: true
              schema:
                type: number
              description: |
                Get only series where the lowest S/N is less than this.
                The S/N is calculated using the robust RMS.
            - in: query
              name: minWorstSNR
              nullable: true
              schema:
                type: number
              description: |
                Get only series where the lowest S/N is more than this.
                The S/N is calculated using the robust RMS.
            - in: query
              name: hash
              nullable: true
              schema:
                type: string
              description: |
                Get only a series that matches this file hash.
                This is useful if you have an HDF5 file downloaded
                from the SkyPortal backend, and want to associate it
                with a PhotometrySeries object.
                We use an MD5 hash of the file contents.
            - in: query
              name: sortBy
              nullable: true
              default: obj_id
              schema:
                type: string
              description: |
                The field to sort by. Currently allowed options are ["id", "ra", "dec", "redshift", "saved_at"]
            - in: query
              name: sortOrder
              nullable: true
              default: asc
              schema:
                type: string
              description: |
                The sort order - either "asc" or "desc". Defaults to "asc"
            - in: query
              name: numPerPage
              nullable: true
              schema:
                type: integer
              description: |
                Number of sources to return per paginated request.
                Defaults to 100. Max 500.
            - in: query
              name: pageNumber
              nullable: true
              schema:
                type: integer
              description: Page number for paginated query results. Defaults to 1
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
                              series:
                                type: array
                                items:
                                  $ref: '#/components/schemas/PhotometricSeries'
                              totalMatches:
                                type: integer
                              pageNumber:
                                type: integer
                              numPerPage:
                                type: integer
        """
        if photometric_series_id is not None:
            with self.Session() as session:
                ps = session.scalars(
                    PhotometricSeries.select(self.current_user).where(
                        PhotometricSeries.id == photometric_series_id
                    )
                ).first()
                if ps is None:
                    return self.error('Invalid photometric series ID.')
                data_format = self.get_query_argument('dataFormat', 'json')

                try:
                    output_dict = ps.to_dict(data_format=data_format)
                except Exception:
                    return self.error(
                        f'Cannot convert photometric series to dictionary: {traceback.format_exc()}'
                    )

                return self.success(data=output_dict)

        # get all photometric series
        data_format = self.get_query_argument('dataFormat', 'none')

        # verify the format is valid before going through the whole query
        if data_format.lower() not in ['none', 'json', 'hdf5']:
            return self.error(
                f'Invalid dataFormat: "{data_format}". Must be one of "none", "json", "hdf5".'
            )
        ra = self.get_query_argument('ra', None)
        dec = self.get_query_argument('dec', None)
        radius = self.get_query_argument('radius', None)
        object_id = self.get_query_argument('objectID', None)
        rejected_id = self.get_query_argument('rejectedObjectID', None)
        series_name = self.get_query_argument('seriesName', None)
        series_obj_id = self.get_query_argument('seriesObjID', None)
        filter = self.get_query_argument('filter', None)
        channel = self.get_query_argument('channel', None)
        origin = self.get_query_argument('origin', None)
        filename = self.get_query_argument('filename', None)
        start_before = self.get_query_argument('startBefore', None)
        start_after = self.get_query_argument('startAfter', None)
        middle_before = self.get_query_argument('midBefore', None)
        middle_after = self.get_query_argument('midAfter', None)
        end_before = self.get_query_argument('endBefore', None)
        end_after = self.get_query_argument('endAfter', None)
        detected = self.get_query_argument('detected', None)
        exp_time_exact = self.get_query_argument('expTime', None)
        min_exp_time = self.get_query_argument('minExpTime', None)
        max_exp_time = self.get_query_argument('maxExpTime', None)
        min_frame_rate = self.get_query_argument('minFrameRate', None)
        max_frame_rate = self.get_query_argument('maxFrameRate', None)
        min_num_exp = self.get_query_argument('minNumExposures', None)
        max_num_exp = self.get_query_argument('maxNumExposures', None)
        instrument_id = self.get_query_argument('instrumentID', None)
        followup_id = self.get_query_argument('followupRequestID', None)
        assignment_id = self.get_query_argument('assignmentID', None)
        owner_id = self.get_query_argument('ownerID', None)
        mag_brighter = self.get_query_argument('magBrighterThan', None)
        mag_fainter = self.get_query_argument('magFainterThan', None)
        lim_mag_brighter = self.get_query_argument('limitingMagBrighterThan', None)
        lim_mag_fainter = self.get_query_argument('limitingMagFainterThan', None)
        lim_mag_none = self.get_query_argument('limitingMagIsNaN', False)
        magref_brighter = self.get_query_argument('magrefBrighterThan', None)
        magref_fainter = self.get_query_argument('magrefFainterThan', None)
        max_rms = self.get_query_argument('maxRMS', None)
        min_rms = self.get_query_argument('minRMS', None)
        use_robust = self.get_query_argument('useRobustMagAndRMS', False)
        min_median_snr = self.get_query_argument('minMedianSNR', None)
        max_median_snr = self.get_query_argument('maxMedianSNR', None)
        min_best_snr = self.get_query_argument('minBestSNR', None)
        max_best_snr = self.get_query_argument('maxBestSNR', None)
        min_worst_snr = self.get_query_argument('minWorstSNR', None)
        max_worst_snr = self.get_query_argument('maxWorstSNR', None)
        hash = self.get_query_argument('hash', None)
        sort_by = self.get_query_argument('sortBy', 'obj_id')
        sort_order = self.get_query_argument('sortOrder', 'asc')
        page_number = self.get_query_argument('pageNumber', 1)
        num_per_page = min(
            int(self.get_query_argument("numPerPage", DEFAULT_SERIES_PER_PAGE)),
            MAX_SERIES_PER_PAGE,
        )

        stmt = PhotometricSeries.select(self.current_user)

        if ra is not None and dec is not None and radius is not None:
            try:
                ra = float(ra)
                dec = float(dec)
                radius = float(radius)
            except ValueError:
                return self.error(
                    "Invalid values for ra, dec or radius - could not convert to float"
                )
            if ra > 360 or ra < 0 or dec > 90 or dec < -90:
                return self.error(f"Invalid values for ra ({ra}) or dec ({dec})")

            other = ca.Point(ra=ra, dec=dec)
            stmt = stmt.where(PhotometricSeries.within(other, radius))

        if object_id:
            stmt = stmt.where(PhotometricSeries.obj_id.contains(str(object_id).strip()))
        if rejected_id:
            rejected_id = rejected_id.split(',')
            rejected_id = [x.strip() for x in rejected_id]
            stmt = stmt.where(PhotometricSeries.obj_id.notin_(rejected_id))

        if series_name:
            stmt = stmt.where(PhotometricSeries.series_name == series_name.strip())
        if series_obj_id:
            stmt = stmt.where(PhotometricSeries.series_obj_id == series_obj_id.strip())
        if filter:
            stmt = stmt.where(PhotometricSeries.filter == filter)
        if channel:
            stmt = stmt.where(PhotometricSeries.channel == channel)
        if origin:
            stmt = stmt.where(PhotometricSeries.origin == origin)

        if filename:
            persistent_folder = cfg.get(
                'photometric_series_folder', 'persistentdata/phot_series'
            )
            basedir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
            )
            root_folder = os.path.join(basedir, persistent_folder)
            if filename.startswith(root_folder):
                pass
            elif filename.startswith(persistent_folder):
                filename = os.path.join(basedir, filename)
            else:
                filename = os.path.join(root_folder, filename)

            stmt = stmt.where(PhotometricSeries.filename == filename)

        if start_after is not None:
            try:
                start_after_mjd = Time(arrow.get(start_after).datetime).mjd
            except Exception:
                return self.error(
                    f'Cannot parse time {start_after}: {traceback.format_exc()}'
                )
            stmt = stmt.where(PhotometricSeries.mjd_first > start_after_mjd)
        if start_before is not None:
            try:
                start_before_mjd = Time(arrow.get(start_before).datetime).mjd
            except Exception:
                return self.error(
                    f'Cannot parse time {start_before}: {traceback.format_exc()}'
                )
            stmt = stmt.where(PhotometricSeries.mjd_first < start_before_mjd)
        if middle_after is not None:
            try:
                middle_after_mjd = Time(arrow.get(middle_after).datetime).mjd
            except Exception:
                return self.error(
                    f'Cannot parse time {middle_after}: {traceback.format_exc()}'
                )
            stmt = stmt.where(PhotometricSeries.mjd_mid > middle_after_mjd)
        if middle_before is not None:
            try:
                middle_before_mjd = Time(arrow.get(middle_before).datetime).mjd
            except Exception:
                return self.error(
                    f'Cannot parse time {middle_before}: {traceback.format_exc()}'
                )
            stmt = stmt.where(PhotometricSeries.mjd_mid < middle_before_mjd)
        if end_after is not None:
            try:
                end_after_mjd = Time(arrow.get(end_after).datetime).mjd
            except Exception:
                return self.error(
                    f'Cannot parse time {end_after}: {traceback.format_exc()}'
                )
            stmt = stmt.where(PhotometricSeries.mjd_last > end_after_mjd)
        if end_before is not None:
            try:
                end_before_mjd = Time(arrow.get(end_before).datetime).mjd
            except Exception:
                return self.error(
                    f'Cannot parse time {end_before}: {traceback.format_exc()}'
                )
            stmt = stmt.where(PhotometricSeries.mjd_last < end_before_mjd)

        if detected is not None:
            if isinstance(detected, str) and detected.lower() in ['true', 't', '1']:
                detected = True
            elif isinstance(detected, str) and detected.lower() in ['false', 'f', '0']:
                detected = False

            try:
                detected = bool(detected)
            except ValueError:
                return self.error(
                    f'Cannot parse detected value {detected}: {traceback.format_exc()}'
                )
            stmt = stmt.where(PhotometricSeries.is_detected.is_(detected))

        if exp_time_exact is not None:
            try:
                exp_time_exact = float(exp_time_exact)
            except ValueError:
                return self.error(
                    f'Invalid value for expTimeExact {exp_time_exact}. '
                    'Could not convert to float. '
                )
            stmt = stmt.where(PhotometricSeries.exp_time == exp_time_exact)

        if min_exp_time is not None:
            try:
                min_exp_time = float(min_exp_time)
            except ValueError:
                return self.error(
                    f'Invalid value for minExpTime {min_exp_time}. '
                    'Could not convert to float. '
                )
            stmt = stmt.where(PhotometricSeries.exp_time >= min_exp_time)

        if max_exp_time is not None:
            try:
                max_exp_time = float(max_exp_time)
            except ValueError:
                return self.error(
                    f'Invalid value for maxExpTime {max_exp_time}. '
                    'Could not convert to float. '
                )
            stmt = stmt.where(PhotometricSeries.exp_time <= max_exp_time)

        if min_frame_rate is not None:
            try:
                min_frame_rate = float(min_frame_rate)
            except ValueError:
                return self.error(
                    f'Invalid value for minFrameRate {min_frame_rate}. '
                    'Could not convert to float. '
                )
            stmt = stmt.where(PhotometricSeries.frame_rate >= min_frame_rate)

        if max_frame_rate is not None:
            try:
                max_frame_rate = float(max_frame_rate)
            except ValueError:
                return self.error(
                    f'Invalid value for maxFrameRate {max_frame_rate}. '
                    'Could not convert to float. '
                )
            stmt = stmt.where(PhotometricSeries.frame_rate <= max_frame_rate)

        if min_num_exp is not None:
            try:
                min_num_exp = int(min_num_exp)
            except ValueError:
                return self.error(
                    f'Invalid value for minNumExposures {min_num_exp}. '
                    'Could not convert to int. '
                )
            stmt = stmt.where(PhotometricSeries.num_exp >= min_num_exp)

        if max_num_exp is not None:
            try:
                max_num_exp = int(max_num_exp)
            except ValueError:
                return self.error(
                    f'Invalid value for maxNumExposures {max_num_exp}. '
                    'Could not convert to int. '
                )
            stmt = stmt.where(PhotometricSeries.num_exp <= max_num_exp)

        if instrument_id is not None:
            try:
                instrument_id = int(instrument_id)
            except ValueError:
                return self.error(
                    f'Invalid value for instrumentId {instrument_id}. '
                    'Could not convert to int. '
                )
            stmt = stmt.where(PhotometricSeries.instrument_id == instrument_id)

        if followup_id is not None:
            try:
                followup_id = int(followup_id)
            except ValueError:
                return self.error(
                    f'Invalid value for followupId {followup_id}. '
                    'Could not convert to int. '
                )
            stmt = stmt.where(PhotometricSeries.followup_request_id == followup_id)

        if assignment_id is not None:
            try:
                assignment_id = int(assignment_id)
            except ValueError:
                return self.error(
                    f'Invalid value for assignmentId {assignment_id}. '
                    'Could not convert to int. '
                )
            stmt = stmt.where(PhotometricSeries.assignment_id == assignment_id)

        if owner_id is not None:
            try:
                owner_id = int(owner_id)
            except ValueError:
                return self.error(
                    f'Invalid value for ownerId {owner_id}. '
                    'Could not convert to int. '
                )
            stmt = stmt.where(PhotometricSeries.owner_id == owner_id)

        if mag_fainter is not None:
            try:
                mag_fainter = float(mag_fainter)
            except ValueError:
                return self.error(
                    f'Invalid value for magFainterThan {mag_fainter}. '
                    'Could not convert to float. '
                )
            if use_robust:
                stmt = stmt.where(PhotometricSeries.robust_mag >= mag_fainter)
            else:
                stmt = stmt.where(PhotometricSeries.mean_mag >= mag_fainter)

        if mag_brighter is not None:
            try:
                mag_brighter = float(mag_brighter)
            except ValueError:
                return self.error(
                    f'Invalid value for magBrighterThan {mag_brighter}. '
                    'Could not convert to float. '
                )
            if use_robust:
                stmt = stmt.where(PhotometricSeries.robust_mag <= mag_brighter)
            else:
                stmt = stmt.where(PhotometricSeries.mean_mag <= mag_brighter)

        if lim_mag_fainter is not None:
            try:
                lim_mag_fainter = float(lim_mag_fainter)
            except ValueError:
                return self.error(
                    f'Invalid value for limMagFainterThan {lim_mag_fainter}. '
                    'Could not convert to float. '
                )
            stmt = stmt.where(PhotometricSeries.limiting_mag >= lim_mag_fainter)

        if lim_mag_brighter is not None:
            try:
                lim_mag_brighter = float(lim_mag_brighter)
            except ValueError:
                return self.error(
                    f'Invalid value for limMagBrighterThan {lim_mag_brighter}. '
                    'Could not convert to float. '
                )
            stmt = stmt.where(PhotometricSeries.limiting_mag <= lim_mag_brighter)

        if lim_mag_none:
            stmt = stmt.where(PhotometricSeries.limiting_mag.is_(None))

        if magref_fainter is not None:
            try:
                magref_fainter = float(magref_fainter)
            except ValueError:
                return self.error(
                    f'Invalid value for magrefFainterThan {magref_fainter}. '
                    'Could not convert to float. '
                )
            stmt = stmt.where(PhotometricSeries.magref >= magref_fainter)

        if magref_brighter is not None:
            try:
                magref_brighter = float(magref_brighter)
            except ValueError:
                return self.error(
                    f'Invalid value for magrefBrighterThan {magref_brighter}. '
                    'Could not convert to float. '
                )
            stmt = stmt.where(PhotometricSeries.magref <= magref_brighter)

        if max_rms is not None:
            try:
                max_rms = float(max_rms)
            except ValueError:
                return self.error(
                    f'Invalid value for maxRMS {max_rms}. '
                    'Could not convert to float. '
                )
            if use_robust:
                stmt = stmt.where(PhotometricSeries.robust_rms <= max_rms)
            else:
                stmt = stmt.where(PhotometricSeries.rms_mag <= max_rms)

        if min_rms is not None:
            try:
                min_rms = float(min_rms)
            except ValueError:
                return self.error(
                    f'Invalid value for minRMS {min_rms}. '
                    'Could not convert to float. '
                )
            if use_robust:
                stmt = stmt.where(PhotometricSeries.robust_rms >= min_rms)
            else:
                stmt = stmt.where(PhotometricSeries.rms_mag >= min_rms)

        if min_median_snr is not None:
            try:
                min_median_snr = float(min_median_snr)
            except ValueError:
                return self.error(
                    f'Invalid value for minMedianSNR {min_median_snr}. '
                    'Could not convert to float. '
                )
            stmt = stmt.where(PhotometricSeries.median_snr >= min_median_snr)

        if max_median_snr is not None:
            try:
                max_median_snr = float(max_median_snr)
            except ValueError:
                return self.error(
                    f'Invalid value for maxMedianSNR {max_median_snr}. '
                    'Could not convert to float. '
                )
            stmt = stmt.where(PhotometricSeries.median_snr <= max_median_snr)

        if min_best_snr is not None:
            try:
                min_best_snr = float(min_best_snr)
            except ValueError:
                return self.error(
                    f'Invalid value for minBestSNR {min_best_snr}. '
                    'Could not convert to float. '
                )
            stmt = stmt.where(PhotometricSeries.best_snr >= min_best_snr)

        if max_best_snr is not None:
            try:
                max_best_snr = float(max_best_snr)
            except ValueError:
                return self.error(
                    f'Invalid value for maxBestSNR {max_best_snr}. '
                    'Could not convert to float. '
                )
            stmt = stmt.where(PhotometricSeries.best_snr <= max_best_snr)

        if min_worst_snr is not None:
            try:
                min_worst_snr = float(min_worst_snr)
            except ValueError:
                return self.error(
                    f'Invalid value for minWorstSNR {min_worst_snr}. '
                    'Could not convert to float. '
                )
            stmt = stmt.where(PhotometricSeries.worst_snr >= min_worst_snr)

        if max_worst_snr is not None:
            try:
                max_worst_snr = float(max_worst_snr)
            except ValueError:
                return self.error(
                    f'Invalid value for maxWorstSNR {max_worst_snr}. '
                    'Could not convert to float. '
                )
            stmt = stmt.where(PhotometricSeries.worst_snr <= max_worst_snr)

        if hash is not None:
            stmt = stmt.where(PhotometricSeries.hash == hash)

        try:
            # add any additional enums to this list:
            if sort_by in ['filter']:
                # sorting enums is done by default using their order in the original
                # definition, which is not alphabetical order (which is what the user expects)
                # ref: https://stackoverflow.com/a/23618085
                whens = {
                    name: name
                    for name in getattr(PhotometricSeries, sort_by).type.enums
                }
                order_by_column = case(whens, value=getattr(PhotometricSeries, sort_by))
            else:
                order_by_column = getattr(PhotometricSeries, sort_by)
        except AttributeError:
            return self.error(
                f'Invalid value for sortBy {sort_by}. Could not find column. '
            )

        if sort_order not in ['asc', 'desc']:
            return self.error(
                f'Invalid value "{sort_order}" for sortOrder. '
                'Must be "asc" or "desc". '
            )
        if sort_order == 'desc':
            order_by_column = order_by_column.desc()

        stmt = stmt.order_by(order_by_column)

        try:
            page_number = max(int(page_number), 1)
        except ValueError:
            return self.error(f'Invalid value "{page_number}" for pageNumber. ')

        try:
            num_per_page = int(num_per_page)
        except ValueError:
            return self.error(f'Invalid value "{num_per_page}" for numPerPage. ')

        if num_per_page > MAX_SERIES_PER_PAGE:
            return self.error(
                f'Invalid value "{num_per_page}" for numPerPage. '
                f'Maximum value is {MAX_SERIES_PER_PAGE}. '
            )

        with self.Session() as session:
            count_stmt = sa.select(func.count()).select_from(stmt)
            total_matches = session.execute(count_stmt).scalar()
            stmt = stmt.offset((page_number - 1) * num_per_page)
            stmt = stmt.limit(num_per_page)
            series = session.scalars(stmt).unique().all()

            try:
                results = {
                    'series': [s.to_dict(data_format) for s in series],
                    'totalMatches': total_matches,
                    'numPerPage': num_per_page,
                    'pageNumber': page_number,
                }
            except Exception:
                return self.error(
                    f'Could not convert series to dict {traceback.format_exc()}'
                )
            return self.success(data=results)

    @permissions(['Upload data'])
    def delete(self, photometric_series_id):
        """
        ---
        description: Delete a photometric series
        tags:
          - photometry
          - photometric series
        parameters:
          - in: path
            name: photometric_series_id
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
            ps = session.scalars(
                PhotometricSeries.select(session.user_or_token, mode="delete").where(
                    PhotometricSeries.id == photometric_series_id
                )
            ).first()

            if ps is None:
                return self.error(
                    f'Cannot find photometry point with ID: {photometric_series_id}.'
                )

            obj_id = ps.obj_id

            session.delete(ps)
            session.commit()

            self.push_all(
                action="skyportal/REFRESH_SOURCE_PHOTOMETRY",
                payload={"obj_id": obj_id},
            )

            return self.success()
