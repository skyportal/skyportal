import traceback
from typing import Annotated

import arrow
import sqlalchemy as sa
from pydantic import BaseModel, Field
from skyportal_py_models.moving_objects import (
    MovingObjectFollowupPostBody,
    MovingObjectTrackKnownPostBody,
    MovingObjectTrackMPCPostBody,
    MovingObjectTrackPostBody,
)
from sqlalchemy.orm import joinedload
from tornado.ioloop import IOLoop

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from baselayer.app.flow import Flow

from ...models import Broker, Instrument, Obj, SharingService, SharingServiceSubmission
from ...utils.moving_object_track import (
    NotMeasurable,
    band_flux_agreements,
    measure_cutout,
    motion_residuals,
    position_angles,
    render_epoch,
)
from ...utils.moving_objects import (
    add_instrument_fields,
    find_observable_sequence,
    get_ephemeris,
)
from ...utils.mpc_submission import (
    ack_email,
    default_submitter,
    track_psv,
)
from ..base import BaseHandler
from .broker import alert_permissions_async

_, cfg = load_env()


class MovingObjectFollowupHandler(BaseHandler):
    @auth_or_token
    async def post(
        self,
        obj_name: Annotated[str, Field(description="Name of the moving object")],
        *,
        body: MovingObjectFollowupPostBody = None,
    ):
        """
        ---
        summary: Find a continuous sequence of observations for a moving object
        description: Find a continuous sequence of observations for a moving object in an instrument's field. N observations of a given exposure time and filter are scheduled at the optimal times between start_time and end_time.
        tags:
        - moving objects
        - follow-up
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
        body = self.parse_body(MovingObjectFollowupPostBody)
        instrument_id = body.instrument_id
        nb_obs = body.exposure_count
        obs_time = body.exposure_time
        start_time = body.start_time
        end_time = body.end_time
        band = body.filter
        primary_only = body.primary_only
        airmass_limit = body.airmass_limit
        moon_distance_limit = body.moon_distance_limit
        sun_altitude_limit = body.sun_altitude_limit
        references_only = body.references_only

        if instrument_id is None:
            return self.error("Instrument ID must be provided")
        if start_time is None:
            return self.error("Start time must be provided")
        if end_time is None:
            return self.error("End time must be provided")
        if nb_obs is None:
            return self.error("Number of exposures must be provided")
        if obs_time is None:
            return self.error("Exposure time must be provided")
        if band is None:
            return self.error("Filter must be provided")

        try:
            instrument_id = int(instrument_id)
        except ValueError:
            return self.error("Instrument ID must be an integer")

        try:
            nb_obs = int(nb_obs)
        except ValueError:
            return self.error("Number of exposures must be an integer")

        try:
            obs_time = float(obs_time)
        except ValueError:
            return self.error("Exposure time must be a number")

        try:
            start_time = arrow.get(start_time).naive
        except arrow.parser.ParserError:
            return self.error("Invalid start time")

        try:
            end_time = arrow.get(end_time).naive
        except arrow.parser.ParserError:
            return self.error("Invalid end time")

        # if the delta T between start and end time > 7 days, return an error
        if (end_time - start_time).total_seconds() > 7 * 24 * 3600:
            return self.error("Time window must be less than 7 days")

        async with self.AsyncSession() as session:
            try:
                instrument = await session.scalar(
                    sa.select(Instrument)
                    .where(Instrument.id == instrument_id)
                    .options(joinedload(Instrument.telescope))
                )
                if instrument is None:
                    return self.error(f"Instrument {instrument_id} not found")
                instrument_id, instrument_name = instrument.id, instrument.name
                observer = instrument.telescope.observer
                if observer is None:
                    return self.error("No observer can be found for this instrument")

                df = get_ephemeris(
                    obj_name,
                    start_time,
                    end_time,
                    observer,
                    airmass_limit=airmass_limit,
                    moon_distance_limit=moon_distance_limit,
                    sun_altitude_limit=sun_altitude_limit,
                )

                # `add_instrument_fields` does sync DB work — bridge via greenlet
                dfs, field_id_to_radec = await session.run_sync(
                    lambda sync_session: add_instrument_fields(
                        df,
                        instrument_id,
                        instrument_name,
                        sync_session,
                        observer,
                        primary_only=primary_only,
                        airmass_limit=airmass_limit,
                        moon_distance_limit=moon_distance_limit,
                        references_only=references_only,
                    )
                )

                observations = find_observable_sequence(
                    dfs, field_id_to_radec, observer, nb_obs, obs_time, band=band
                )

                return self.success(data=observations)
            except Exception as e:
                traceback.print_exc()
                return self.error(f"Error: {e}")


async def known_object_check(user, broker, detections, survey, session):
    """Whether JPL already knows this object, with the negative verified, as a
    blocking call to run off the event loop.

    The control comes from the same night as the track: a detection whose
    solar-system object is named in the alert itself. Without one, the
    check reports unverified rather than claiming a discovery.
    """
    from astropy.time import Time

    from ...utils.jpl_sbident import check_known_object, obscode_for_survey

    obscode = await obscode_for_survey(session, survey)
    permissions = await alert_permissions_async(user, session)
    control = await IOLoop.current().run_in_executor(
        None,
        lambda: broker.broker_class.find_control_detection(
            broker,
            detections[0]["jd"],
            session,
            survey=survey,
            permissions=permissions,
        ),
    )

    def obs_time_for(jd):
        return Time(float(jd), format="jd", scale="utc").to_datetime()

    return lambda: check_known_object(
        detections, obs_time_for, obscode=obscode or "500", control=control
    )


class MovingObjectTrackHandler(BaseHandler):
    @auth_or_token
    async def post(self, *, body: MovingObjectTrackPostBody = None):
        """
        ---
        summary: Measure a linked moving-object track
        description: |
          Measure each detection of a track in its difference cutout and report
          what decides whether the track is one real object: per-epoch
          significance and centroid offset, how the position angle turns along
          the arc, the residual about a smooth motion model, and whether the
          pixels order the bands the way the photometry does.

          Measuring needs real pixel values, so this requires a broker that
          returns FITS. A broker serving rendered PNGs is refused rather than
          measured, because a display stretch has already destroyed the flux
          scale.
        tags:
          - moving objects
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
        body = self.parse_body(MovingObjectTrackPostBody)
        detections = [d.model_dump() for d in body.detections]
        if not detections:
            return self.error("A track needs at least one detection.")

        async with self.AsyncSession() as session:
            broker = await session.scalar(
                Broker.select(self.current_user).where(Broker.id == body.broker_id)
            )
            if broker is None:
                return self.error(f"No broker with id {body.broker_id}")
            if (
                body.measure_cutouts
                and not broker.broker_class.implements()["get_cutouts"]
            ):
                return self.error(f"Broker {broker.name} does not serve cutouts.")

            measured, failures = [], []
            for detection in sorted(detections, key=lambda d: d["jd"]):
                # Geometry alone needs no pixels, so no broker call either.
                if not body.measure_cutouts:
                    measured.append(dict(detection))
                    continue
                try:
                    row = await self._measure(broker, detection, body, session)
                except Exception as e:
                    failures.append(
                        {"candid": str(detection["candid"]), "error": str(e)}
                    )
                    continue
                measured.append(row)

            if not measured:
                return self.error(
                    "No detection could be measured. "
                    + "; ".join(f["error"] for f in failures[:3])
                )

            residuals = motion_residuals(measured)
            known = None
            if body.check_known:
                known = await self._check_known(broker, measured, body, session)
            return self.success(
                data={
                    "detections": measured,
                    "known_object": known,
                    "failures": failures,
                    "position_angles": position_angles(measured),
                    "motion": residuals,
                    "band_flux": band_flux_agreements(measured),
                    "arc_days": measured[-1]["jd"] - measured[0]["jd"],
                    "n_detections": len(measured),
                    # The count that makes the case: a real object arrives under
                    # a new object id almost every epoch.
                    "n_object_ids": len(
                        {d.get("objectId") for d in measured if d.get("objectId")}
                    ),
                }
            )

    async def _check_known(self, broker, measured, body, session):
        check = await known_object_check(
            self.current_user, broker, measured, body.survey, session
        )
        return await IOLoop.current().run_in_executor(None, check)

    async def _measure(self, broker, detection, body, session):
        """One detection measured in its difference cutout."""
        from ...broker_apis._thumbnails import decode_cutout

        permissions = await alert_permissions_async(self.current_user, session)
        cutouts = await IOLoop.current().run_in_executor(
            None,
            lambda: broker.broker_class.get_cutouts(
                broker,
                str(detection["candid"]),
                session,
                survey=body.survey,
                permissions=permissions,
            ),
        )
        payload = (cutouts or {}).get(body.cutout)
        if payload is None:
            raise ValueError(f"no {body.cutout} for candid {detection['candid']}")
        if isinstance(payload, str) and payload.startswith("data:image"):
            raise ValueError(
                "this broker returns rendered images, whose flux scale is gone"
            )

        data, header = decode_cutout(payload, body.survey)
        try:
            measurement = measure_cutout(data)
        except NotMeasurable as e:
            raise ValueError(str(e)) from e

        row = {**detection, **measurement}
        if body.include_images:
            row["png"] = render_epoch(data, body.survey, header)
        return row


