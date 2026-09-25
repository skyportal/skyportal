import traceback
from typing import Annotated

import arrow
import sqlalchemy as sa
from pydantic import Field
from skyportal_py_models.moving_objects import (
    MovingObjectFollowupPostBody,
    MovingObjectTrackPostBody,
)
from sqlalchemy.orm import joinedload
from tornado.ioloop import IOLoop

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env

from ...models import Broker, Instrument
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
from ..base import BaseHandler
from .broker import alert_permissions

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
                        {
                            d.get("ztf_object_id")
                            for d in measured
                            if d.get("ztf_object_id")
                        }
                    ),
                }
            )

    async def _check_known(self, broker, measured, body, session):
        """Whether JPL already knows this object, with the negative verified.

        The control comes from the same night as the track: a detection whose
        solar-system object is named in the alert itself. Without one, the
        check reports unverified rather than claiming a discovery.
        """
        from astropy.time import Time

        from ...utils.jpl_sbident import check_known_object, obscode_for_survey

        obscode = await obscode_for_survey(session, body.survey)
        control = await IOLoop.current().run_in_executor(
            None,
            lambda: broker.broker_class.find_control_detection(
                broker,
                measured[0]["jd"],
                session,
                survey=body.survey,
                permissions=alert_permissions(self.current_user, session),
            ),
        )

        def obs_time_for(jd):
            return Time(float(jd), format="jd", scale="utc").to_datetime()

        return await IOLoop.current().run_in_executor(
            None,
            lambda: check_known_object(
                measured, obs_time_for, obscode=obscode or "500", control=control
            ),
        )

    async def _measure(self, broker, detection, body, session):
        """One detection measured in its difference cutout."""
        from ...broker_apis._thumbnails import decode_cutout

        cutouts = await IOLoop.current().run_in_executor(
            None,
            lambda: broker.broker_class.get_cutouts(
                broker,
                str(detection["candid"]),
                session,
                survey=body.survey,
                permissions=alert_permissions(self.current_user, session),
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

            try:
                data = await IOLoop.current().run_in_executor(
                    None,
                    lambda: broker.broker_class.get_track(
                        broker,
                        track_id,
                        session,
                        survey=survey,
                        permissions=alert_permissions(self.current_user, session),
                    ),
                )
            except Exception as e:
                return self.error(f"Error fetching track from {broker.name}: {e}")
            return self.success(data=data)
