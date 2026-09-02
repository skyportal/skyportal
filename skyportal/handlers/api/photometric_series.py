import operator
import os
import traceback
from contextlib import contextmanager

import arrow
import conesearch_alchemy as ca
import pandas as pd
import sqlalchemy as sa
from astropy.time import Time
from marshmallow.exceptions import ValidationError
from skyportal_py_models.photometric_series import (
    PhotometricSeriesGetQuery,
    PhotometricSeriesPatchBody,
    PhotometricSeriesPostBody,
    PhotometricSeriesResponse,
)
from sqlalchemy import func
from sqlalchemy.sql.expression import case

from baselayer.app.access import permissions  # , auth_or_token
from baselayer.app.env import load_env
from baselayer.log import make_log

from ...enum_types import ALLOWED_BANDPASSES
from ...models.assignment import ClassicalAssignment
from ...models.followup_request import FollowupRequest
from ...models.group import Group
from ...models.instrument import Instrument
from ...models.obj import Obj
from ...models.photometric_series import (
    PhotometricSeries,
    infer_metadata,
    verify_data,
    verify_metadata,
)
from ...models.stream import Stream
from ...utils.data_access import default_share_public_group_name
from ...utils.hdf5_files import load_dataframe_from_bytestream
from ..base import BaseHandler

_, cfg = load_env()


log = make_log("api/photometric_series")

MAX_SERIES_PER_PAGE = 500


@contextmanager
def reraise(message):
    """Re-raise anything as a ValueError prefixed by `message`, with the traceback."""
    try:
        yield
    except Exception:
        raise ValueError(f"{message}: {traceback.format_exc()}")


def parse_series_data(data):
    """Coerce a request's `data` into a DataFrame, plus any metadata carried by an
    HDF5 bytestream. Anything that is neither a dict nor a string is passed through."""
    if isinstance(data, dict):
        with reraise("Could not convert data to a DataFrame"):
            return pd.DataFrame(data), {}
    if isinstance(data, str):
        with reraise("Could not load DataFrame from HDF5 file"):
            return load_dataframe_from_bytestream(data)
    return data, {}


def get_group_ids(data, user, session):
    """Group IDs of `data`, resolving "all" to the public group and always
    including the user's single user group."""
    group_ids = data.pop("group_ids", [])
    if isinstance(group_ids, str) and group_ids == "all":
        public_group = session.scalars(
            sa.select(Group).where(Group.name == cfg["misc.public_group_name"])
        ).first()
        group_ids = [public_group.id]
    if isinstance(group_ids, int | str):
        group_ids = [group_ids]
    if not isinstance(group_ids, list | tuple):
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
            raise ValidationError(f"Invalid group ID: {group_id}")

    if not group_ids:
        # no groups specified: share with the configured default groups
        public_group_name = default_share_public_group_name()
        if public_group_name is not None:
            public_group = session.scalars(
                sa.select(Group).where(Group.name == public_group_name)
            ).first()
            if public_group is not None:
                group_ids = [public_group.id]

    # always add the single user group
    group_ids.append(user.single_user_group.id)
    group_ids = list(set(group_ids))
    return group_ids


def get_stream_ids(data, user, session):
    """Unique stream IDs of `data`, checking each one is accessible."""
    stream_ids = data.pop("stream_ids", [])
    if not isinstance(stream_ids, list | tuple):
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
            raise ValidationError(f"No stream with ID {stream_id}")

    stream_ids = list(set(stream_ids))
    return stream_ids


def individual_enum_checks(metadata):
    """Raise a ValueError if an enum-backed metadata value is not allowed."""
    if metadata["filter"] not in ALLOWED_BANDPASSES:
        raise ValueError(
            f"Filter {metadata['filter']} is not allowed. "
            f"Allowed filters are: {ALLOWED_BANDPASSES}"
        )

    tsa = metadata.get("time_stamp_alignment", "middle")
    if tsa not in ["start", "middle", "end"]:
        raise ValueError(
            f"Time stamp alignment {tsa} is not allowed. "
            f"Allowed values are: start, middle, end"
        )