class MovingObjectTrackLookupHandler(BaseHandler):
    @auth_or_token
    async def get(self, track_id: str):
        """
        ---
        summary: Get a linked track and its detections
        description: |
          Fetch one track from the broker by its id, with the detections that
          make it up. The track stores candids only, so the positions are
          fetched alongside them: a vetting view needs jd/ra/dec/mag/band.

          Detections the requester's streams do not cover are omitted and
          counted, so a partially visible track cannot pass for a short one.
        tags:
          - moving objects
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
        broker_id = self.get_argument("broker_id", None)
        survey = self.get_argument("survey", "ZTF")

        async with self.AsyncSession() as session:
            if broker_id is not None:
                broker = await session.scalar(
                    Broker.select(self.current_user).where(Broker.id == int(broker_id))
                )
            else:
                broker = await session.scalar(
                    Broker.select(self.current_user).where(
                        Broker.active.is_(True), Broker.default_alert_search.is_(True)
                    )
                )
            if broker is None:
                return self.error("No broker to look the track up on")
            if not hasattr(broker.broker_class, "get_track"):
                return self.error(f"Broker {broker.name} does not serve tracks.")

            permissions = await alert_permissions_async(self.current_user, session)
            try:
                data = await IOLoop.current().run_in_executor(
                    None,
                    lambda: broker.broker_class.get_track(
                        broker,
                        track_id,
                        session,
                        survey=survey,
                        permissions=permissions,
                    ),
                )
            except Exception as e:
                return self.error(f"Error fetching track from {broker.name}: {e}")
            return self.success(data=data)


class MovingObjectTrackKnownHandler(BaseHandler):
    @auth_or_token
    async def post(self, track_id: str, *, body: MovingObjectTrackKnownPostBody = None):
        """
        ---
        summary: Check a track against the known small bodies
        description: |
          Start a JPL check of whether a track is an already-known small body
          and return at once, since JPL takes minutes to answer. The verdict is
          pushed to the requester's browser as skyportal/TRACK_KNOWN_OBJECT.
        tags:
          - moving objects
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
        body = self.parse_body(MovingObjectTrackKnownPostBody)
        user_id = self.associated_user_object.id
        async with self.AsyncSession() as session:
            broker = await session.scalar(
                Broker.select(self.current_user).where(Broker.id == body.broker_id)
            )
            if broker is None:
                return self.error(f"No broker with id {body.broker_id}")
            if not hasattr(broker.broker_class, "get_track"):
                return self.error(f"Broker {broker.name} does not serve tracks.")
            permissions = await alert_permissions_async(self.current_user, session)
            try:
                track = await IOLoop.current().run_in_executor(
                    None,
                    lambda: broker.broker_class.get_track(
                        broker,
                        track_id,
                        session,
                        survey=body.survey,
                        permissions=permissions,
                    ),
                )
            except Exception as e:
                return self.error(f"Error fetching track from {broker.name}: {e}")
            if not track["detections"]:
                return self.error(f"No detection of {track_id} is visible to you.")
            check = await known_object_check(
                self.current_user, broker, track["detections"], body.survey, session
            )

        def run():
            try:
                verdict = check()
            except Exception as e:
                verdict = {
                    "known": None,
                    "verified": False,
                    "matches": [],
                    "nearby": [],
                    "errors": [str(e)],
                    "reason": f"the check failed: {e}",
                }
            Flow().push(
                user_id,
                "skyportal/TRACK_KNOWN_OBJECT",
                {"track_id": track_id, "known_object": verdict},
            )

        IOLoop.current().run_in_executor(None, run)
        return self.success()


