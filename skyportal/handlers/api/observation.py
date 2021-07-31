from baselayer.app.access import permissions, auth_or_token
import arrow
import healpix_alchemy as ha
import numpy as np
import pandas as pd
from sqlalchemy.orm import joinedload
from sqlalchemy import func, union
from astropy.time import Time

from ..base import BaseHandler
from ...models import (
    DBSession,
    GcnEvent,
    InstrumentFieldTile,
    Localization,
    LocalizationTile,
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
            - in: dateobs
              name: name
              schema:
                type: string
              description: Filter by GcnEvent event
            - in: localization_name
              name: name
              schema:
                type: string
              description: Filter by GcnEvent localization
            - in: localization_cumprob
              name: name
              schema:
                type: string
              description: Filter by GcnEvent localization cumulative probability
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
        dateobs = data.get('dateobs')
        localization_name = data.get('localization_name')
        localization_cumprob = data.get("localization_cumprob", 1.01)

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

        # optional: slice by GcnEvent localization
        if dateobs is not None:
            if localization_name is not None:
                localization = (
                    Localization.query_records_accessible_by(self.current_user)
                    .filter(
                        Localization.dateobs == dateobs,
                        Localization.localization_name == localization_name,
                    )
                    .first()
                )
                if localization is None:
                    return self.error("Localization not found", status=404)
            else:
                event = (
                    GcnEvent.query_records_accessible_by(
                        self.current_user,
                        options=[
                            joinedload(GcnEvent.localizations),
                        ],
                    )
                    .filter(GcnEvent.dateobs == dateobs)
                    .first()
                )
                if event is None:
                    return self.error("GCN event not found", status=404)
                localization = event.localizations[-1]

            # compute probability in the fields based on the localization
            a, b = LocalizationTile, InstrumentFieldTile
            a_lo = a.nested_lo.label('a_lo')
            a_hi = a.nested_hi.label('a_hi')
            b_lo = b.nested_lo.label('b_lo')
            b_hi = b.nested_hi.label('b_hi')

            query1 = DBSession().query(
                a_lo,
                a_hi,
                b_lo,
                b_hi,
                InstrumentFieldTile.instrument_id.label('instrument_id'),
                InstrumentFieldTile.instrument_field_id.label('instrument_field_id'),
                LocalizationTile.localization_id.label('localization_id'),
                LocalizationTile.probdensity.label('probdensity'),
            )

            query2 = union(
                query1.join(b, a_lo.between(b_lo, b_hi)),
                query1.join(b, b_lo.between(a_lo, a_hi)),
            ).cte()

            lo = func.greatest(query2.c.a_lo, query2.c.b_lo)
            hi = func.least(query2.c.a_hi, query2.c.b_hi)
            area = (hi - lo + 1) * ha.healpix.PIXEL_AREA
            prob = func.sum(query2.c.probdensity * area).label('probability')

            query = (
                DBSession()
                .query(query2.c.instrument_field_id, prob)
                .filter(query2.c.localization_id == localization.id)
                .filter(query2.c.instrument_id == instrument.id)
                .group_by(query2.c.localization_id, query2.c.instrument_field_id)
            )

            tiles = query.all()
            field_ids = np.array([tile[0] for tile in tiles])
            probs = np.array([tile[1] for tile in tiles])
            idx = np.argsort(probs)[::-1]
            field_ids, probs = field_ids[idx], probs[idx]
            cumprobs = np.cumsum(probs)

            if instrument.name == "ZTF":
                # ZTF has two overlapping grids
                field_ids_keep = field_ids[
                    np.where(cumprobs <= 2 * localization_cumprob)[0]
                ]
            else:
                field_ids_keep = field_ids[
                    np.where(cumprobs <= localization_cumprob)[0]
                ]

            observations_all = []
            for observation in observations:
                # is the field in the cumulative percentage requested?
                if observation.field_id not in field_ids_keep:
                    continue
                idx = np.where(field_ids == observation.field_id)[0][0]
                observations_all.append(
                    {**observation.to_dict(), 'probability': probs[idx]}
                )
            observations = observations_all

        self.verify_and_commit()
        return self.success(data=observations)