def check_objects_exist(metadata, user, session):
    """Raise a ValueError if any object `metadata` refers to is missing or inaccessible."""
    obj_id = metadata.get("obj_id", None)
    if obj_id is None:
        raise ValueError("Must supply an obj_id")
    obj = session.scalars(Obj.select(user).where(Obj.id == obj_id)).first()
    if obj is None:
        raise ValueError(f"Invalid obj_id: {obj_id}")

    instrument_id = metadata.get("instrument_id")

    if instrument_id is None:
        raise ValueError("Must supply an instrument_id")

    instrument = session.scalars(
        Instrument.select(user).where(Instrument.id == instrument_id)
    ).first()
    if instrument is None:
        raise ValueError(f"Invalid instrument_id: {instrument_id}")

    followup_request_id = metadata.get("followup_request_id")
    if followup_request_id is not None:
        followup_request = session.scalars(
            FollowupRequest.select(user).where(
                FollowupRequest.id == followup_request_id
            )
        ).first()
        if followup_request is None:
            raise ValueError(f"Invalid followup_request_id: {followup_request_id}")

    assignment_id = metadata.get("assignment_id")
    if assignment_id is not None:
        assignment = session.scalars(
            ClassicalAssignment.select(user).where(
                ClassicalAssignment.id == assignment_id
            )
        ).first()
        if assignment is None:
            raise ValueError(f"Invalid assignment_id: {assignment_id}")


def resolve_metadata(metadata, user, session, owner_id):
    """Validate the DB objects `metadata` refers to and return it fully parsed,
    alongside the resolved group and stream IDs."""
    with reraise("Could not parse group IDs"):
        group_ids = get_group_ids(metadata, user, session)
    with reraise("Could not parse stream IDs"):
        stream_ids = get_stream_ids(metadata, user, session)
    with reraise("Problems accessing database objects"):
        check_objects_exist(metadata, user, session)

    with reraise("Problem parsing data/metadata"):
        metadata.update(
            {
                "group_ids": group_ids,
                "stream_ids": stream_ids,
                "owner_id": owner_id,
            }
        )
        metadata = verify_metadata(metadata)

    with reraise("Problem parsing metadata"):
        individual_enum_checks(metadata)

    return metadata, group_ids, stream_ids


def assign_groups_and_streams(ps, group_ids, stream_ids, session):
    ps.groups = session.scalars(sa.select(Group).where(Group.id.in_(group_ids))).all()
    ps.streams = session.scalars(
        sa.select(Stream).where(Stream.id.in_(stream_ids))
    ).all()


def post_photometric_series(json_data, data, attributes_metadata, user, session):
    """Create a PhotometricSeries from `data` and the merged metadata, and return its ID."""
    with reraise("Problem parsing data/metadata"):
        verify_data(data)
        metadata = infer_metadata(data)
        metadata.update(attributes_metadata)
        metadata.update(json_data)
        metadata = {k: v for k, v in metadata.items() if v is not None}

    metadata, group_ids, stream_ids = resolve_metadata(metadata, user, session, user.id)

    with reraise("Could not create PhotometricSeries object"):
        ps = PhotometricSeries(data, **metadata)
        ps.autodelete = cfg.get("photometric_series_autodelete", True)

    with reraise("Errors when making file name"):
        full_name, _ = ps.make_full_name()

    if os.path.isfile(full_name):
        existing_ps = session.scalars(
            sa.select(PhotometricSeries).where(PhotometricSeries.filename == full_name)
        ).first()
        if existing_ps is not None:
            raise ValueError(
                f"PhotometricSeries with filename {full_name} already exists"
            )
        # the file exists but is not in the DB, so it is safe to overwrite
        os.remove(full_name)

    existing_ps = session.scalars(
        sa.select(PhotometricSeries).where(PhotometricSeries.hash == ps.hash)
    ).first()
    if existing_ps is not None:
        raise ValueError(
            "A PhotometricSeries with the same hash already exists, "
            f"with filename: {existing_ps.make_full_name()[0]}"
        )

    try:
        ps.save_data()
        session.add(ps)
        assign_groups_and_streams(ps, group_ids, stream_ids, session)
        session.commit()
        return ps.id
    except Exception:
        session.rollback()
        ps.delete_data()  # make sure not to leave files behind
        raise ValueError(f"Could not save photometric series: {traceback.format_exc()}")


