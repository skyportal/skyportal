from typing import ClassVar

import arrow
import sqlalchemy as sa
from arrow import ParserError
from marshmallow.exceptions import ValidationError
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_
from sqlalchemy.orm import joinedload, selectinload

from baselayer.app.access import auth_or_token, permissions
from baselayer.app.custom_exceptions import AccessError

from ...models import Group, MMADetector, MMADetectorSpectrum, MMADetectorTimeInterval
from ...models.schema import (
    MMADetectorSpectrumPost,
)
from ..base import BaseHandler


async def validate_accessible_ids(id_list, model_class, session):
    """Accessibility half of spectrum.parse_id_list, for ID lists already
    parsed by the query model. Raises AccessError on inaccessible IDs."""
    if id_list is None:
        return None

    result = await session.scalars(model_class.select(session.user_or_token))
    accessible_ids = {row.id for row in result.unique().all()}
    for id in id_list:
        if id not in accessible_ids:
            raise AccessError(
                f'Invalid {model_class.__name__} IDs field ("{id_list}"); '
                f"Not all {model_class.__name__} IDs are valid/accessible"
            )
    return id_list


class MMADetectorGetQuery(BaseModel):
    """Query parameters for listing MMA Detectors."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset()

    name: str | None = Field(
        default=None,
        description="Filter by name",
    )


class MMADetectorPostBody(BaseModel):
    """Request body for creating an MMADetector."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        description="Unabbreviated facility name (e.g., LIGO Hanford Observatory)."
    )
    nickname: str = Field(description="Abbreviated facility name (e.g., H1).")
    aliases: list[str] | None = Field(
        default=None,
        description="Other names GCN notices use for this detector (e.g. Fermi "
        "for FermiGBM). An event is linked when a tag matches the nickname or "
        "any alias.",
    )
    type: str = Field(
        description="MMA detector type, one of gravitational-wave, neutrino, "
        "gamma-ray-burst, or x-ray."
    )
    lat: float | None = Field(default=None, description="Latitude in deg.")
    lon: float | None = Field(default=None, description="Longitude in deg.")
    elevation: float | None = Field(default=None, description="Elevation in meters.")
    fixed_location: bool | None = Field(
        default=None,
        description="Does this detector have a fixed location (lon, lat, elev)?",
    )


class MMADetectorPostResponse(BaseModel):
    """Data payload returned when creating an MMADetector."""

    id: int = Field(description="New mmadetector ID")


