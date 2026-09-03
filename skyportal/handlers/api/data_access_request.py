import dateutil.parser
import sqlalchemy as sa
from astropy.time import Time
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import selectinload

from baselayer.app.access import auth_or_token, permissions

from ...models import (
    Allocation,
    DataAccessRequest,
    FollowupRequest,
    Group,
    GroupPhotometry,
    GroupSpectrum,
    GroupUser,
    Instrument,
    Obj,
    Photometry,
    Spectrum,
    User,
    UserNotification,
)
from ...utils.parse import get_page_and_n_per_page
from ..base import BaseHandler

MAX_DATA_ACCESS_REQUESTS = 500


class PhotometryDataset(BaseModel):
    """One owner's photometry on an object in a single instrument/filter."""

    model_config = ConfigDict(extra="forbid")

    ownerID: int = Field(description="ID of the User who owns the photometry")
    instrumentID: int = Field(description="ID of the instrument it was taken with")
    filter: str = Field(description="Bandpass the photometry was taken in")


class DataAccessRequestPostBody(BaseModel):
    """Request body for asking an owner for data on an object."""

    model_config = ConfigDict(extra="forbid")

    objId: str = Field(description="ID of the object the data is attached to")
    photometry: list[PhotometryDataset] = Field(
        default_factory=list,
        description="Photometry datasets being asked for, as returned by the "
        "data availability endpoint.",
    )
    spectrumIDs: list[int] = Field(
        default_factory=list, description="IDs of the spectra being asked for"
    )
    message: str | None = Field(
        default=None, description="Note to the owner explaining the request"
    )


