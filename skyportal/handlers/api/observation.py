from baselayer.app.access import permissions, auth_or_token
import arrow
import pandas as pd
from sqlalchemy.orm import joinedload
from astropy.time import Time

from ..base import BaseHandler
from ...models import (
    DBSession,
    Telescope,
    Instrument,
    InstrumentField,
    ExecutedObservation,
)


class ObservationHandler(BaseHandler):
    @permissions(['System admin'])
    async def post(self):
        """
        ---
        description: Ingest a set of ExecutedObservations
        tags:
          - galaxies
        requestBody:
          content:
            application/json:
              schema: ObservationHandlerPost
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
        telescope_name = data.get('telescope_name')
        instrument_name = data.get('instrument_name')
        observation_data = data.get('observation_data')

        if observation_data is None:
            return self.error(message="Missing observation_data")

        telescope = (
            Telescope.query_records_accessible_by(
                self.current_user,
            )
            .filter(
                Telescope.name == telescope_name,
            )
            .first()
        )
        if telescope is None:
            return self.error(message="Missing telescope {telescope_name}")

        instrument = (
            Instrument.query_records_accessible_by(
                self.current_user,
                options=[
                    joinedload(Instrument.fields, InstrumentField.tiles),
                ],
            )
            .filter(
                Instrument.telescope == telescope,
                Instrument.name == instrument_name,
            )
            .first()
        )
        if instrument is None:
            return self.error(message=f"Missing instrument {instrument_name}")

        obstable = pd.DataFrame.from_dict(observation_data)
        bands = {1: 'g', 2: 'r', 3: 'i', 4: 'z', 5: 'J'}

        observations = []
        obs_grouped_by_exp = obstable.groupby('expid')
        for group_name, df_group in obs_grouped_by_exp:
            field_id = int(df_group["field"].median())
            field = InstrumentField.query.filter_by(
                instrument_id=instrument.id, field_id=field_id
            ).first()
            if field is None:
                return self.error(message=f"Missing field {field_id}")

            if instrument_name == "ZTF":
                processed_fraction = len(df_group["field"]) / 64.0
            else:
                processed_fraction = 1

            observations.append(
                ExecutedObservation(
                    instrument_id=instrument.id,
                    observation_id=int(df_group["expid"].median()),
                    field_id=field.id,
                    obstime=Time(df_group["jd"].median(), format='jd').datetime,
                    seeing=df_group["sciinpseeing"].median(),
                    limmag=df_group["diffmaglim"].median(),
                    exposure_time=df_group["exptime"].median(),
                    filt=bands[int(df_group["fid"].median())],
                    processed_fraction=processed_fraction,
                )
            )

        for observation in observations:
            DBSession().add(observation)
        self.verify_and_commit()

        return self.success()

    @auth_or_token
    def get(self):
        """
        ---
          description: Retrieve all observations
          tags:
            - observations
          parameters:
            - in: telescope_name
              name: name
              schema:
                type: string
              description: Filter by telescope name
            - in: instrument_name
              name: name
              schema:
                type: string
              description: Filter by instrument name
            - in: start_date
              name: name
              schema:
                type: string
              description: Filter by start date
            - in: end_date
              name: name
              schema:
                type: string
              description: Filter by end date
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfObservation
            400:
              content:
                application/json:
                  schema: Error
        """

        data = self.get_json()

        telescope_name = data.get('telescope_name')
        instrument_name = data.get('instrument_name')
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        telescope = (
            Telescope.query_records_accessible_by(
                self.current_user,
            )
            .filter(
                Telescope.name == telescope_name,
            )
            .first()
        )
        if telescope is None:
            return self.error(message=f"Missing telescope {telescope_name}")

        instrument = (
            Instrument.query_records_accessible_by(
                self.current_user,
                options=[
                    joinedload(Instrument.fields, InstrumentField.tiles),
                ],
            )
            .filter(
                Instrument.telescope == telescope,
                Instrument.name == instrument_name,
            )
            .first()
        )
        if instrument is None:
            return self.error(message=f"Missing instrument {instrument_name}")

        if start_date is None:
            return self.error(message="Missing start_date")

        if end_date is None:
            return self.error(message="Missing end_date")

        query = ExecutedObservation.query_records_accessible_by(
            self.current_user, mode="read"
        )

        start_date = arrow.get(start_date.strip()).datetime
        end_date = arrow.get(end_date.strip()).datetime

        query = query.filter(ExecutedObservation.instrument_id == instrument.id)
        query = query.filter(ExecutedObservation.obstime >= start_date)
        query = query.filter(ExecutedObservation.obstime <= end_date)

        observations = query.all()
        self.verify_and_commit()
        return self.success(data=observations)