class MMADetectorPatchBody(BaseModel):
    """Request body for updating an MMADetector."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, description="Unabbreviated facility name.")
    nickname: str | None = Field(default=None, description="Abbreviated facility name.")
    aliases: list[str] | None = Field(
        default=None,
        description="Other names GCN notices use for this detector.",
    )
    type: str | None = Field(default=None, description="MMA detector type.")
    lat: float | None = Field(default=None, description="Latitude in deg.")
    lon: float | None = Field(default=None, description="Longitude in deg.")
    elevation: float | None = Field(default=None, description="Elevation in meters.")
    fixed_location: bool | None = Field(
        default=None,
        description="Does this detector have a fixed location (lon, lat, elev)?",
    )


class MMADetectorSpectrumPostBody(BaseModel):
    """Request body for uploading an MMADetector spectrum."""

    model_config = ConfigDict(extra="forbid")

    frequencies: list[float] = Field(description="Frequencies of the spectrum [Hz].")
    amplitudes: list[float] = Field(
        description="Amplitude of the Spectrum [1/sqrt(Hz)]."
    )
    start_time: str = Field(
        description="The ISO UTC start time the spectrum was taken."
    )
    end_time: str = Field(description="The ISO UTC end time the spectrum was taken.")
    detector_id: int = Field(
        description="ID of the MMADetector that acquired the Spectrum."
    )
    group_ids: list[int] | str | None = Field(
        default=None,
        description='IDs of the Groups to share this spectrum with. Set to "all" '
        "to make this spectrum visible to all users.",
    )


class MMADetectorSpectrumPatchBody(BaseModel):
    """Request body for updating an MMADetector spectrum."""

    model_config = ConfigDict(extra="forbid")

    frequencies: list[float] | None = Field(
        default=None, description="Frequencies of the spectrum [Hz]."
    )
    amplitudes: list[float] | None = Field(
        default=None, description="Amplitude of the Spectrum [1/sqrt(Hz)]."
    )
    start_time: str | None = Field(
        default=None, description="The ISO UTC start time the spectrum was taken."
    )
    end_time: str | None = Field(
        default=None, description="The ISO UTC end time the spectrum was taken."
    )
    detector_id: int | None = Field(
        default=None, description="ID of the MMADetector that acquired the Spectrum."
    )
    group_ids: list[int] | str | None = Field(
        default=None,
        description='IDs of the Groups to share this spectrum with. Set to "all" '
        "to make this spectrum visible to all users.",
    )


class MMADetectorSpectrumPostResponse(BaseModel):
    """Data payload returned when uploading an MMADetector spectrum."""

    id: int = Field(description="New mmadetector spectrum ID")


class MMADetectorTimeIntervalPostBody(BaseModel):
    """Request body for uploading MMADetector time interval(s)."""

    model_config = ConfigDict(extra="forbid")

    detector_id: int | None = Field(
        default=None, description="ID of the MMADetector for the time interval(s)."
    )
    time_interval: list | None = Field(
        default=None, description="A single time interval [start, end]."
    )
    time_intervals: list | None = Field(
        default=None, description="List of time intervals, each [start, end]."
    )
    group_ids: list[int] | str | None = Field(
        default=None,
        description="IDs of the Groups to share these time intervals with. Set to "
        '"all" to make them visible to all users.',
    )


class MMADetectorTimeIntervalPatchBody(BaseModel):
    """Request body for updating an MMADetector time interval."""

    model_config = ConfigDict(extra="forbid")

    detector_id: int | None = Field(
        default=None, description="ID of the MMADetector for the time interval."
    )
    time_interval: list | None = Field(
        default=None, description="A time interval [start, end]."
    )
    group_ids: list[int] | str | None = Field(
        default=None,
        description="IDs of the Groups to share this time interval with. Set to "
        '"all" to make it visible to all users.',
    )


class MMADetectorTimeIntervalPostResponse(BaseModel):
    """Data payload returned when uploading MMADetector time interval(s)."""

    ids: list[int] = Field(description="New mmadetector time interval IDs")


class MMADetectorHandler(BaseHandler):
    @permissions(["Manage allocations"])
    async def post(
        self, *, body: MMADetectorPostBody = None
    ) -> MMADetectorPostResponse:
        """
        ---
        summary: Create an MMA Detector
        description: Create a Multimessenger Astronomical Detector (MMADetector)
        tags:
          - mma detectors
        """
        body = self.parse_body(MMADetectorPostBody)
        data = body.model_dump(exclude_unset=True)

        async with self.AsyncSession() as session:
            schema = MMADetector.__schema__()
            try:
                mmadetector = schema.load(data)
            except ValidationError as e:
                return self.error(
                    f"Invalid/missing parameters: {e.normalized_messages()}"
                )
            if body.fixed_location:
                if body.lat < -90 or body.lat > 90 or body.lon < -180 or body.lon > 180:
                    return self.error(
                        "Latitude must be between -90 and 90, longitude between -180 and 180"
                    )
            session.add(mmadetector)
            await session.commit()

            self.push_all(action="skyportal/REFRESH_MMADETECTOR_LIST")
            return self.success(data={"id": mmadetector.id})

    @auth_or_token
    async def get(
        self, mmadetector_id: int | None = None, *, query: MMADetectorGetQuery = None
    ):
        """
        ---
        single:
          summary: Retrieve an MMA Detector
          description: Retrieve a Multimessenger Astronomical Detector (MMADetector)
          tags:
            - mma detectors
          responses:
            200:
              content:
                application/json:
                  schema: SingleMMADetector
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          summary: Retrieve multiple MMA Detectors
          description: Retrieve all Multimessenger Astronomical Detectors (MMADetectors)
          tags:
            - mma detectors
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfMMADetectors
            400:
              content:
                application/json:
                  schema: Error
        """
        query = self.parse_query(MMADetectorGetQuery)

        async with self.AsyncSession() as session:
            if mmadetector_id is not None:
                try:
                    mmadetector_id_int = int(mmadetector_id)
                except (TypeError, ValueError):
                    return self.error(f"Invalid mmadetector_id: {mmadetector_id}")
                t = await session.scalar(
                    MMADetector.select(
                        session.user_or_token,
                        options=[selectinload(MMADetector.events)],
                    ).where(MMADetector.id == mmadetector_id_int)
                )
                if t is None:
                    return self.error(
                        f"Could not load MMA Detector with ID {mmadetector_id}"
                    )
                return self.success(data=t)

            stmt = MMADetector.select(session.user_or_token)
            if query.name is not None:
                stmt = stmt.where(MMADetector.name.contains(query.name))

            result = await session.scalars(stmt)
            data = result.all()
            return self.success(data=data)

    @permissions(["Manage allocations"])
    async def patch(self, mmadetector_id: int, *, body: MMADetectorPatchBody = None):
        """
        ---
        summary: Update an MMA Detector
        description: Update a Multimessenger Astronomical Detector (MMADetector)
        tags:
          - mma detectors
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
        body = self.parse_body(MMADetectorPatchBody)

        try:
            mmadetector_id_int = int(mmadetector_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid mmadetector_id: {mmadetector_id}")

        async with self.AsyncSession() as session:
            t = await session.scalar(
                MMADetector.select(session.user_or_token, mode="update").where(
                    MMADetector.id == mmadetector_id_int
                )
            )
            if t is None:
                return self.error("Invalid MMA Detector ID.")
            data = body.model_dump(exclude_unset=True)
            data["id"] = mmadetector_id_int

            schema = MMADetector.__schema__()
            try:
                schema.load(data, partial=True)
            except ValidationError as e:
                return self.error(
                    f"Invalid/missing parameters: {e.normalized_messages()}"
                )

            if "name" in body.model_fields_set:
                t.name = body.name
            if "nickname" in body.model_fields_set:
                t.nickname = body.nickname
            if "aliases" in body.model_fields_set:
                t.aliases = body.aliases
            if "lat" in body.model_fields_set:
                if body.lat < -90 or body.lat > 90:
                    return self.error("Latitude must be between -90 and 90")
                t.lat = body.lat
            if "lon" in body.model_fields_set:
                if body.lon < -180 or body.lon > 180:
                    return self.error("Longitude between -180 and 180")
                t.lon = body.lon
            if "fixed_location" in body.model_fields_set:
                t.fixed_location = body.fixed_location
            if "type" in body.model_fields_set:
                t.type = body.type

            await session.commit()

            self.push_all(action="skyportal/REFRESH_MMADETECTOR_LIST")
            return self.success()

    @permissions(["Manage allocations"])
    async def delete(self, mmadetector_id: int):
        """
        ---
        summary: Delete an MMA Detector
        description: Delete a Multimessenger Astronomical Detector (MMADetector)
        tags:
          - mma detectors
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

        try:
            mmadetector_id_int = int(mmadetector_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid mmadetector_id: {mmadetector_id}")

        async with self.AsyncSession() as session:
            t = await session.scalar(
                MMADetector.select(session.user_or_token, mode="delete").where(
                    MMADetector.id == mmadetector_id_int
                )
            )
            if t is None:
                return self.error("Invalid MMA Detector ID.")
            await session.delete(t)
            await session.commit()
            self.push_all(action="skyportal/REFRESH_MMADETECTOR_LIST")
            return self.success()


class MMADetectorSpectrumGetQuery(BaseModel):
    """Query parameters for listing MMA Detector spectra."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset()

    observedBefore: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, "
            "return only spectra observed before this time."
        ),
    )
    observedAfter: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, "
            "return only spectra observed after this time."
        ),
    )
    detectorIDs: list[int] | None = Field(
        default=None,
        description="If provided, filter only spectra observed with one of these mmadetector IDs.",
    )
    groupIDs: list[int] | None = Field(
        default=None,
        description="If provided, filter only spectra saved to one of these group IDs.",
    )