class DataAccessRequestPatchBody(BaseModel):
    """Request body for answering a request."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(description="Either 'accepted' or 'declined'")
    groupID: int | None = Field(
        default=None,
        description="Group to share the data into when accepting. Defaults to "
        "the requester's single user group.",
    )


class DataAccessRequestGetQuery(BaseModel):
    """Query parameters for listing data access requests."""

    model_config = ConfigDict(extra="forbid")

    objId: str | None = Field(default=None, description="Only requests on this object")
    status: str | None = Field(
        default=None, description="Only requests with this status"
    )
    direction: str | None = Field(
        default=None,
        description="'incoming' for requests to answer, 'outgoing' for requests "
        "made by the calling user. Both when omitted.",
    )
    pageNumber: int = Field(
        default=1,
        description="Page number for paginated query results. Defaults to 1.",
    )
    numPerPage: int = Field(
        default=25,
        description=(
            "Number of requests to return per paginated request. Defaults to "
            f"25. Max {MAX_DATA_ACCESS_REQUESTS}."
        ),
    )


def _photometry_key(owner_id, instrument_id, filter_name):
    return f"{owner_id}:{instrument_id}:{filter_name}"


async def _shared_groups(session, user_id, requester_ids):
    """Groups each requester shares with the calling user, keyed by requester.

    These are the groups an answer can grant into without telling the answerer
    anything about the requester they did not already know: both are members.
    """
    if not requester_ids:
        return {}
    mine = sa.select(GroupUser.group_id).where(GroupUser.user_id == user_id)
    rows = (
        await session.execute(
            sa.select(GroupUser.user_id, Group.id, Group.name)
            .join(Group, Group.id == GroupUser.group_id)
            .where(
                GroupUser.user_id.in_(requester_ids),
                GroupUser.group_id.in_(mine),
                Group.single_user_group.is_(False),
            )
        )
    ).all()
    shared = {}
    for requester_id, group_id, name in rows:
        shared.setdefault(requester_id, []).append({"id": group_id, "name": name})
    return shared


def _request_summary(request, shared_groups=None):
    """The parts of a request the frontend shows."""
    return {
        "id": request.id,
        "status": request.status,
        "message": request.message,
        "obj_id": request.obj_id,
        "data_type": request.data_type,
        "instrument_id": request.instrument_id,
        "filter": request.filter,
        "spectrum_id": request.spectrum_id,
        "granted_group_id": request.granted_group_id,
        "created_at": request.created_at.isoformat(),
        "requester": {
            "id": request.requester.id,
            "username": request.requester.username,
            "first_name": request.requester.first_name,
            "last_name": request.requester.last_name,
        },
        "owner": {
            "id": request.owner.id,
            "username": request.owner.username,
            "first_name": request.owner.first_name,
            "last_name": request.owner.last_name,
        },
        "shareable_groups": (shared_groups or {}).get(request.requester_id, []),
    }


# Requests in these states are done with: they cannot collide with tonight.
_SETTLED_REQUEST_STATES = ("complete", "completed", "deleted", "expired")


def _owners_hiding_data():
    """Users who have opted out of having their data discovered at all."""
    return sa.select(User.id).where(
        User.preferences["hideDataFromDiscovery"].astext == "true"
    )


def _held_by_a_discoverable_group(join_model, data_id_column, data_id):
    """Whether the collaborations holding this data are willing to advertise it.

    Data held only by groups with `discoverable_data` off — an embargoed
    programme, say — is never mentioned to anyone outside them. Single user
    groups are not collaborations and do not get a say: an upload always lands
    in the uploader's own group, and data nobody else holds is exactly what
    someone might want to ask for. Whether *that* is advertised is the owner's
    preference to set.
    """
    collaborations = (
        sa.select(join_model.group_id)
        .join(Group, Group.id == join_model.group_id)
        .where(data_id_column == data_id, Group.single_user_group.is_(False))
    )
    return sa.or_(
        sa.not_(collaborations.exists()),
        collaborations.where(Group.discoverable_data.is_(True)).exists(),
    )


def _discoverable_photometry(obj_id):
    """Photometry on an object that may be advertised to non-members."""
    return sa.select(Photometry.id).where(
        Photometry.obj_id == obj_id,
        Photometry.owner_id.notin_(_owners_hiding_data()),
        _held_by_a_discoverable_group(
            GroupPhotometry, GroupPhotometry.photometr_id, Photometry.id
        ),
    )


def _discoverable_spectra(obj_id):
    """Spectra on an object that may be advertised to non-members."""
    return sa.select(Spectrum.id).where(
        Spectrum.obj_id == obj_id,
        Spectrum.owner_id.notin_(_owners_hiding_data()),
        _held_by_a_discoverable_group(
            GroupSpectrum, GroupSpectrum.spectr_id, Spectrum.id
        ),
    )


async def _hidden_photometry_ids(session, obj_id, dataset, user_or_token):
    """Photometry ids in a dataset that the calling user cannot already read."""
    visible = Photometry.select(user_or_token, columns=[Photometry.id]).where(
        Photometry.obj_id == obj_id
    )
    result = await session.scalars(
        sa.select(Photometry.id)
        .where(
            Photometry.obj_id == obj_id,
            Photometry.owner_id == dataset.ownerID,
            Photometry.instrument_id == dataset.instrumentID,
            Photometry.filter == dataset.filter,
            Photometry.id.notin_(visible),
            Photometry.id.in_(_discoverable_photometry(obj_id)),
        )
        .distinct()
    )
    return result.all()


class DataAvailabilityHandler(BaseHandler):
    @auth_or_token
    async def get(self, obj_id: str):
        """
        ---
        summary: Retrieve what data exists on a source but is not visible
        description: >
            Retrieve metadata describing the photometry and spectra attached to
            a source that the calling user cannot read: who owns it, which
            instrument and filter it was taken with, when, and how much of it
            there is. No fluxes, magnitudes or spectra are returned; this is
            the description of data that can then be asked for.
        tags:
          - sources
          - data sharing
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
        """
        async with self.AsyncSession() as session:
            obj = await session.scalar(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            )
            if obj is None:
                return self.error("Invalid objId")

            user_id = self.associated_user_object.id

            visible_photometry = Photometry.select(
                session.user_or_token, columns=[Photometry.id]
            ).where(Photometry.obj_id == obj_id)
            photometry_rows = (
                await session.execute(
                    sa.select(
                        Photometry.owner_id,
                        Photometry.instrument_id,
                        Photometry.filter,
                        sa.func.count(Photometry.id.distinct()),
                        sa.func.min(Photometry.mjd),
                        sa.func.max(Photometry.mjd),
                    )
                    .where(
                        Photometry.obj_id == obj_id,
                        Photometry.id.notin_(visible_photometry),
                        Photometry.id.in_(_discoverable_photometry(obj_id)),
                    )
                    .group_by(
                        Photometry.owner_id,
                        Photometry.instrument_id,
                        Photometry.filter,
                    )
                )
            ).all()

            visible_spectra = Spectrum.select(
                session.user_or_token, columns=[Spectrum.id]
            ).where(Spectrum.obj_id == obj_id)
            spectrum_rows = (
                await session.execute(
                    sa.select(
                        Spectrum.id,
                        Spectrum.owner_id,
                        Spectrum.instrument_id,
                        Spectrum.observed_at,
                        Spectrum.type,
                        Spectrum.label,
                        Spectrum.origin,
                    )
                    .where(
                        Spectrum.obj_id == obj_id,
                        Spectrum.id.notin_(visible_spectra),
                        Spectrum.id.in_(_discoverable_spectra(obj_id)),
                    )
                    .distinct()
                )
            ).all()

            owner_ids = {row[0] for row in photometry_rows} | {
                row[1] for row in spectrum_rows
            }
            instrument_ids = {row[1] for row in photometry_rows} | {
                row[2] for row in spectrum_rows
            }
            owners = (
                await session.execute(
                    sa.select(
                        User.id, User.username, User.first_name, User.last_name
                    ).where(User.id.in_(owner_ids))
                )
            ).all()
            owners = {
                row[0]: {
                    "id": row[0],
                    "username": row[1],
                    "first_name": row[2],
                    "last_name": row[3],
                }
                for row in owners
            }
            instruments = (
                await session.execute(
                    sa.select(Instrument.id, Instrument.name).where(
                        Instrument.id.in_(instrument_ids)
                    )
                )
            ).all()
            instruments = {
                row[0]: {"id": row[0], "name": row[1]} for row in instruments
            }

            existing_result = await session.scalars(
                sa.select(DataAccessRequest).where(
                    DataAccessRequest.requester_id == user_id,
                    DataAccessRequest.obj_id == obj_id,
                )
            )
            existing = existing_result.all()
            photometry_requests = {
                _photometry_key(
                    request.owner_id, request.instrument_id, request.filter
                ): request
                for request in existing
                if request.data_type == "photometry"
            }
            spectrum_requests = {
                request.spectrum_id: request
                for request in existing
                if request.data_type == "spectrum"
            }

            photometry = []
            for (
                owner_id,
                instrument_id,
                filter_name,
                count,
                min_mjd,
                max_mjd,
            ) in photometry_rows:
                request = photometry_requests.get(
                    _photometry_key(owner_id, instrument_id, filter_name)
                )
                photometry.append(
                    {
                        "owner": owners.get(owner_id),
                        "instrument": instruments.get(instrument_id),
                        "filter": filter_name,
                        "num_points": count,
                        "first_mjd": min_mjd,
                        "last_mjd": max_mjd,
                        "request": (
                            {"id": request.id, "status": request.status}
                            if request is not None
                            else None
                        ),
                    }
                )

            spectra = []
            for (
                spectrum_id,
                owner_id,
                instrument_id,
                observed_at,
                spectrum_type,
                label,
                origin,
            ) in spectrum_rows:
                request = spectrum_requests.get(spectrum_id)
                spectra.append(
                    {
                        "id": spectrum_id,
                        "owner": owners.get(owner_id),
                        "instrument": instruments.get(instrument_id),
                        "observed_at": (
                            observed_at.isoformat() if observed_at is not None else None
                        ),
                        # The photometry plot marks spectra by epoch, and works
                        # in MJD.
                        "observed_at_mjd": (
                            Time(observed_at).mjd if observed_at is not None else None
                        ),
                        "type": spectrum_type,
                        "label": label,
                        "origin": origin,
                        "request": (
                            {"id": request.id, "status": request.status}
                            if request is not None
                            else None
                        ),
                    }
                )

            return self.success(data={"photometry": photometry, "spectra": spectra})


class DataAccessRequestHandler(BaseHandler):
    @auth_or_token
    async def get(
        self,
        request_id: int | None = None,
        *,
        query: DataAccessRequestGetQuery = None,
    ):
        """
        ---
        single:
          summary: Get a data access request
          description: Retrieve a single data access request
          tags:
            - data sharing
          responses:
            200:
              content:
                application/json:
                  schema: Success
        multiple:
          summary: Get data access requests
          description: >
            Retrieve the data access requests the calling user made, or that
            they are in a position to answer.
          tags:
            - data sharing
          responses:
            200:
              content:
                application/json:
                  schema: Success
        """
        query = self.parse_query(DataAccessRequestGetQuery)

        async with self.AsyncSession() as session:
            user_id = self.associated_user_object.id
            # distinct(): the accessible-rows ACL joins through the user's groups,
            # so a request reachable via several shared groups would otherwise be
            # returned (and counted) once per group.
            statement = (
                DataAccessRequest.select(session.user_or_token)
                .distinct()
                .options(
                    selectinload(DataAccessRequest.requester),
                    selectinload(DataAccessRequest.owner),
                )
            )
            if request_id is not None:
                request = await session.scalar(
                    statement.where(DataAccessRequest.id == request_id)
                )
                if request is None:
                    return self.error(
                        f"Could not find a data access request with ID {request_id}"
                    )
                shared = await _shared_groups(session, user_id, [request.requester_id])
                return self.success(data=_request_summary(request, shared))

            if query.objId is not None:
                statement = statement.where(DataAccessRequest.obj_id == query.objId)
            if query.status is not None:
                statement = statement.where(DataAccessRequest.status == query.status)
            if query.direction == "outgoing":
                statement = statement.where(DataAccessRequest.requester_id == user_id)
            elif query.direction == "incoming":
                statement = statement.where(DataAccessRequest.requester_id != user_id)

            try:
                page_number, n_per_page = get_page_and_n_per_page(
                    query.pageNumber, query.numPerPage, MAX_DATA_ACCESS_REQUESTS
                )
            except ValueError as e:
                return self.error(str(e))

            total_matches = await session.scalar(
                sa.select(sa.func.count()).select_from(statement.subquery())
            )
            requests = (
                await session.scalars(
                    statement.order_by(DataAccessRequest.created_at.desc())
                    .limit(n_per_page)
                    .offset((page_number - 1) * n_per_page)
                )
            ).all()
            shared = await _shared_groups(
                session, user_id, {request.requester_id for request in requests}
            )
            return self.success(
                data={
                    "requests": [
                        _request_summary(request, shared) for request in requests
                    ],
                    "totalMatches": int(total_matches),
                    "pageNumber": page_number,
                    "numPerPage": n_per_page,
                }
            )

    @auth_or_token
    async def post(self, *, body: DataAccessRequestPostBody = None):
        """
        ---
        summary: Ask for data on a source
        description: >
            Ask the owners of photometry or spectra on a source to share it.
            One request is created per dataset asked for; datasets already
            visible to the calling user, or already the subject of a pending
            request, are skipped.
        tags:
          - data sharing
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        body = self.parse_body(DataAccessRequestPostBody)
        if not body.photometry and not body.spectrumIDs:
            return self.error(
                "One of either `photometry` or `spectrumIDs` must be provided."
            )

        async with self.AsyncSession() as session:
            obj = await session.scalar(
                Obj.select(session.user_or_token).where(Obj.id == body.objId)
            )
            if obj is None:
                return self.error("Invalid objId")

            user_id = self.associated_user_object.id
            existing_result = await session.scalars(
                sa.select(DataAccessRequest).where(
                    DataAccessRequest.requester_id == user_id,
                    DataAccessRequest.obj_id == body.objId,
                    DataAccessRequest.status == "pending",
                )
            )
            pending = existing_result.all()
            pending_photometry = {
                _photometry_key(request.owner_id, request.instrument_id, request.filter)
                for request in pending
                if request.data_type == "photometry"
            }
            pending_spectra = {
                request.spectrum_id
                for request in pending
                if request.data_type == "spectrum"
            }

            created = []
            notify = {}

            for dataset in body.photometry:
                key = _photometry_key(
                    dataset.ownerID, dataset.instrumentID, dataset.filter
                )
                if key in pending_photometry:
                    continue
                photometry_ids = await _hidden_photometry_ids(
                    session, body.objId, dataset, session.user_or_token
                )
                if not photometry_ids:
                    return self.error(
                        f"No photometry to request for {dataset.filter} on "
                        f"instrument {dataset.instrumentID}: it does not exist, "
                        "or you can already see it."
                    )
                holding_group_ids = (
                    await session.scalars(
                        sa.select(GroupPhotometry.group_id)
                        .where(GroupPhotometry.photometr_id.in_(photometry_ids))
                        .distinct()
                    )
                ).all()
                request = DataAccessRequest(
                    requester_id=user_id,
                    owner_id=dataset.ownerID,
                    obj_id=body.objId,
                    data_type="photometry",
                    instrument_id=dataset.instrumentID,
                    filter=dataset.filter,
                    owner_group_ids=list(holding_group_ids),
                    status="pending",
                    message=body.message,
                )
                session.add(request)
                created.append(request)
                notify.setdefault(dataset.ownerID, 0)
                notify[dataset.ownerID] += 1

            if body.spectrumIDs:
                visible_spectra = Spectrum.select(
                    session.user_or_token, columns=[Spectrum.id]
                ).where(Spectrum.obj_id == body.objId)
                spectra = (
                    await session.execute(
                        sa.select(Spectrum.id, Spectrum.owner_id)
                        .where(
                            Spectrum.id.in_(body.spectrumIDs),
                            Spectrum.obj_id == body.objId,
                            Spectrum.id.notin_(visible_spectra),
                            Spectrum.id.in_(_discoverable_spectra(body.objId)),
                        )
                        .distinct()
                    )
                ).all()
                found = {row[0] for row in spectra}
                missing = [sid for sid in body.spectrumIDs if sid not in found]
                if missing:
                    return self.error(
                        f"No spectra to request for IDs {missing}: they do not "
                        "exist on this object, or you can already see them."
                    )
                for spectrum_id, owner_id in spectra:
                    if spectrum_id in pending_spectra:
                        continue
                    holding_group_ids = (
                        await session.scalars(
                            sa.select(GroupSpectrum.group_id)
                            .where(GroupSpectrum.spectr_id == spectrum_id)
                            .distinct()
                        )
                    ).all()
                    request = DataAccessRequest(
                        requester_id=user_id,
                        owner_id=owner_id,
                        obj_id=body.objId,
                        data_type="spectrum",
                        spectrum_id=spectrum_id,
                        owner_group_ids=list(holding_group_ids),
                        status="pending",
                        message=body.message,
                    )
                    session.add(request)
                    created.append(request)
                    notify.setdefault(owner_id, 0)
                    notify[owner_id] += 1

            if not created:
                return self.error("You have already asked for this data.")

            requester = self.associated_user_object
            asker = requester.username
            for owner_id, count in notify.items():
                session.add(
                    UserNotification(
                        user_id=owner_id,
                        text=f"*{asker}* asked for {count} of your "
                        f"dataset(s) on *{body.objId}*",
                        url="/data_access_requests",
                    )
                )
            await session.commit()

            for owner_id in notify:
                self.flow.push(owner_id, "skyportal/FETCH_NOTIFICATIONS", {})
                # A pending request is an open obligation, not just a
                # notification: refresh the lists that show it as outstanding.
                self.flow.push(owner_id, "skyportal/REFRESH_DATA_ACCESS_REQUESTS", {})
            return self.success(data={"ids": [request.id for request in created]})

    @permissions(["Upload data"])
    async def patch(self, request_id: int, *, body: DataAccessRequestPatchBody = None):
        """
        ---
        summary: Answer a data access request
        description: >
            Accept or decline a request for data you own. Accepting shares the
            requested dataset with a group the requester belongs to, defaulting
            to their single user group.
        tags:
          - data sharing
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        body = self.parse_body(DataAccessRequestPatchBody)
        if body.status not in ("accepted", "declined"):
            return self.error("`status` must be either 'accepted' or 'declined'.")

        async with self.AsyncSession() as session:
            request = await session.scalar(
                DataAccessRequest.select(session.user_or_token, mode="update")
                .options(
                    selectinload(DataAccessRequest.requester),
                    selectinload(DataAccessRequest.owner),
                )
                .where(DataAccessRequest.id == request_id)
            )
            if request is None:
                return self.error(
                    "Insufficient permissions: a data access request can only be "
                    "answered by the owner of the data or an admin of a group "
                    "holding it."
                )
            if request.status != "pending":
                return self.error(f"Request has already been {request.status}.")

            group = None
            if body.status == "accepted":
                group = await self.resolve_target_group(session, request, body.groupID)
                if isinstance(group, str):
                    return self.error(group)
                shared = await self.share_dataset(session, request, group)
                if isinstance(shared, str):
                    return self.error(shared)
                request.granted_group_id = group.id

            request.status = body.status
            request.responded_by_id = self.associated_user_object.id
            session.add(
                UserNotification(
                    user_id=request.requester_id,
                    text=f"Your request for data on *{request.obj_id}* was "
                    f"*{body.status}*",
                    url=f"/source/{request.obj_id}",
                )
            )
            await session.commit()

            self.flow.push(request.requester_id, "skyportal/FETCH_NOTIFICATIONS", {})
            # Answered: it leaves the owner's queue and the requester's.
            for user_id_to_refresh in (request.requester_id, request.owner_id):
                self.flow.push(
                    user_id_to_refresh, "skyportal/REFRESH_DATA_ACCESS_REQUESTS", {}
                )
            if body.status == "accepted":
                self.flow.push(
                    request.requester_id,
                    "skyportal/REFRESH_SOURCE",
                    {"obj_key": request.obj_id},
                )
            return self.success()

    async def resolve_target_group(self, session, request, group_id):
        """The group to share into: one the requester belongs to.

        Returns the Group, or an error message.
        """
        statement = (
            sa.select(Group)
            .join(GroupUser, GroupUser.group_id == Group.id)
            .where(GroupUser.user_id == request.requester_id)
        )
        if group_id is None:
            statement = statement.where(Group.single_user_group.is_(True))
        else:
            statement = statement.where(Group.id == group_id)
        group = await session.scalar(statement)
        if group is None:
            return (
                f"Invalid groupID {group_id}: the requester is not a member of it."
                if group_id is not None
                else "The requester has no single user group to share into."
            )
        return group

    async def share_dataset(self, session, request, group):
        """Add the requested dataset to a group. Returns an error message if
        there is nothing left to share."""
        if request.data_type == "photometry":
            photometry_ids = (
                await session.scalars(
                    sa.select(Photometry.id)
                    .where(
                        Photometry.obj_id == request.obj_id,
                        Photometry.owner_id == request.owner_id,
                        Photometry.instrument_id == request.instrument_id,
                        Photometry.filter == request.filter,
                    )
                    .distinct()
                )
            ).all()
            if not photometry_ids:
                return "The requested photometry no longer exists."
            await session.execute(
                pg_insert(GroupPhotometry.__table__)
                .values(
                    [
                        {"photometr_id": photometry_id, "group_id": group.id}
                        for photometry_id in photometry_ids
                    ]
                )
                .on_conflict_do_nothing()
            )
            return None

        spectrum = await session.scalar(
            sa.select(Spectrum).where(Spectrum.id == request.spectrum_id)
        )
        if spectrum is None:
            return "The requested spectrum no longer exists."
        await session.execute(
            pg_insert(GroupSpectrum.__table__)
            .values([{"spectr_id": spectrum.id, "group_id": group.id}])
            .on_conflict_do_nothing()
        )
        return None

    @auth_or_token
    async def delete(self, request_id: int):
        """
        ---
        summary: Withdraw a data access request
        description: Withdraw a request you made
        tags:
          - data sharing
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        async with self.AsyncSession() as session:
            request = await session.scalar(
                DataAccessRequest.select(session.user_or_token, mode="delete").where(
                    DataAccessRequest.id == request_id
                )
            )
            if request is None:
                return self.error(
                    "Insufficient permissions: only the requester can withdraw a "
                    "data access request."
                )
            await session.delete(request)
            await session.commit()
            return self.success()


