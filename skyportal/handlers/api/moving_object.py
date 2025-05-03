import traceback

import arrow
import sqlalchemy as sa

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env

from ...models import (
    DBSession,
    Instrument,
)
from ...utils.moving_objects import (
    add_instrument_fields,
    find_observable_sequence,
    get_ephemeris,
)
from ...utils.parse import str_to_bool
from ..base import BaseHandler

_, cfg = load_env()


class MovingObjectFollowupHandler(BaseHandler):
    @auth_or_token
    def post(self, obj_name):
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
        requestBody:
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            instrument_id:
                                type: integer
                                description: ID of the instrument to use
                            exposure_count:
                                type: integer
                                description: Number of exposures
                            exposure_time:
                                type: number
                                description: Exposure time in seconds
                            start_time:
                                type: string
                                format: date-time
                                description: Start time of the obversations' time window
                            end_time:
                                type: string
                                format: date-time
                                description: End time of the obversations' time window
                            filter:
                                type: string
                                description: Filter to use
                            primary_only:
                                type: boolean
                                description: Only consider an instrument's fields from it's primary grid, if any
                                required: false
                            airmass_limit:
                                type: number
                                description: Maximum airmass for observations. Default is 2.5
                                required: false
                            moon_distance_limit:
                                type: number
                                description: Minimum distance from the Moon in degrees. Default is 30
                                required: false
                            sun_altitude_limit:
                                type: number
                                description: Maximum altitude of the Sun in degrees. Default is -18
                                required: false
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
        instrument_id = data.get("instrument_id")
        nb_obs = data.get("exposure_count")
        obs_time = data.get("exposure_time")
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        band = data.get("filter")
        primary_only = data.get("primary_only", True)
        airmass_limit = data.get("airmass_limit", 2.5)
        moon_distance_limit = data.get("moon_distance_limit", 30)
        sun_altitude_limit = data.get("sun_altitude_limit", -18)
        references_only = data.get("references_only", False)

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
            start_time = arrow.get(start_time).datetime
        except arrow.parser.ParserError:
            return self.error("Invalid start time")

        try:
            end_time = arrow.get(end_time).datetime
        except arrow.parser.ParserError:
            return self.error("Invalid end time")

        # if the delta T between start and end time > 7 days, return an error
        if (end_time - start_time).total_seconds() > 7 * 24 * 3600:
            return self.error("Time window must be less than 7 days")

        if str_to_bool(references_only, default=False):
            references_only = True
        else:
            references_only = False

        with DBSession() as session:
            try:
                instrument = session.scalar(
                    sa.select(Instrument).where(Instrument.id == instrument_id)
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

                dfs, field_id_to_radec = add_instrument_fields(
                    df,
                    instrument_id,
                    instrument_name,
                    session,
                    observer,
                    primary_only=primary_only,
                    airmass_limit=airmass_limit,
                    moon_distance_limit=moon_distance_limit,
                    references_only=references_only,
                )

                observations = find_observable_sequence(
                    dfs, field_id_to_radec, observer, nb_obs, obs_time, band=band
                )

                return self.success(data=observations)
            except Exception as e:
                traceback.print_exc()
                return self.error(f"Error: {e}")