class MMADetectorSpectrumHandler(BaseHandler):
    @permissions(["Upload data"])
    async def post(
        self, *, body: MMADetectorSpectrumPostBody = None
    ) -> MMADetectorSpectrumPostResponse:
        """
        ---
        summary: Upload an MMA Detector Spectrum
        description: Upload a Multimessenger Astronomical Detector (MMADetector) spectrum
        tags:
          - mma detector spectra
        """
        body = self.parse_body(MMADetectorSpectrumPostBody)
        try:
            data = MMADetectorSpectrumPost.load(body.model_dump(exclude_unset=True))
        except ValidationError as e:
            return self.error(
                f"Invalid / missing parameters; {e.normalized_messages()}"
            )

        async with self.AsyncSession() as session:
            from ...utils.data_access import (
                accessible_group_ids_async,
                default_extra_share_group_ids,
            )

            mmadetector = await session.scalar(
                MMADetector.select(self.current_user).where(
                    MMADetector.id == data["detector_id"]
                )
            )
            if mmadetector is None:
                return self.error(
                    f"Cannot find mmadetector with ID: {data['detector_id']}"
                )

            owner_id = self.associated_user_object.id

            single_user_group_id = await session.scalar(
                sa.select(Group.id).where(
                    Group.single_user_group.is_(True),
                    Group.users.any(id=owner_id),
                )
            )

            group_ids = data.pop("group_ids", None)
            if group_ids == [] or group_ids is None:
                group_ids = await default_extra_share_group_ids(session)
            elif group_ids == "all":
                group_ids = await accessible_group_ids_async(self.current_user, session)

            if (
                single_user_group_id is not None
                and single_user_group_id not in group_ids
            ):
                group_ids.append(single_user_group_id)

            groups_result = await session.scalars(
                Group.select(self.current_user).where(Group.id.in_(group_ids))
            )
            groups = groups_result.unique().all()
            if {g.id for g in groups} != set(group_ids):
                return self.error(
                    f"Cannot find one or more groups with IDs: {group_ids}."
                )

            spec = MMADetectorSpectrum(**data)
            spec.mmadetector = mmadetector
            spec.groups = groups
            spec.owner_id = owner_id
            session.add(spec)

            await session.commit()

            self.push_all(
                action="skyportal/REFRESH_MMADETECTOR",
                payload={"detector_id": mmadetector.id},
            )

            self.push_all(
                action="skyportal/REFRESH_MMADETECTOR_SPECTRA",
                payload={"detector_id": mmadetector.id},
            )

            return self.success(data={"id": spec.id})

    @auth_or_token
    async def get(
        self,
        spectrum_id: int | None = None,
        *,
        query: MMADetectorSpectrumGetQuery = None,
    ):
        """
        ---
        single:
          summary: Retrieve an MMA Detector Spectrum
          description: Retrieve an mmadetector spectrum
          tags:
            - mma detector spectra
          responses:
            200:
              content:
                application/json:
                  schema: SingleMMADetectorSpectrum
            403:
              content:
                application/json:
                  schema: Error
        multiple:
          summary: Retrieve multiple MMA Detector Spectra
          description: Retrieve multiple spectra with given criteria
          tags:
            - mma detector spectra
        """

        query = self.parse_query(MMADetectorSpectrumGetQuery)

        if spectrum_id is not None:
            try:
                spectrum_id_int = int(spectrum_id)
            except (TypeError, ValueError):
                return self.error(f"Invalid spectrum_id: {spectrum_id}")
            async with self.AsyncSession() as session:
                spectrum = await session.scalar(
                    MMADetectorSpectrum.select(session.user_or_token).where(
                        MMADetectorSpectrum.id == spectrum_id_int
                    )
                )
                if spectrum is None:
                    return self.error(
                        f"Could not access spectrum {spectrum_id}.", status=403
                    )
                return self.success(data=spectrum)

        observed_before = query.observedBefore
        observed_after = query.observedAfter
        detector_ids = query.detectorIDs
        group_ids = query.groupIDs

        # validate inputs
        try:
            observed_before = (
                arrow.get(observed_before).naive if observed_before else None
            )
        except (TypeError, ParserError):
            return self.error(f'Cannot parse time input value "{observed_before}".')

        try:
            observed_after = arrow.get(observed_after).naive if observed_after else None
        except (TypeError, ParserError):
            return self.error(f'Cannot parse time input value "{observed_after}".')

        async with self.AsyncSession() as session:
            try:
                detector_ids = await validate_accessible_ids(
                    detector_ids, MMADetector, session
                )
                group_ids = await validate_accessible_ids(group_ids, Group, session)
            except (ValueError, AccessError) as e:
                return self.error(str(e))

            # filter the spectra
            spec_query = MMADetectorSpectrum.select(session.user_or_token)
            if detector_ids:
                spec_query = spec_query.where(
                    MMADetectorSpectrum.detector_id.in_(detector_ids)
                )

            if group_ids:
                spec_query = spec_query.where(
                    or_(
                        *[
                            MMADetectorSpectrum.groups.any(Group.id == gid)
                            for gid in group_ids
                        ]
                    )
                )

            if observed_before:
                spec_query = spec_query.where(
                    MMADetectorSpectrum.end_time <= observed_before
                )

            if observed_after:
                spec_query = spec_query.where(
                    MMADetectorSpectrum.start_time >= observed_after
                )

            result = await session.scalars(spec_query)
            spectra = result.unique().all()

            return self.success(data=spectra)

    @permissions(["Upload data"])
    async def patch(
        self, spectrum_id: int, *, body: MMADetectorSpectrumPatchBody = None
    ):
        """
        ---
        summary: Update an MMA Detector Spectrum
        description: Update mmadetector spectrum
        tags:
          - mma detector spectra
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
        body = self.parse_body(MMADetectorSpectrumPatchBody)

        try:
            spectrum_id = int(spectrum_id)
        except (TypeError, ValueError):
            return self.error("Could not convert spectrum id to int.")

        try:
            data = MMADetectorSpectrumPost.load(
                body.model_dump(exclude_unset=True), partial=True
            )
        except ValidationError as e:
            return self.error(f"Invalid/missing parameters: {e.normalized_messages()}")

        group_ids = data.pop("group_ids", None)

        async with self.AsyncSession() as session:
            from ...utils.data_access import accessible_group_ids_async

            if group_ids == "all":
                group_ids = await accessible_group_ids_async(self.current_user, session)

            spectrum = await session.scalar(
                MMADetectorSpectrum.select(self.current_user)
                .where(MMADetectorSpectrum.id == spectrum_id)
                .options(
                    selectinload(MMADetectorSpectrum.groups),
                    selectinload(MMADetectorSpectrum.detector),
                )
            )

            if group_ids:
                groups_result = await session.scalars(
                    Group.select(self.current_user).where(Group.id.in_(group_ids))
                )
                groups = groups_result.unique().all()
                if {g.id for g in groups} != set(group_ids):
                    return self.error(
                        f"Cannot find one or more groups with IDs: {group_ids}."
                    )

                if groups:
                    existing_group_ids = {g.id for g in spectrum.groups}
                    new_groups = [g for g in groups if g.id not in existing_group_ids]
                    if new_groups:
                        spectrum.groups = spectrum.groups + new_groups

            for k in data:
                setattr(spectrum, k, data[k])

            await session.commit()

            self.push_all(
                action="skyportal/REFRESH_MMADETECTOR",
                payload={"detector_id": spectrum.detector.id},
            )

            self.push_all(
                action="skyportal/REFRESH_MMADETECTOR_SPECTRA",
                payload={"detector_id": spectrum.detector.id},
            )

            return self.success()

    @permissions(["Upload data"])
    async def delete(self, spectrum_id: int):
        """
        ---
        summary: Delete an MMA Detector Spectrum
        description: Delete an mmadetector spectrum
        tags:
          - mma detector spectra
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
            spectrum = await session.scalar(
                MMADetectorSpectrum.select(self.current_user, mode="delete")
                .where(MMADetectorSpectrum.id == spectrum_id)
                .options(selectinload(MMADetectorSpectrum.detector))
            )
            if spectrum is None:
                return self.error(f"Cannot find spectrum with ID {spectrum_id}")

            detector_id = spectrum.detector.id
            await session.delete(spectrum)
            await session.commit()

            self.push_all(
                action="skyportal/REFRESH_MMADETECTOR",
                payload={"detector_id": detector_id},
            )

            self.push_all(
                action="skyportal/REFRESH_MMADETECTOR_SPECTRA",
                payload={"detector_id": detector_id},
            )

            return self.success()