class ScheduledObservationsHandler(BaseHandler):
    @auth_or_token
    async def get(self, obj_id: str):
        """
        ---
        summary: Retrieve what is scheduled on a source but is not visible
        description: >
            Retrieve the follow-up requests on a source that the calling user
            cannot read: which instrument, which group asked, who to talk to,
            and the state of the request. No request payloads are returned.
            Data availability describes what has already been taken; this
            describes what is about to be, so two groups do not spend the same
            night on the same target. Observing run assignments are not listed:
            runs are world-readable, so those are already visible to everyone.
        tags:
          - sources
          - data sharing
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
        """
        async with self.AsyncSession() as session:
            obj = await session.scalar(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            )
            if obj is None:
                return self.error("Invalid objId")

            visible_requests = FollowupRequest.select(
                session.user_or_token, columns=[FollowupRequest.id]
            ).where(FollowupRequest.obj_id == obj_id)

            rows = (
                await session.execute(
                    sa.select(
                        FollowupRequest.status,
                        FollowupRequest.created_at,
                        Instrument.name,
                        Group.name,
                        User.id,
                        User.username,
                        User.first_name,
                        User.last_name,
                    )
                    .join(Allocation, Allocation.id == FollowupRequest.allocation_id)
                    .join(Instrument, Instrument.id == Allocation.instrument_id)
                    .join(Group, Group.id == Allocation.group_id)
                    .join(User, User.id == FollowupRequest.requester_id)
                    .where(
                        FollowupRequest.obj_id == obj_id,
                        FollowupRequest.id.notin_(visible_requests),
                        # Same bargain as data availability: a group that will
                        # not advertise its data does not advertise its plans.
                        Group.discoverable_data.is_(True),
                        FollowupRequest.requester_id.notin_(_owners_hiding_data()),
                    )
                )
            ).all()

            return self.success(
                data={
                    "followup_requests": [
                        {
                            "status": row[0],
                            "created_at": row[1].isoformat() if row[1] else None,
                            "instrument_name": row[2],
                            "group_name": row[3],
                            "requester": {
                                "id": row[4],
                                "username": row[5],
                                "first_name": row[6],
                                "last_name": row[7],
                            },
                        }
                        for row in rows
                    ]
                }
            )


