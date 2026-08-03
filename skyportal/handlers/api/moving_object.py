import traceback

import arrow
import sqlalchemy as sa
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import joinedload

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env

from ...models import Instrument
from ...utils.moving_objects import (
    add_instrument_fields,
    find_observable_sequence,
    get_ephemeris,
)
from ..base import BaseHandler

_, cfg = load_env()


class MovingObjectFollowupPostBody(BaseModel):
    """Request body for a moving object follow-up observation plan."""

    model_config = ConfigDict(extra="forbid")

    instrument_id: int | None = Field(
        default=None, description="ID of the instrument to use"
    )
    exposure_count: int | None = Field(default=None, description="Number of exposures")
    exposure_time: float | None = Field(
        default=None, description="Exposure time in seconds"
    )
    start_time: str | None = Field(
        default=None, description="Start time of the obversations' time window"
    )
    end_time: str | None = Field(
        default=None, description="End time of the obversations' time window"
    )
    filter: str | None = Field(default=None, description="Filter to use")
    primary_only: bool = Field(
        default=True,
        description="Only consider an instrument's fields from it's primary grid, if any",
    )
    airmass_limit: float = Field(
        default=2.5, description="Maximum airmass for observations. Default is 2.5"
    )
    moon_distance_limit: float = Field(
        default=30,
        description="Minimum distance from the Moon in degrees. Default is 30",
    )
    sun_altitude_limit: float = Field(
        default=-18,
        description="Maximum altitude of the Sun in degrees. Default is -18",
    )
    references_only: bool = Field(
        default=False,
        description="Only consider fields that have reference images available",
    )


class MovingObjectFollowupHandler(BaseHandler):
    @auth_or_token
    async def post(self, obj_name: str, *, body: MovingObjectFollowupPostBody = None):
        """
        ---
        summary: Find a continuous sequence of observations for a moving object
        description: Find a continuous sequence of observations for a moving object in an instrument's field. N observations of a given exposure time and filter are scheduled at the optimal times between start_time and end_time.
        tags:
        - moving objects
        - follow-up
        parameters:
          - in: path
            name: obj_name
            required: true
            schema:
                type: string
            description: Name of the moving object
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