class MMADetectorTimeIntervalGetQuery(BaseModel):
    """Query parameters for listing MMA Detector time intervals."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset()

    observedBefore: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, "
            "return only time intervals observed before this time."
        ),
    )
    observedAfter: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, "
            "return only time intervals observed after this time."
        ),
    )
    detectorIDs: list[int] | None = Field(
        default=None,
        description=(
            "If provided, filter only time intervals observed with one of these "
            "mmadetector IDs."
        ),
    )
    groupIDs: list[int] | None = Field(
        default=None,
        description="If provided, filter only time intervals saved to one of these group IDs.",
    )


class MMADetectorTimeIntervalHandler(BaseHandler):
    @permissions(["Upload data"])
    async def post(
        self, *, body: MMADetectorTimeIntervalPostBody = None
    ) -> MMADetectorTimeIntervalPostResponse:
        """
        ---
        summary: Upload an MMA Detector Time Interval
        description: Upload a Multimessenger Astronomical Detector (MMADetector) time_interval(s)
        tags:
          - mma detector time intervals
        """
        body = self.parse_body(MMADetectorTimeIntervalPostBody)
        json = body.model_dump(exclude_unset=True)

        if "time_intervals" in json:
            time_intervals = json["time_intervals"]
        elif "time_interval" in json:
            time_intervals = [json["time_interval"]]
        else:
            return self.error("time_interval or time_intervals required in json")

        if "detector_id" not in json:
            return self.error("detector_id required in json")

        async with self.AsyncSession() as session:
            from ...utils.data_access import (
                accessible_group_ids_async,
                default_extra_share_group_ids,
            )

            mmadetector = await session.scalar(
                MMADetector.select(self.current_user).where(
                    MMADetector.id == json["detector_id"]
                )
            )
            if mmadetector is None:
                return self.error(
                    f"Cannot find mmadetector with ID: {json['detector_id']}"
                )

            owner_id = self.associated_user_object.id

            single_user_group_id = await session.scalar(
                sa.select(Group.id).where(
                    Group.single_user_group.is_(True),
                    Group.users.any(id=owner_id),
                )
            )

            group_ids = json.pop("group_ids", None)
            if group_ids == [] or group_ids is None:
                group_ids = await default_extra_share_group_ids(session)
            elif group_ids == "all":
                group_ids = await accessible_group_ids_async(self.current_user, session)

            if (
                single_user_group_id is not None
                and single_user_group_id not in group_ids
            ):
                group_ids.append(single_user_group_id)

            groups_result = await session.scalars(
                Group.select(self.current_user).where(Group.id.in_(group_ids))
            )
            groups = groups_result.unique().all()
            if {g.id for g in groups} != set(group_ids):
                return self.error(
                    f"Cannot find one or more groups with IDs: {group_ids}."
                )

            time_interval_list = []
            for time_interval in time_intervals:
                data = {
                    "time_interval": time_interval,
                    "detector_id": json["detector_id"],
                }

                time_interval = MMADetectorTimeInterval(**data)
                time_interval.mmadetector = mmadetector
                time_interval.groups = groups
                time_interval.owner_id = owner_id
                time_interval_list.append(time_interval)

            session.add_all(time_interval_list)
            await session.commit()

            self.push_all(
                action="skyportal/REFRESH_MMASEGMENT",
                payload={"detector_id": mmadetector.id},
            )

            self.push_all(
                action="skyportal/REFRESH_MMASEGMENT_SEGMENTS",
                payload={"detector_id": mmadetector.id},
            )

            return self.success(
                data={"ids": [time_interval.id for time_interval in time_interval_list]}
            )

    @auth_or_token
    async def get(
        self,
        time_interval_id: int | None = None,
        *,
        query: MMADetectorTimeIntervalGetQuery = None,
    ):
        """
        ---
        single:
          summary: Retrieve an MMA Detector Time Interval
          description: Retrieve an mmadetector time_interval
          tags:
            - mma detector time intervals
          responses:
            200:
              content:
                application/json:
                  schema: SingleMMADetectorTimeInterval
            403:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve multiple time_intervals with given criteria
          tags:
            - mma detector time intervals
        """
        query = self.parse_query(MMADetectorTimeIntervalGetQuery)

        if time_interval_id is not None:
            try:
                time_interval_id_int = int(time_interval_id)
            except (TypeError, ValueError):
                return self.error(f"Invalid time_interval_id: {time_interval_id}")
            async with self.AsyncSession() as session:
                time_interval = await session.scalar(
                    MMADetectorTimeInterval.select(session.user_or_token)
                    .where(MMADetectorTimeInterval.id == time_interval_id_int)
                    .options(
                        selectinload(MMADetectorTimeInterval.owner),
                        selectinload(MMADetectorTimeInterval.groups),
                        selectinload(MMADetectorTimeInterval.detector),
                    )
                )
                if time_interval is None:
                    return self.error(
                        f"Could not access time_interval {time_interval_id}.",
                        status=403,
                    )
                seg = time_interval.time_interval
                data = {
                    "id": time_interval.id,
                    "time_interval": [seg.lower, seg.upper],
                    "owner": time_interval.owner,
                    "groups": time_interval.groups,
                    "detector": time_interval.detector,
                }
                return self.success(data=data)

        observed_before = query.observedBefore
        observed_after = query.observedAfter
        detector_ids = query.detectorIDs
        group_ids = query.groupIDs

        # validate inputs
        try:
            observed_before = (
                arrow.get(observed_before).naive if observed_before else None
            )
        except (TypeError, ParserError):
            return self.error(f'Cannot parse time input value "{observed_before}".')

        try:
            observed_after = arrow.get(observed_after).naive if observed_after else None
        except (TypeError, ParserError):
            return self.error(f'Cannot parse time input value "{observed_after}".')

        async with self.AsyncSession() as session:
            try:
                detector_ids = await validate_accessible_ids(
                    detector_ids, MMADetector, session
                )
                group_ids = await validate_accessible_ids(group_ids, Group, session)
            except (ValueError, AccessError) as e:
                return self.error(str(e))

            # filter the time_interval
            time_interval_query = MMADetectorTimeInterval.select(
                session.user_or_token
            ).options(
                selectinload(MMADetectorTimeInterval.owner),
                selectinload(MMADetectorTimeInterval.groups),
                selectinload(MMADetectorTimeInterval.detector),
            )
            if detector_ids:
                time_interval_query = time_interval_query.where(
                    MMADetectorTimeInterval.detector_id.in_(detector_ids)
                )

            if group_ids:
                time_interval_query = time_interval_query.where(
                    or_(
                        *[
                            MMADetectorTimeInterval.groups.any(Group.id == gid)
                            for gid in group_ids
                        ]
                    )
                )

            if observed_before:
                time_interval_query = time_interval_query.where(
                    MMADetectorTimeInterval.end_time <= observed_before
                )

            if observed_after:
                time_interval_query = time_interval_query.where(
                    MMADetectorTimeInterval.start_time >= observed_after
                )

            result = await session.scalars(time_interval_query)
            time_intervals = result.unique().all()
            data = []
            for time_interval in time_intervals:
                seg = time_interval.time_interval
                data.append(
                    {
                        "id": time_interval.id,
                        "time_interval": [seg.lower, seg.upper],
                        "owner": time_interval.owner,
                        "groups": time_interval.groups,
                        "detector": time_interval.detector,
                    }
                )
            return self.success(data=data)

    @permissions(["Upload data"])
    async def patch(
        self, time_interval_id: int, *, body: MMADetectorTimeIntervalPatchBody = None
    ):
        """
        ---
        summary: Update an MMA Detector Time Interval
        description: Update mmadetector time_interval
        tags:
          - mma detector time intervals
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
        body = self.parse_body(MMADetectorTimeIntervalPatchBody)

        try:
            time_interval_id = int(time_interval_id)
        except (TypeError, ValueError):
            return self.error("Could not convert time_interval id to int.")

        data = body.model_dump(exclude_unset=True)
        group_ids = data.pop("group_ids", None)

        async with self.AsyncSession() as session:
            from ...utils.data_access import accessible_group_ids_async

            if group_ids == "all":
                group_ids = await accessible_group_ids_async(self.current_user, session)

            time_interval = await session.scalar(
                MMADetectorTimeInterval.select(self.current_user)
                .where(MMADetectorTimeInterval.id == time_interval_id)
                .options(
                    selectinload(MMADetectorTimeInterval.groups),
                    selectinload(MMADetectorTimeInterval.detector),
                )
            )

            if group_ids:
                groups_result = await session.scalars(
                    Group.select(self.current_user).where(Group.id.in_(group_ids))
                )
                groups = groups_result.unique().all()
                if {g.id for g in groups} != set(group_ids):
                    return self.error(
                        f"Cannot find one or more groups with IDs: {group_ids}."
                    )

                if groups:
                    time_interval.groups = time_interval.groups + groups

            if "time_interval" in data:
                time_interval.time_interval = data["time_interval"]

            await session.commit()

            self.push_all(
                action="skyportal/REFRESH_MMADETECTOR",
                payload={"detector_id": time_interval.detector.id},
            )

            self.push_all(
                action="skyportal/REFRESH_MMADETECTOR_SEGMENT",
                payload={"detector_id": time_interval.detector.id},
            )

            return self.success()

    @permissions(["Upload data"])
    async def delete(self, time_interval_id: int):
        """
        ---
        summary: Delete an MMA Detector Time Interval
        description: Delete an mmadetector time_interval
        tags:
          - mma detector time intervals
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
            time_interval = await session.scalar(
                MMADetectorTimeInterval.select(self.current_user, mode="delete")
                .where(MMADetectorTimeInterval.id == time_interval_id)
                .options(selectinload(MMADetectorTimeInterval.detector))
            )
            if time_interval is None:
                return self.error(
                    f"Cannot find time_interval with ID {time_interval_id}"
                )

            detector_id = time_interval.detector.id
            await session.delete(time_interval)
            await session.commit()

            self.push_all(
                action="skyportal/REFRESH_MMADETECTOR",
                payload={"detector_id": detector_id},
            )

            self.push_all(
                action="skyportal/REFRESH_MMADETECTOR_SEGMENTS",
                payload={"detector_id": detector_id},
            )

            return self.success()
