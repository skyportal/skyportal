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


def add_observations(instrument_id, obstable):
    """Post executed observations for a given instrument.
    obstable is a pandas DataFrame of the form:

   observation_id  field_id       obstime   seeing    limmag  exposure_time  \
0        84434604         1  2.458599e+06  1.57415  20.40705             30
1        84434651         1  2.458599e+06  1.58120  20.49405             30
2        84434696         1  2.458599e+06  1.64995  20.56030             30
3        84434741         1  2.458599e+06  1.54945  20.57400             30
4        84434788         1  2.458599e+06  1.62870  20.60385             30

  filter  processed_fraction airmass
0   ztfr                 1.0    None
1   ztfr                 1.0    None
2   ztfr                 1.0    None
3   ztfr                 1.0    None
4   ztfr                 1.0    None
     """

    session = Session()
    try:
        observations = []
        for index, row in obstable.iterrows():
            field_id = int(row["field_id"])
            field = (
                session.query(InstrumentField)
                .filter_by(instrument_id=instrument_id, field_id=field_id)
                .first()
            )
            if field is None:
                return log(
                    f"Unable to add observations for instrument {instrument_id}: Missing field {field_id}"
                )

            observation = (
                session.query(ExecutedObservation)
                .filter_by(
                    instrument_id=instrument_id, observation_id=row["observation_id"]
                )
                .first()
            )
            if observation is not None:
                log(
                    f"Observation {row['observation_id']} for instrument {instrument_id} already exists... continuing."
                )

            observations.append(
                ExecutedObservation(
                    instrument_id=instrument_id,
                    observation_id=row["observation_id"],
                    instrument_field_id=field.id,
                    obstime=Time(row["obstime"], format='jd').datetime,
                    seeing=row["seeing"],
                    limmag=row["limmag"],
                    exposure_time=row["exposure_time"],
                    filt=row["filter"],
                    processed_fraction=row["processed_fraction"],
                )
            )
        session.add_all(observations)
        session.commit()

        return log(f"Successfully added observations for instrument {instrument_id}")
    except Exception as e:
        return log(f"Unable to add observations for instrument {instrument_id}: {e}")
    finally:
        Session.remove()


class ObservationHandler(BaseHandler):
    @permissions(['Upload data'])
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

        if not all(
            k in observation_data
            for k in [
                'observation_id',
                'field_id',
                'obstime',
                'filter',
                'exposure_time',
            ]
        ):
            return self.error(
                "observation_id, field_id, obstime, filter, and exposure_time required in observation_data."
            )

        for filt in observation_data["filter"]:
            if filt not in instrument.filters:
                return self.error(f"Filter {filt} not present in {instrument.filters}")

        # fill in any missing optional parameters
        optional_parameters = [
            'airmass',
            'seeing',
            'limmag',
        ]
        for key in optional_parameters:
            if key not in observation_data:
                observation_data[key] = [None] * len(observation_data['observation_id'])

        if "processed_fraction" not in observation_data:
            observation_data["processed_fraction"] = [1] * len(
                observation_data['observation_id']
            )

        obstable = pd.DataFrame.from_dict(observation_data)
        # run async
        IOLoop.current().run_in_executor(
            None,
            lambda: add_observations(instrument.id, obstable),
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
            - in: query
              name: telescope_name
              required: true
              schema:
                type: string
              description: Filter by telescope name
            - in: query
              name: instrument_name
              required: true
              schema:
                type: string
              description: Filter by instrument name
            - in: query
              name: start_date
              required: true
              schema:
                type: string
              description: Filter by start date
            - in: query
              name: end_date
              required: true
              schema:
                type: string
              description: Filter by end date
            - in: query
              name: localizationDateobs
              schema:
                type: string
              description: |
                Event time in ISO 8601 format (`YYYY-MM-DDTHH:MM:SS.sss`).
                Taken from Localization.dateobs queried from /api/localization
                endpoint or dateobs in GcnEvent page table.
            - in: query
              name: localizationName
              schema:
                type: string
              description: |
                Name of localization / skymap to use.
                Can be found in Localization.localization_name queried from
                /api/localization endpoint or skymap name in GcnEvent page
                table.
            - in: query
              name: localizationCumprob
              schema:
                type: number
              description: |
                Cumulative probability up to which to include fields
            - in: query
              name: returnProbability
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to include integrated probability. Defaults to false.
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfExecutedObservations
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
        localization_dateobs = data.get('localizationDateobs', None)
        localization_name = data.get('localizationName', None)
        localization_cumprob = data.get("localizationCumprob", 0.95)
        return_probability = data.get("returnProbability", False)

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
        if localization_dateobs is not None:
            if localization_name is not None:
                localization = (
                    Localization.query_records_accessible_by(self.current_user)
                    .filter(
                        Localization.dateobs == localization_dateobs,
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
                    .filter(GcnEvent.dateobs == localization_dateobs)
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
            localizationtile_subquery = (
                sa.select(LocalizationTile.probdensity, cum_prob).filter(
                    LocalizationTile.localization_id == localization.id
                )
            ).subquery()

            min_probdensity = (
                sa.select(
                    sa.func.min(localizationtile_subquery.columns.probdensity)
                ).filter(
                    localizationtile_subquery.columns.cum_prob <= localization_cumprob
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

    @auth_or_token
    def delete(self, observation_id):
        """
        ---
        description: Delete an observation
        tags:
          - observations
        parameters:
          - in: path
            name: observation_id
            required: true
            schema:
              type: integer
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

        observation = ExecutedObservation.query.filter_by(id=observation_id).first()

        if observation is None:
            return self.error("ExecutedObservation not found", status=404)

        if not observation.is_accessible_by(self.current_user, mode="delete"):
            return self.error(
                "Insufficient permissions: ExecutedObservation can only be deleted by original poster"
            )

        DBSession().delete(observation)
        self.verify_and_commit()

        return self.success()