def update_photometric_series(ps, json_data, data, attributes_metadata, user, session):
    """Update `ps` in place from `data` and the merged metadata, and return its ID."""
    inferred_metadata = {}
    if data is not None:
        with reraise("Problem parsing data/metadata"):
            verify_data(data)
            inferred_metadata = infer_metadata(data)

    prev_filename = ps.filename

    # apply parameters from existing, inferred, bytes stream, and json body.
    metadata = ps.get_metadata()
    metadata.update(inferred_metadata)
    metadata.update(attributes_metadata)
    metadata.update(json_data)

    metadata, group_ids, stream_ids = resolve_metadata(
        metadata, user, session, ps.owner_id
    )

    if data is not None:
        with reraise("Could not update data"):
            ps.data = data  # also run calc_flux_mag() and calc_stats()

    for k, v in metadata.items():
        setattr(ps, k, v)

    assign_groups_and_streams(ps, group_ids, stream_ids, session)

    with reraise("Errors when making file name"):
        full_name, _ = ps.make_full_name()

    if prev_filename != full_name and os.path.isfile(full_name):
        raise ValueError(f"New filename already exists: {full_name}")

    existing_ps = session.scalars(
        sa.select(PhotometricSeries).where(
            PhotometricSeries.hash == ps.hash, PhotometricSeries.id != ps.id
        )
    ).first()
    if existing_ps is not None:
        raise ValueError(
            "Another PhotometricSeries with the same hash already exists, "
            f"with filename: {existing_ps.make_full_name()[0]}"
        )

    try:
        ps.save_data(temp=True)
        session.add(ps)
        session.commit()
    except Exception:
        session.rollback()
        ps.delete_data(temp=True)  # make sure not to leave files behind
        raise ValueError(f"Could not save photometric series: {traceback.format_exc()}")

    try:
        if os.path.isfile(prev_filename):
            os.remove(prev_filename)
    except Exception:
        log(f"Could not remove old file {prev_filename}: {traceback.format_exc()}")
    ps.move_temp_data()  # make the temp file permanent

    return ps.id


