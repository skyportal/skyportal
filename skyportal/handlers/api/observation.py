from baselayer.app.access import permissions, auth_or_token
from baselayer.log import make_log
import arrow
import healpix_alchemy as ha
import pandas as pd
import sqlalchemy as sa
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import sessionmaker, scoped_session
from tornado.ioloop import IOLoop
from astropy.time import Time

from ..base import BaseHandler
from ...models import (
    DBSession,
    GcnEvent,
    Localization,
    LocalizationTile,
    Telescope,
    Instrument,
    InstrumentField,
    InstrumentFieldTile,
    ExecutedObservation,
)


log = make_log('api/observation')

Session = scoped_session(sessionmaker(bind=DBSession.session_factory.kw["bind"]))


class ObservationHandler(BaseHandler):
    @permissions(['System admin'])
    def post(self):
        """
        ---
        description: Ingest a set of ExecutedObservations
        tags:
          - observations
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

        # run async
        IOLoop.current().run_in_executor(
            None,
            lambda: add_tiles(instrument.id, instrument.name, obstable),
        )

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
                  schema: ArrayOfObservations
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
        localization_cumprob = data.get("localization_cumprob", 0.95)
        return_probability = data.get("return_probability", False)

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
                    joinedload(Instrument.fields),
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

        obs_query = ExecutedObservation.query_records_accessible_by(
            self.current_user, mode="read"
        )

        start_date = arrow.get(start_date.strip()).datetime
        end_date = arrow.get(end_date.strip()).datetime

        obs_query = obs_query.filter(ExecutedObservation.instrument_id == instrument.id)
        obs_query = obs_query.filter(ExecutedObservation.obstime >= start_date)
        obs_query = obs_query.filter(ExecutedObservation.obstime <= end_date)

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

            cum_prob = (
                sa.func.sum(
                    LocalizationTile.probdensity * LocalizationTile.healpix.area
                )
                .over(order_by=LocalizationTile.probdensity.desc())
                .label('cum_prob')
            )
            subquery1 = (
                sa.select(LocalizationTile.probdensity, cum_prob).filter(
                    LocalizationTile.localization_id == localization.id
                )
            ).subquery()

            min_probdensity = (
                sa.select(sa.func.min(subquery1.columns.probdensity)).filter(
                    subquery1.columns.cum_prob <= localization_cumprob
                )
            ).scalar_subquery()

            tiles_subquery = (
                sa.select(InstrumentField.id)
                .filter(
                    LocalizationTile.localization_id == localization.id,
                    LocalizationTile.probdensity >= min_probdensity,
                    InstrumentFieldTile.instrument_id == instrument.id,
                    InstrumentFieldTile.instrument_field_id == InstrumentField.id,
                    InstrumentFieldTile.healpix.overlaps(LocalizationTile.healpix),
                )
                .subquery()
            )

            obs_query = obs_query.join(
                tiles_subquery,
                ExecutedObservation.instrument_field_id == tiles_subquery.c.id,
            )

            if return_probability:
                union = (
                    sa.select(
                        ha.func.union(InstrumentFieldTile.healpix).label('healpix')
                    )
                    .filter(
                        InstrumentFieldTile.instrument_id == instrument.id,
                        InstrumentFieldTile.instrument_field_id
                        == ExecutedObservation.instrument_field_id,
                        ExecutedObservation.obstime >= start_date,
                        ExecutedObservation.obstime <= end_date,
                    )
                    .subquery()
                )
                prob = sa.func.sum(
                    LocalizationTile.probdensity
                    * (union.columns.healpix * LocalizationTile.healpix).area
                )
                query = sa.select(prob).filter(
                    LocalizationTile.localization_id == localization.id,
                    union.columns.healpix.overlaps(LocalizationTile.healpix),
                )
                intprob = DBSession().execute(query).scalar_one()

        observations = obs_query.all()

        if return_probability:
            data = {
                "observations": [o.to_dict() for o in observations],
                "probability": intprob,
            }
        else:
            data = observations

        return self.success(data=data)


def add_tiles(instrument_id, instrument_name, obstable):
    session = Session()
    try:
        bands = {1: 'g', 2: 'r', 3: 'i', 4: 'z', 5: 'J'}

        observations = []
        obs_grouped_by_exp = obstable.groupby('expid')
        for group_name, df_group in obs_grouped_by_exp:
            field_id = int(df_group["field"].median())
            field = (
                session.query(InstrumentField)
                .filter_by(instrument_id=instrument_id, field_id=field_id)
                .first()
            )
            if field is None:
                return log(
                    f"Unable to add observations for instrument {instrument_id}: Missing field {field_id}"
                )

            if instrument_name == "ZTF":
                processed_fraction = len(df_group["field"]) / 64.0
            else:
                processed_fraction = 1

            observations.append(
                ExecutedObservation(
                    instrument_id=instrument_id,
                    observation_id=int(df_group["expid"].median()),
                    instrument_field_id=field.id,
                    obstime=Time(df_group["jd"].median(), format='jd').datetime,
                    seeing=df_group["sciinpseeing"].median(),
                    limmag=df_group["diffmaglim"].median(),
                    exposure_time=df_group["exptime"].median(),
                    filt=bands[int(df_group["fid"].median())],
                    processed_fraction=processed_fraction,
                )
            )
        session.add_all(observations)
        session.commit()

        return log(f"Successfully add observations for instrument {instrument_id}")
    except Exception as e:
        return log(f"Unable to add observations for instrument {instrument_id}: {e}")
    finally:
        Session.remove()