def _request_window(payload):
    """The nights a follow-up request covers, as (start, end) dates.

    Payload shapes vary by facility API, so a request whose dates cannot be
    read returns (None, None) and is treated as "could be any night".
    """
    if not isinstance(payload, dict):
        return (None, None)

    def parse(value):
        if not value:
            return None
        try:
            return dateutil.parser.parse(str(value)).date()
        except (ValueError, OverflowError, TypeError):
            return None

    return (parse(payload.get("start_date")), parse(payload.get("end_date")))


def _windows_overlap(first, second):
    """Whether two (start, end) date windows could share a night.

    An unknown bound is open-ended: it cannot be used to rule a clash out.
    """
    first_start, first_end = first
    second_start, second_end = second
    if first_end is not None and second_start is not None and first_end < second_start:
        return False
    if second_end is not None and first_start is not None and second_end < first_start:
        return False
    return True


class DuplicateSchedulingHandler(BaseHandler):
    @auth_or_token
    async def get(self):
        """
        ---
        summary: Objects you have scheduled that another group has too
        description: >
            For every object with a follow-up request you can read, report
            whether a group you are not in has one as well: which instrument
            and which group, so the two can be reconciled before the night
            rather than after it. Nothing about either request's payload is
            returned. Answers the question a shared instance cannot otherwise
            answer -- is someone else about to spend their time on this?
        tags:
          - sources
          - data sharing
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        async with self.AsyncSession() as session:
            mine_stmt = FollowupRequest.select(
                session.user_or_token,
                columns=[
                    FollowupRequest.obj_id,
                    FollowupRequest.id,
                    FollowupRequest.payload,
                ],
            ).where(FollowupRequest.status.notin_(_SETTLED_REQUEST_STATES))
            mine = (await session.execute(mine_stmt)).all()
            if not mine:
                return self.success(data=[])

            my_obj_ids = {row[0] for row in mine}
            my_request_ids = {row[1] for row in mine}
            my_windows = {}
            for obj_id, _, payload in mine:
                my_windows.setdefault(obj_id, []).append(_request_window(payload))

            rows = (
                await session.execute(
                    sa.select(
                        FollowupRequest.obj_id,
                        Instrument.name,
                        Group.name,
                        FollowupRequest.status,
                        FollowupRequest.payload,
                    )
                    .join(Allocation, Allocation.id == FollowupRequest.allocation_id)
                    .join(Instrument, Instrument.id == Allocation.instrument_id)
                    .join(Group, Group.id == Allocation.group_id)
                    .where(
                        # Bind the id lists as single array parameters
                        # (= ANY / != ALL), not expanded IN-lists: a user with
                        # many requests otherwise pushes the bound-parameter count
                        # past Postgres's 65535 limit and the endpoint 500s.
                        FollowupRequest.obj_id
                        == sa.any_(
                            sa.bindparam(
                                "my_obj_ids",
                                list(my_obj_ids),
                                type_=sa.ARRAY(sa.String),
                            )
                        ),
                        FollowupRequest.id
                        != sa.all_(
                            sa.bindparam(
                                "my_request_ids",
                                list(my_request_ids),
                                type_=sa.ARRAY(sa.Integer),
                            )
                        ),
                        FollowupRequest.status.notin_(_SETTLED_REQUEST_STATES),
                        Group.discoverable_data.is_(True),
                        FollowupRequest.requester_id.notin_(_owners_hiding_data()),
                    )
                    .distinct()
                )
            ).all()

            # Two groups holding the same object months apart is not a clash.
            # Only report requests whose window overlaps one of ours; a request
            # with no readable window could be for any night, so it is reported
            # rather than assumed harmless.
            return self.success(
                data=[
                    {
                        "obj_id": row[0],
                        "instrument_name": row[1],
                        "group_name": row[2],
                        "status": row[3],
                    }
                    for row in rows
                    if any(
                        _windows_overlap(mine_window, _request_window(row[4]))
                        for mine_window in my_windows.get(row[0], [(None, None)])
                    )
                ]
            )