class MovingObjectTrackMPCQuery(BaseModel):
    broker_id: int = Field(description="Broker the track is fetched from.")
    sharing_service_id: int | None = Field(
        default=None,
        description="Sharing service whose MPC header to preview the submission with.",
    )
    submitter: str | None = Field(
        default=None,
        description="Name to preview the submission under. Defaults to the requester's.",
    )
    exclude_candids: str | None = Field(
        default=None,
        description="Comma-separated candids of detections to leave out.",
    )


def track_submissions(*track_ids):
    return (
        SharingServiceSubmission.publish_to_mpc.is_(True),
        SharingServiceSubmission.mpc_payload["track_id"].astext.in_(track_ids),
    )


class MovingObjectTrackMPCHandler(BaseHandler):
    async def _track(self, session, broker_id, track_id):
        broker = await session.scalar(
            Broker.select(self.current_user).where(Broker.id == broker_id)
        )
        if broker is None:
            raise ValueError(f"No broker with id {broker_id}")
        if not hasattr(broker.broker_class, "get_track"):
            raise ValueError(f"Broker {broker.name} does not serve tracks.")
        permissions = await alert_permissions_async(self.current_user, session)
        return await IOLoop.current().run_in_executor(
            None,
            lambda: broker.broker_class.get_track(
                broker, track_id, session, survey="ZTF", permissions=permissions
            ),
        )

    @auth_or_token
    async def get(self, track_id: str):
        """
        ---
        summary: Preview a track's MPC submission
        description: |
          The MPC submissions already made for a ZTF track and, given a sharing
          service, the ADES PSV it would be filed with now.
        tags:
          - moving objects
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
        query = self.parse_query(MovingObjectTrackMPCQuery)
        async with self.AsyncSession() as session:
            submissions = await session.scalars(
                SharingServiceSubmission.select(
                    session.user_or_token,
                    options=[joinedload(SharingServiceSubmission.user)],
                )
                .where(*track_submissions(track_id))
                .order_by(SharingServiceSubmission.created_at.desc())
            )
            data = {
                "submissions": [
                    {
                        "id": s.id,
                        "sharing_service_id": s.sharing_service_id,
                        "username": s.user.username,
                        "submitter": s.custom_publishing_string,
                        "mpc_status": s.mpc_status,
                        "mpc_submission_id": s.mpc_submission_id,
                        "created_at": s.created_at,
                    }
                    for s in submissions.unique().all()
                ]
            }
            if query.sharing_service_id is None:
                return self.success(data=data)

            sharing_service = await session.scalar(
                SharingService.select(session.user_or_token).where(
                    SharingService.id == query.sharing_service_id
                )
            )
            if sharing_service is None:
                return self.error(
                    f"No sharing service available with ID {query.sharing_service_id}"
                )
            submitter = query.submitter or default_submitter(
                self.associated_user_object
            )
            exclude = [c for c in (query.exclude_candids or "").split(",") if c]
            try:
                track = await self._track(session, query.broker_id, track_id)
                data["psv"] = track_psv(track, sharing_service, submitter, exclude)
            except Exception as e:
                return self.error(f"Cannot submit {track_id}: {e}")
            data["submitter"] = submitter
            data["members_withheld"] = track["members_withheld"]
            return self.success(data=data)

    @auth_or_token
    async def post(self, track_id: str, *, body: MovingObjectTrackMPCPostBody = None):
        """
        ---
        summary: Submit a ZTF track to the MPC
        description: |
          Queue a vetted track for the Minor Planet Center, filed under the
          requester's name with the sharing service's MPC header. The PSV is
          fixed now, so the MPC receives what the reviewer previewed.
        tags:
          - moving objects
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
        body = self.parse_body(MovingObjectTrackMPCPostBody)
        user = self.associated_user_object
        async with self.AsyncSession() as session:
            sharing_service = await session.scalar(
                SharingService.select(session.user_or_token).where(
                    SharingService.id == body.sharing_service_id
                )
            )
            if sharing_service is None:
                return self.error(
                    f"No sharing service available with ID {body.sharing_service_id}"
                )
            if not sharing_service.enable_sharing_with_mpc:
                return self.error(
                    f"Sharing service {sharing_service.name} does not submit to the MPC."
                )
            obj = await session.scalar(
                Obj.select(session.user_or_token).where(Obj.id == body.obj_id)
            )
            if obj is None:
                return self.error(f"No object available with ID {body.obj_id}")

            submitter = body.submitter or default_submitter(user)
            try:
                ack_email(user, sharing_service)
                track = await self._track(session, body.broker_id, track_id)
                psv = body.psv or track_psv(
                    track, sharing_service, submitter, body.exclude_candids
                )
            except Exception as e:
                return self.error(f"Cannot submit {track_id}: {e}")

            # Checked across every group: the MPC must not get a track twice.
            existing = await session.scalar(
                sa.select(SharingServiceSubmission).where(
                    *track_submissions(track_id, track["id"]),
                    SharingServiceSubmission.mpc_status.in_(
                        ["pending", "processing", "submitted"]
                    ),
                )
            )
            if existing is not None:
                return self.error(
                    f"{track['id']} is already {existing.mpc_status} to the MPC "
                    f"(submission {existing.id})."
                )

            submission = SharingServiceSubmission(
                sharing_service_id=sharing_service.id,
                obj_id=obj.id,
                user_id=user.id,
                custom_publishing_string=submitter,
                auto_submission=False,
                publish_to_mpc=True,
                mpc_status="pending",
                mpc_payload={
                    "track_id": track["id"],
                    "broker_id": body.broker_id,
                    "submitter": submitter,
                    "exclude_candids": body.exclude_candids,
                    "psv": psv,
                },
            )
            session.add(submission)
            await session.commit()
            self.push_all(
                action="skyportal/REFRESH_SHARING_SERVICE_SUBMISSIONS",
                payload={"sharing_service_id": sharing_service.id},
            )
            return self.success(data={"id": submission.id})