class PhotometricSeriesHandler(BaseHandler):
    @permissions(["Upload data"])
    async def post(
        self, *, body: PhotometricSeriesPostBody = None
    ) -> PhotometricSeriesResponse:
        """
        ---
        summary: Upload a photometric series.
        description: Upload a photometric series.
        tags:
          - photometric series
        """
        body = self.parse_body(PhotometricSeriesPostBody)
        json_data = body.model_dump(exclude_unset=True)
        data = json_data.pop("data", None)
        if data is None:
            return self.error(
                "Must supply data as a dictionary (JSON) or dataframe in HDF5 format. "
            )
        if not isinstance(data, dict | str):
            return self.error(
                "Data must be a dictionary (JSON) or dataframe in HDF5 format. "
            )

        try:
            data, attributes_metadata = parse_series_data(data)
        except ValueError as e:
            return self.error(str(e))

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
                return self.error(f"Unable to post photometric series: {str(e)}")

        return self.success(data={"id": photometric_series_id})

    @permissions(["Upload data"])
    async def patch(
        self, photometric_series_id: int, *, body: PhotometricSeriesPatchBody = None
    ) -> PhotometricSeriesResponse:
        """
        ---
        summary: Update a photometric series.
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
          - photometric series
        """
        body = self.parse_body(PhotometricSeriesPatchBody)
        with self.Session() as session:
            ps = session.scalars(
                PhotometricSeries.select(self.current_user).where(
                    PhotometricSeries.id == photometric_series_id
                )
            ).first()

            if ps is None:
                return self.error("Invalid photometric series ID.")

            json_data = body.model_dump(exclude_unset=True)
            data = json_data.pop("data", None)  # allowed to be None

            try:
                data, attributes_metadata = parse_series_data(data)
            except ValueError as e:
                return self.error(str(e))

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
                return self.error(f"Unable to update photometric series: {str(e)}")

            return self.success(data={"id": photometric_series_id})

    @permissions(["Upload data"])
    async def get(
        self,
        photometric_series_id: int | None = None,
        *,
        query: PhotometricSeriesGetQuery = None,
    ):
        """
        ---
        single:
          summary: Retrieve a photometric series
          description: Retrieve a photometric series
          tags:
            - photometric series
          responses:
            200:
              content:
                application/json:
                  schema: SinglePhotometricSeries
        multiple:
          summary: Retrieve multiple photometric series
          description: Retrieve all photometric series, based on various cuts.
          tags:
            - photometric series
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
        query = self.parse_query(PhotometricSeriesGetQuery)

        if photometric_series_id is not None:
            with self.Session() as session:
                ps = session.scalars(
                    PhotometricSeries.select(self.current_user).where(
                        PhotometricSeries.id == photometric_series_id
                    )
                ).first()
                if ps is None:
                    return self.error("Invalid photometric series ID.")
                data_format = "json" if query.dataFormat is None else query.dataFormat

                try:
                    output_dict = ps.to_dict(data_format=data_format)
                except Exception:
                    return self.error(
                        f"Cannot convert photometric series to dictionary: {traceback.format_exc()}"
                    )

                return self.success(data=output_dict)

        # get all photometric series
        data_format = "none" if query.dataFormat is None else query.dataFormat

        stmt = PhotometricSeries.select(self.current_user)

        if query.ra is not None and query.dec is not None and query.radius is not None:
            ra = query.ra
            dec = query.dec
            if ra > 360 or ra < 0 or dec > 90 or dec < -90:
                return self.error(f"Invalid values for ra ({ra}) or dec ({dec})")

            other = ca.Point(ra=ra, dec=dec)
            stmt = stmt.where(PhotometricSeries.within(other, query.radius))

        if query.objectID:
            stmt = stmt.where(
                PhotometricSeries.obj_id.contains(str(query.objectID).strip())
            )
        if query.rejectedObjectID:
            rejected_id = [x.strip() for x in query.rejectedObjectID.split(",")]
            stmt = stmt.where(PhotometricSeries.obj_id.notin_(rejected_id))

        if query.seriesName:
            stmt = stmt.where(PhotometricSeries.series_name == query.seriesName.strip())
        if query.seriesObjID:
            stmt = stmt.where(
                PhotometricSeries.series_obj_id == query.seriesObjID.strip()
            )
        if query.filter:
            # psycopg3 strict-binds the string against the enum column; cast
            # explicitly so the comparison binds as the enum type.
            stmt = stmt.where(
                sa.cast(PhotometricSeries.filter, sa.String) == query.filter
            )
        if query.channel:
            stmt = stmt.where(PhotometricSeries.channel == query.channel)
        if query.origin:
            stmt = stmt.where(PhotometricSeries.origin == query.origin)

        if query.filename:
            filename = query.filename
            persistent_folder = cfg.get(
                "photometric_series_folder", "persistentdata/phot_series"
            )
            basedir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
            )
            root_folder = os.path.join(basedir, persistent_folder)
            if not filename.startswith(root_folder):
                filename = (
                    os.path.join(basedir, filename)
                    if filename.startswith(persistent_folder)
                    else os.path.join(root_folder, filename)
                )

            stmt = stmt.where(PhotometricSeries.filename == filename)

        for value, column, after in (
            (query.startAfter, PhotometricSeries.mjd_first, True),
            (query.startBefore, PhotometricSeries.mjd_first, False),
            (query.midAfter, PhotometricSeries.mjd_mid, True),
            (query.midBefore, PhotometricSeries.mjd_mid, False),
            (query.endAfter, PhotometricSeries.mjd_last, True),
            (query.endBefore, PhotometricSeries.mjd_last, False),
        ):
            if value is None:
                continue
            try:
                mjd = Time(arrow.get(value).datetime).mjd
            except Exception:
                return self.error(
                    f"Cannot parse time {value}: {traceback.format_exc()}"
                )
            stmt = stmt.where(column > mjd if after else column < mjd)

        model = PhotometricSeries
        if query.useRobustMagAndRMS:
            mag, rms = model.robust_mag, model.robust_rms
        else:
            mag, rms = model.mean_mag, model.rms_mag

        for value, column, op in (
            (query.expTime, model.exp_time, operator.eq),
            (query.minExpTime, model.exp_time, operator.ge),
            (query.maxExpTime, model.exp_time, operator.le),
            (query.minFrameRate, model.frame_rate, operator.ge),
            (query.maxFrameRate, model.frame_rate, operator.le),
            (query.minNumExposures, model.num_exp, operator.ge),
            (query.maxNumExposures, model.num_exp, operator.le),
            (query.instrumentID, model.instrument_id, operator.eq),
            (query.followupRequestID, model.followup_request_id, operator.eq),
            (query.assignmentID, model.assignment_id, operator.eq),
            (query.ownerID, model.owner_id, operator.eq),
            (query.magFainterThan, mag, operator.ge),
            (query.magBrighterThan, mag, operator.le),
            (query.limitingMagFainterThan, model.limiting_mag, operator.ge),
            (query.limitingMagBrighterThan, model.limiting_mag, operator.le),
            (query.magrefFainterThan, model.magref, operator.ge),
            (query.magrefBrighterThan, model.magref, operator.le),
            (query.minRMS, rms, operator.ge),
            (query.maxRMS, rms, operator.le),
            (query.minMedianSNR, model.median_snr, operator.ge),
            (query.maxMedianSNR, model.median_snr, operator.le),
            (query.minBestSNR, model.best_snr, operator.ge),
            (query.maxBestSNR, model.best_snr, operator.le),
            (query.minWorstSNR, model.worst_snr, operator.ge),
            (query.maxWorstSNR, model.worst_snr, operator.le),
            (query.hash, model.hash, operator.eq),
        ):
            if value is not None:
                stmt = stmt.where(op(column, value))

        if query.detected is not None:
            stmt = stmt.where(PhotometricSeries.is_detected.is_(query.detected))

        if query.limitingMagIsNaN:
            stmt = stmt.where(PhotometricSeries.limiting_mag.is_(None))

        # a non-column attribute would pass getattr and only fail inside order_by
        if query.sortBy not in sa.inspect(PhotometricSeries).mapper.column_attrs:
            return self.error(
                f"Invalid value for sortBy {query.sortBy}. Could not find column. "
            )

        order_by_column = getattr(PhotometricSeries, query.sortBy)
        if isinstance(order_by_column.type, sa.Enum):
            # enums sort by declaration order, not the alphabetical order users expect
            order_by_column = case(
                {name: name for name in order_by_column.type.enums},
                value=sa.cast(order_by_column, sa.String),
            )
        if query.sortOrder == "desc":
            order_by_column = order_by_column.desc()

        stmt = stmt.order_by(order_by_column)

        page_number = max(query.pageNumber, 1)
        num_per_page = min(query.numPerPage, MAX_SERIES_PER_PAGE)

        with self.Session() as session:
            count_stmt = sa.select(func.count()).select_from(stmt)
            total_matches = session.execute(count_stmt).scalar()
            stmt = stmt.offset((page_number - 1) * num_per_page)
            stmt = stmt.limit(num_per_page)
            series = session.scalars(stmt).unique().all()

            try:
                results = {
                    "series": [s.to_dict(data_format) for s in series],
                    "totalMatches": total_matches,
                    "numPerPage": num_per_page,
                    "pageNumber": page_number,
                }
            except Exception:
                return self.error(
                    f"Could not convert series to dict {traceback.format_exc()}"
                )
            return self.success(data=results)

    @permissions(["Upload data"])
    async def delete(self, photometric_series_id: int):
        """
        ---
        summary: Delete a photometric series
        description: Delete a photometric series
        tags:
          - photometric series
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

        async with self.AsyncSession() as session:
            ps = await session.scalar(
                PhotometricSeries.select(session.user_or_token, mode="delete").where(
                    PhotometricSeries.id == photometric_series_id
                )
            )

            if ps is None:
                return self.error(
                    f"Cannot find photometry point with ID: {photometric_series_id}."
                )

            obj_id = ps.obj_id

            await session.delete(ps)
            await session.commit()

            self.push_all(
                action="skyportal/REFRESH_SOURCE_PHOTOMETRY",
                payload={"obj_id": obj_id},
            )

            return self.success()
