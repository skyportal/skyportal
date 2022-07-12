from baselayer.app.access import permissions, auth_or_token
from baselayer.log import make_log
import arrow
import astropy
import functools
import healpix_alchemy as ha
import humanize
import json
from marshmallow.exceptions import ValidationError
import numpy as np
import pandas as pd
from regions import Regions
import requests
import sqlalchemy as sa
from sqlalchemy.orm import joinedload, undefer
from sqlalchemy.orm import sessionmaker, scoped_session
from tornado.ioloop import IOLoop
import urllib
from astropy.time import Time
import io
from io import StringIO

from baselayer.app.flow import Flow
from baselayer.app.env import load_env
from baselayer.app.custom_exceptions import AccessError
from ..base import BaseHandler
from ...models import (
    DBSession,
    Allocation,
    GcnEvent,
    Group,
    Localization,
    LocalizationTile,
    Telescope,
    Instrument,
    InstrumentField,
    InstrumentFieldTile,
    ExecutedObservation,
    QueuedObservation,
    SurveyEfficiencyForObservationPlan,
    SurveyEfficiencyForObservations,
)

from ...models.schema import ObservationExternalAPIHandlerPost
from ...utils.simsurvey import (
    get_simsurvey_parameters,
)
from .instrument import add_tiles
from .observation_plan import observation_simsurvey, observation_simsurvey_plot

env, cfg = load_env()
TREASUREMAP_URL = cfg['app.treasuremap_endpoint']

log = make_log('api/observation')

Session = scoped_session(sessionmaker(bind=DBSession.session_factory.kw["bind"]))

MAX_OBSERVATIONS = 1000


def add_queued_observations(instrument_id, obstable):
    """Fetch queued observations from ZTF scheduler.
    instrument_id: int
        ID of the instrument
    obstable: pandas.DataFrame
        A dataframe returned from the ZTF scheduler queue
    """

    session = Session()

    try:
        observations = []
        for index, row in obstable.iterrows():
            field_id = int(row["field_id"])
            field = (
                session.query(InstrumentField)
                .filter(
                    InstrumentField.instrument_id == instrument_id,
                    InstrumentField.field_id == field_id,
                )
                .first()
            )
            if field is None:
                return log(
                    f"Unable to add observations for instrument {instrument_id}: Missing field {field_id}"
                )

            observations.append(
                QueuedObservation(
                    queue_name=row['queue_name'],
                    instrument_id=row['instrument_id'],
                    instrument_field_id=field.id,
                    obstime=row['obstime'],
                    validity_window_start=row['validity_window_start'],
                    validity_window_end=row['validity_window_end'],
                    exposure_time=row["exposure_time"],
                    filt=row['filter'],
                )
            )
        session.add_all(observations)
        session.commit()

        flow = Flow()
        flow.push('*', "skyportal/REFRESH_QUEUED_OBSERVATIONS")

        return log(
            f"Successfully added queued observations for instrument {instrument_id}"
        )
    except Exception as e:
        return log(
            f"Unable to add queued observations for instrument {instrument_id}: {e}"
        )
    finally:
        Session.remove()


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
    # if the fields do not yet exist, we need to add them
    if ('RA' in obstable) and ('Dec' in obstable) and not ('field_id' in obstable):
        instrument = session.query(Instrument).get(instrument_id)
        regions = Regions.parse(instrument.region, format='ds9')
        field_data = obstable[['RA', 'Dec']]
        field_ids = add_tiles(
            instrument.id, instrument.name, regions, field_data, session=session
        )
        obstable['field_id'] = field_ids

    try:
        observations = []
        for index, row in obstable.iterrows():
            field_id = int(row["field_id"])
            field = (
                session.query(InstrumentField)
                .filter(
                    InstrumentField.instrument_id == instrument_id,
                    InstrumentField.field_id == field_id,
                )
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
                continue

            # enable multiple obstime formats
            try:
                # can catch iso and isot this way
                obstime = Time(row["obstime"])
            except ValueError:
                # otherwise catch jd as the numerical example
                obstime = Time(row["obstime"], format='jd')

            observations.append(
                ExecutedObservation(
                    instrument_id=instrument_id,
                    observation_id=row["observation_id"],
                    instrument_field_id=field.id,
                    obstime=obstime.datetime,
                    seeing=row["seeing"],
                    limmag=row["limmag"],
                    exposure_time=row["exposure_time"],
                    filt=row["filter"],
                    processed_fraction=row["processed_fraction"],
                )
            )
        session.add_all(observations)
        session.commit()

        flow = Flow()
        flow.push('*', "skyportal/REFRESH_OBSERVATIONS")

        return log(f"Successfully added observations for instrument {instrument_id}")
    except Exception as e:
        return log(f"Unable to add observations for instrument {instrument_id}: {e}")
    finally:
        Session.remove()


def get_observations(
    session,
    start_date,
    end_date,
    telescope_name=None,
    instrument_name=None,
    localization_dateobs=None,
    localization_name=None,
    localization_cumprob=0.95,
    return_statistics=False,
    includeGeoJSON=False,
    observation_status='executed',
    n_per_page=100,
    page_number=1,
):
    f"""Query for list of observations

    Parameters
    ----------
    session: sqlalchemy.Session
        Database session for this transaction
    start_date: datetime
        Start time of the observations
    end_date: datetime
        End time of the observations
    telescope_name : skyportal.models.instrument.Telescope.name
        The name of the telescope that the request is made based on
    instrument_name : skyportal.models.instrument.Instrument.name
        The name of the instrument that the request is made based on
    localization_dateobs : skyportal.models.Localization.dateobs
        Event time in ISO 8601 format (`YYYY-MM-DDTHH:MM:SS.sss`).
        Each localization is associated with a specific GCNEvent by
        the date the event happened, and this date is used as a unique
        identifier. It can be therefore found as Localization.dateobs,
        queried from the /api/localization endpoint or dateobs in the
        GcnEvent page table.
    localization_name : skyportal.models.Localization.localization_name
        Name of localization / skymap to use.
        Can be found in Localization.localization_name queried from
        /api/localization endpoint or skymap name in GcnEvent page table.
    localization_cumprob : number
        Cumulative probability up to which to include fields.
        Defaults to 0.95.
    return_statistics: bool
        Boolean indicating whether to include integrated probability and area.
        Defaults to false.
    includeGeoJSON: bool
                Boolean indicating whether to include associated GeoJSON fields. Defaults to false.
    observation_status: str
        Whether to include queued or executed observations. Defaults to
            executed.
    n_per_page: int
        Number of observations to return per paginated request. Defaults to 100. Can be no larger than {MAX_OBSERVATIONS}.
    page_number: int
        Page number for paginated query results. Defaults to 1.
    Returns
    -------
    dict
        observations : list
            ExecutedObservations in dictionary format
        probability: number
            Integrated probability
        area: number
            Area covered in square degrees
    """

    if return_statistics and localization_dateobs is None:
        raise ValueError(
            'localization_dateobs must be specified if return_statistics=True'
        )

    if observation_status == "executed":
        Observation = ExecutedObservation
    elif observation_status == "queued":
        Observation = QueuedObservation
    else:
        raise ValueError('observation_status should be executed or queued')

    if includeGeoJSON:
        obs_query = (
            Observation.select(
                session.user_or_token,
                mode="read",
            )
            .options(
                joinedload(Observation.field).undefer(InstrumentField.contour_summary)
            )
            .options(
                joinedload(Observation.instrument).joinedload(Instrument.telescope)
            )
        )
    else:

        obs_query = (
            Observation.select(
                session.user_or_token,
                mode="read",
            )
            .options(joinedload(Observation.field))
            .options(
                joinedload(Observation.instrument).joinedload(Instrument.telescope)
            )
        )

    obs_query = obs_query.where(Observation.obstime >= start_date)
    obs_query = obs_query.where(Observation.obstime <= end_date)

    # optional: slice by Instrument
    if telescope_name is not None and instrument_name is not None:
        telescope = session.scalars(
            Telescope.select(session.user_or_token).where(
                Telescope.name == telescope_name
            )
        ).first()
        if telescope is None:
            raise ValueError(f"Missing telescope {telescope_name}")

        instrument = session.scalars(
            Instrument.select(
                session.user_or_token, options=[joinedload(Instrument.fields)]
            ).where(
                Instrument.telescope == telescope, Instrument.name == instrument_name
            )
        ).first()
        if instrument is None:
            return ValueError(f"Missing instrument {instrument_name}")

        obs_query = obs_query.where(Observation.instrument_id == instrument.id)

    # optional: slice by GcnEvent localization
    if localization_dateobs is not None:
        if localization_name is not None:
            localization = session.scalars(
                Localization.select(session.user_or_token).where(
                    Localization.dateobs == localization_dateobs,
                    Localization.localization_name == localization_name,
                )
            ).first()
            if localization is None:
                raise ValueError("Localization not found")
        else:
            event = session.scalars(
                GcnEvent.select(
                    session.user_or_token, options=[joinedload(GcnEvent.localizations)]
                ).where(GcnEvent.dateobs == localization_dateobs)
            ).first()
            if event is None:
                raise ValueError("GCN event not found")
            localization = event.localizations[-1]

        cum_prob = (
            sa.func.sum(LocalizationTile.probdensity * LocalizationTile.healpix.area)
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
            ).filter(localizationtile_subquery.columns.cum_prob <= localization_cumprob)
        ).scalar_subquery()

        if telescope_name is not None and instrument_name is not None:
            tiles_subquery = (
                sa.select(InstrumentField.id)
                .filter(
                    LocalizationTile.localization_id == localization.id,
                    LocalizationTile.probdensity >= min_probdensity,
                    InstrumentFieldTile.instrument_id == instrument.id,
                    InstrumentFieldTile.instrument_field_id == InstrumentField.id,
                    InstrumentFieldTile.healpix.overlaps(LocalizationTile.healpix),
                )
                .distinct()
                .subquery()
            )
        else:
            tiles_subquery = (
                sa.select(InstrumentField.id)
                .filter(
                    LocalizationTile.localization_id == localization.id,
                    LocalizationTile.probdensity >= min_probdensity,
                    InstrumentFieldTile.instrument_field_id == InstrumentField.id,
                    InstrumentFieldTile.healpix.overlaps(LocalizationTile.healpix),
                )
                .distinct()
                .subquery()
            )

        obs_query = obs_query.join(
            tiles_subquery,
            Observation.instrument_field_id == tiles_subquery.c.id,
        )

        if return_statistics:
            if telescope_name is not None and instrument_name is not None:
                union = (
                    sa.select(
                        ha.func.union(InstrumentFieldTile.healpix).label('healpix')
                    )
                    .filter(
                        InstrumentFieldTile.instrument_id == instrument.id,
                        InstrumentFieldTile.instrument_field_id
                        == Observation.instrument_field_id,
                        Observation.obstime >= start_date,
                        Observation.obstime <= end_date,
                    )
                    .distinct()
                    .subquery()
                )
            else:
                union = (
                    sa.select(
                        ha.func.union(InstrumentFieldTile.healpix).label('healpix')
                    )
                    .filter(
                        InstrumentFieldTile.instrument_field_id
                        == Observation.instrument_field_id,
                        Observation.obstime >= start_date,
                        Observation.obstime <= end_date,
                    )
                    .distinct()
                    .subquery()
                )

            area = sa.func.sum(union.columns.healpix.area)
            prob = sa.func.sum(
                LocalizationTile.probdensity
                * (union.columns.healpix * LocalizationTile.healpix).area
            )
            query_area = sa.select(area).filter(
                LocalizationTile.localization_id == localization.id,
                LocalizationTile.probdensity >= min_probdensity,
                union.columns.healpix.overlaps(LocalizationTile.healpix),
            )
            query_prob = sa.select(prob).filter(
                LocalizationTile.localization_id == localization.id,
                LocalizationTile.probdensity >= min_probdensity,
                union.columns.healpix.overlaps(LocalizationTile.healpix),
            )
            intprob = session.execute(query_prob).scalar_one()
            intarea = session.execute(query_area).scalar_one()

            if intprob is None:
                intprob = 0.0
            if intarea is None:
                intarea = 0.0

    total_matches = session.scalar(sa.select(sa.func.count()).select_from(obs_query))
    if n_per_page is not None:
        obs_query = (
            obs_query.distinct()
            .limit(n_per_page)
            .offset((page_number - 1) * n_per_page)
        )

    observations = session.scalars(obs_query).all()
    observations_list = []
    for o in observations:
        obs_dict = o.to_dict()
        obs_dict['field'] = obs_dict['field'].to_dict()
        obs_dict['instrument'] = obs_dict['instrument'].to_dict()
        observations_list.append(obs_dict)

    data = {
        "observations": observations_list,
        "totalMatches": int(total_matches),
    }

    if includeGeoJSON:
        # features are JSON representations that the d3 stuff understands.
        # We use these to render the contours of the sky localization and
        # locations of the transients.

        geojson = []
        fields_in = []
        for ii, observation in enumerate(observations):
            if observation.instrument_field_id not in fields_in:
                fields_in.append(observation.instrument_field_id)
                geojson.append(observation.field.contour_summary)
            else:
                continue

        if return_statistics:
            data = {
                **data,
                "probability": intprob,
                "area": intarea * (180.0 / np.pi) ** 2,  # sq. degrees,
                "geojson": geojson,
            }
        else:
            data = {
                **data,
                "geojson": geojson,
            }

    else:
        if return_statistics:
            data = {
                **data,
                "probability": intprob,
                "area": intarea * (180.0 / np.pi) ** 2,  # sq. degrees
            }

    return data


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
        telescope_name = data.get('telescopeName')
        instrument_name = data.get('instrumentName')
        observation_data = data.get('observationData', {})

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

        unique_keys = set(list(observation_data.keys()))
        field_id_keys = {
            'observation_id',
            'field_id',
            'obstime',
            'filter',
            'exposure_time',
        }
        radec_keys = {
            'observation_id',
            'RA',
            'Dec',
            'obstime',
            'filter',
            'exposure_time',
        }
        if not field_id_keys.issubset(unique_keys) and not radec_keys.issubset(
            unique_keys
        ):
            return self.error(
                "observation_id, field_id (or RA and Dec), obstime, filter, and exposure_time required in observation_data."
            )

        if (
            ('RA' in observation_data)
            and ('Dec' in observation_data)
            and not ('field_id' in observation_data)
        ):
            if instrument.region is None:
                return self.error(
                    "instrument.region must not be None if providing only RA and Dec."
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
    async def get(self):
        """
        ---
          description: Retrieve all observations
          tags:
            - observations
          parameters:
            - in: query
              name: telescopeName
              schema:
                type: string
              description: Filter by telescope name
            - in: query
              name: instrumentName
              schema:
                type: string
              description: Filter by instrument name
            - in: query
              name: startDate
              required: true
              schema:
                type: string
              description: Filter by start date
            - in: query
              name: endDate
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
                Each localization is associated with a specific GCNEvent by
                the date the event happened, and this date is used as a unique
                identifier. It can be therefore found as Localization.dateobs,
                queried from the /api/localization endpoint or dateobs in the
                GcnEvent page table.
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
                Cumulative probability up to which to include fields.
                Defaults to 0.95.
            - in: query
              name: returnStatistics
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to include integrated probability and area. Defaults to false.
            - in: query
              name: includeGeoJSON
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to include associated GeoJSON. Defaults to
                false.
            - in: query
              name: observationStatus
              nullable: true
              schema:
                type: str
              description: |
                 Whether to include queued or executed observations.
                 Defaults to executed.
            - in: query
              name: numPerPage
              nullable: true
              schema:
                type: integer
              description: |
                Number of followup requests to return per paginated request.
                Defaults to 100. Can be no larger than {MAX_OBSERVATIONS}.
            - in: query
              name: pageNumber
              nullable: true
              schema:
                type: integer
              description: Page number for paginated query results. Defaults to 1
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

        telescope_name = self.get_query_argument('telescopeName', None)
        instrument_name = self.get_query_argument('instrumentName', None)
        start_date = self.get_query_argument('startDate')
        end_date = self.get_query_argument('endDate')
        localization_dateobs = self.get_query_argument('localizationDateobs', None)
        localization_name = self.get_query_argument('localizationName', None)
        localization_cumprob = self.get_query_argument("localizationCumprob", 0.95)
        return_statistics = self.get_query_argument("returnStatistics", False)
        includeGeoJSON = self.get_query_argument("includeGeoJSON", False)
        observation_status = self.get_query_argument("observationStatus", 'executed')
        page_number = self.get_query_argument("pageNumber", 1)
        n_per_page = self.get_query_argument("numPerPage", 100)

        try:
            page_number = int(page_number)
        except ValueError:
            return self.error("Invalid page number value.")
        try:
            n_per_page = int(n_per_page)
        except (ValueError, TypeError) as e:
            return self.error(f"Invalid numPerPage value: {str(e)}")

        if n_per_page > MAX_OBSERVATIONS:
            return self.error(
                f'numPerPage should be no larger than {MAX_OBSERVATIONS}.'
            )

        if start_date is None:
            return self.error(message="Missing start_date")

        if end_date is None:
            return self.error(message="Missing end_date")

        start_date = arrow.get(start_date.strip()).datetime
        end_date = arrow.get(end_date.strip()).datetime

        with self.Session() as session:
            data = get_observations(
                session,
                start_date,
                end_date,
                telescope_name=telescope_name,
                instrument_name=instrument_name,
                localization_dateobs=localization_dateobs,
                localization_name=localization_name,
                localization_cumprob=localization_cumprob,
                return_statistics=return_statistics,
                includeGeoJSON=includeGeoJSON,
                observation_status=observation_status,
                n_per_page=n_per_page,
                page_number=page_number,
            )

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

        with self.Session() as session:
            observation = session.scalars(
                ExecutedObservation.select(self.current_user).where(
                    ExecutedObservation.id == observation_id
                )
            ).first()
            if observation is None:
                return self.error("ExecutedObservation not found", status=404)

            if not observation.is_accessible_by(self.current_user, mode="delete"):
                return self.error(
                    "Insufficient permissions: ExecutedObservation can only be deleted by original poster"
                )

            session.delete(observation)
            session.commit()

            return self.success()


class ObservationASCIIFileHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Upload observation from ASCII file
        tags:
          - observations
        requestBody:
          content:
            application/json:
              schema: ObservationASCIIFileHandlerPost
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

        json = self.get_json()
        observation_data = json.pop('observationData', None)
        instrument_id = json.pop('instrumentID', None)

        if observation_data is None:
            return self.error(message="Missing observation_data")

        instrument = (
            Instrument.query_records_accessible_by(
                self.current_user,
                options=[
                    joinedload(Instrument.fields, InstrumentField.tiles),
                ],
            )
            .filter(
                Instrument.id == instrument_id,
            )
            .first()
        )
        if instrument is None:
            return self.error(message=f"Missing instrument with ID {instrument_id}")
        try:
            observation_data = pd.read_table(
                StringIO(observation_data), sep=","
            ).to_dict(orient='list')
        except Exception as e:
            return self.error(f"Unable to read in observation file: {e}")

        unique_keys = set(list(observation_data.keys()))
        field_id_keys = {
            'observation_id',
            'field_id',
            'obstime',
            'filter',
            'exposure_time',
        }
        radec_keys = {
            'observation_id',
            'RA',
            'Dec',
            'obstime',
            'filter',
            'exposure_time',
        }
        if not field_id_keys.issubset(unique_keys) and not radec_keys.issubset(
            unique_keys
        ):
            return self.error(
                "observation_id, field_id (or RA and Dec), obstime, filter, and exposure_time required in observation_data."
            )

        if (
            ('RA' in observation_data)
            and ('Dec' in observation_data)
            and not ('field_id' in observation_data)
        ):
            if instrument.region is None:
                return self.error(
                    "instrument.region must not be None if providing only RA and Dec."
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


class ObservationGCNHandler(BaseHandler):
    @auth_or_token
    async def get(self, instrument_id):
        """
        ---
          description: Get a GCN-izable summary of the observations.
          tags:
            - observations
          parameters:
            - in: path
              name: instrument_id
              required: true
              schema:
                type: string
              description: |
                ID for the instrument to submit
            - in: query
              name: startDate
              required: true
              schema:
                type: string
              description: Filter by start date
            - in: query
              name: endDate
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
                Each localization is associated with a specific GCNEvent by
                the date the event happened, and this date is used as a unique
                identifier. It can be therefore found as Localization.dateobs,
                queried from the /api/localization endpoint or dateobs in the
                GcnEvent page table.
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
                Cumulative probability up to which to include fields.
                Defaults to 0.95.
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

        start_date = self.get_query_argument('startDate')
        end_date = self.get_query_argument('endDate')
        localization_dateobs = self.get_query_argument('localizationDateobs', None)
        localization_name = self.get_query_argument('localizationName', None)
        localization_cumprob = self.get_query_argument("localizationCumprob", 0.95)

        if start_date is None:
            return self.error(message="Missing start_date")

        if end_date is None:
            return self.error(message="Missing end_date")

        start_date = arrow.get(start_date.strip()).datetime
        end_date = arrow.get(end_date.strip()).datetime

        with self.Session() as session:

            stmt = Instrument.select(self.current_user).where(
                Instrument.id == instrument_id
            )
            instrument = session.scalars(stmt).first()

            if instrument is None:
                return self.error(message=f"Invalid instrument ID {instrument_id}")

            data = get_observations(
                session,
                start_date,
                end_date,
                telescope_name=instrument.telescope.name,
                instrument_name=instrument.name,
                localization_dateobs=localization_dateobs,
                localization_name=localization_name,
                localization_cumprob=localization_cumprob,
            )

            observations = data["observations"]
            num_observations = len(observations)
            if num_observations == 0:
                return self.error('Need at least one observation to produce a GCN')

            start_observation = astropy.time.Time(
                min(obs["obstime"] for obs in observations), format='datetime'
            )
            unique_filters = list({obs["filt"] for obs in observations})
            total_time = sum(obs["exposure_time"] for obs in observations)
            probability = data["probability"]
            area = data["area"]

            stmt = GcnEvent.select(self.current_user).where(
                GcnEvent.dateobs == localization_dateobs
            )
            event = session.scalars(stmt).first()
            trigger_time = astropy.time.Time(event.dateobs, format='datetime')
            dt = start_observation.datetime - event.dateobs

            content = f"""
                SUBJECT: Follow-up of {event.gcn_notices[0].stream} trigger {trigger_time.isot} with {instrument.name}.

                We observed the localization region of {event.gcn_notices[0].stream} trigger {trigger_time.isot} UTC with {instrument.name} on the {instrument.telescope.name}. We obtained a total of {num_observations} images covering {",".join(unique_filters)} bands for a total of {total_time} seconds. The observations covered {area:.1f} square degrees beginning at {start_observation.isot} ({humanize.naturaldelta(dt)} after the burst trigger time) corresponding to ~{int(100 * probability)}% of the probability enclosed in the localization region.
                """

            return self.success(data=content)


class ObservationExternalAPIHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Retrieve observations from external API
        tags:
          - observations
        requestBody:
          content:
            application/json:
              schema: ObservationExternalAPIHandlerPost
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

        try:
            data = ObservationExternalAPIHandlerPost.load(data)
        except ValidationError as e:
            return self.error(
                f'Invalid / missing parameters: {e.normalized_messages()}'
            )

        data["requester_id"] = self.associated_user_object.id
        data["last_modified_by_id"] = self.associated_user_object.id
        data['allocation_id'] = int(data['allocation_id'])
        data['start_date'] = arrow.get(data['start_date'].strip()).datetime
        data['end_date'] = arrow.get(data['end_date'].strip()).datetime

        allocation = Allocation.get_if_accessible_by(
            data['allocation_id'], self.current_user, raise_if_none=True
        )
        instrument = allocation.instrument

        if instrument.api_classname_obsplan is None:
            return self.error('Instrument has no remote observation plan API.')

        if not instrument.api_class_obsplan.implements()['retrieve']:
            return self.error(
                'Submitting executed observation plan requests to this Instrument is not available.'
            )

        try:
            # we now retrieve and commit to the database the
            # executed observations
            instrument.api_class_obsplan.retrieve(
                allocation, data['start_date'], data['end_date']
            )
            self.push_notification(
                'Observation ingestion in progress. Should be available soon.'
            )
        except Exception as e:
            return self.error(f"Error in querying instrument API: {e}")

    @permissions(['Upload data'])
    def get(self, allocation_id):
        """
        ---
        description: Retrieve queued observations from external API
        tags:
          - observations
        parameters:
          - in: path
            name: allocation_id
            required: true
            schema:
              type: string
            description: |
              ID for the allocation to retrieve
          - in: query
            name: startDate
            required: false
            schema:
              type: string
            description: Filter by start date
          - in: query
            name: endDate
            required: false
            schema:
              type: string
            description: Filter by end date
          - in: query
            name: queuesOnly
            required: false
            schema:
              type: bool
            description: Return queue only (do not commit observations)
        responses:
          200:
            content:
              application/json:
                schema: ArrayOfPlannedObservations
          400:
            content:
              application/json:
                schema: Error
        """

        start_date = self.get_query_argument('startDate', None)
        end_date = self.get_query_argument('endDate', None)
        queues_only = self.get_query_argument('queuesOnly', False)

        if not queues_only:
            if start_date is None:
                return self.error(message="Missing start_date")

            if end_date is None:
                return self.error(message="Missing end_date")

            start_date = arrow.get(start_date.strip()).datetime
            end_date = arrow.get(end_date.strip()).datetime

        data = {}
        data["requester_id"] = self.associated_user_object.id
        data["last_modified_by_id"] = self.associated_user_object.id
        data['allocation_id'] = int(allocation_id)
        data['start_date'] = start_date
        data['end_date'] = end_date

        allocation = Allocation.get_if_accessible_by(
            data['allocation_id'], self.current_user, raise_if_none=True
        )
        instrument = allocation.instrument

        if instrument.api_classname_obsplan is None:
            return self.error('Instrument has no remote observation plan API.')

        if not instrument.api_class_obsplan.implements()['queued']:
            return self.error(
                'Submitting executed observation plan requests to this Instrument is not available.'
            )

        try:
            # we now retrieve and commit to the database the
            # executed observations
            queue_names = instrument.api_class_obsplan.queued(
                allocation,
                data['start_date'],
                data['end_date'],
                queues_only=queues_only,
            )
            if not queues_only:
                self.push_notification(
                    'Planned observation ingestion in progress. Should be available soon.'
                )
            return self.success(data={'queue_names': queue_names})
        except Exception as e:
            return self.error(f"Error in querying instrument API: {e}")

    @permissions(['Upload data'])
    def delete(self, allocation_id):
        """
        ---
        description: Retrieve queued observations from external API
        tags:
          - observations
        parameters:
          - in: path
            name: allocation_id
            required: true
            schema:
              type: string
            description: |
              ID for the allocation to delete queue
          - in: query
            name: queueName
            required: true
            schema:
              type: string
            description: Queue name to remove
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

        if 'queueName' not in data:
            return self.error('queueName is a required argument')
        queue_name = data['queueName']

        data["requester_id"] = self.associated_user_object.id
        data["last_modified_by_id"] = self.associated_user_object.id
        data['allocation_id'] = allocation_id

        allocation = Allocation.get_if_accessible_by(
            data['allocation_id'], self.current_user, raise_if_none=True
        )
        instrument = allocation.instrument

        if instrument.api_classname_obsplan is None:
            return self.error('Instrument has no remote observation plan API.')

        if not instrument.api_class_obsplan.implements()['remove_queue']:
            return self.error('Cannot delete queues from this Instrument.')

        try:
            # we now retrieve and commit to the database the
            # executed observations
            instrument.api_class_obsplan.remove_queue(
                allocation, queue_name, self.associated_user_object.username
            )
        except Exception as e:
            return self.error(f"Error in querying instrument API: {e}")


class ObservationTreasureMapHandler(BaseHandler):
    @auth_or_token
    def post(self, instrument_id):
        """
        ---
        description: Submit the observation plan to treasuremap.space
        tags:
          - observation_plan_requests
        parameters:
          - in: path
            name: instrument_id
            required: true
            schema:
              type: string
            description: |
              ID for the instrument to submit
          - in: query
            name: startDate
            required: true
            schema:
              type: string
            description: Filter by start date
          - in: query
            name: endDate
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
              Each localization is associated with a specific GCNEvent by
              the date the event happened, and this date is used as a unique
              identifier. It can be therefore found as Localization.dateobs,
              queried from the /api/localization endpoint or dateobs in the
              GcnEvent page table.
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
              Cumulative probability up to which to include fields.
              Defaults to 0.95.
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
        start_date = data.get('startDate')
        end_date = data.get('endDate')
        localization_dateobs = data.get('localizationDateobs', None)
        localization_name = data.get('localizationName', None)
        localization_cumprob = data.get("localizationCumprob", 0.95)

        if start_date is None:
            return self.error(message="Missing start_date")

        if end_date is None:
            return self.error(message="Missing end_date")

        start_date = arrow.get(start_date.strip()).datetime
        end_date = arrow.get(end_date.strip()).datetime

        with self.Session() as session:

            instrument = session.scalars(
                Instrument.select(
                    session.user_or_token, options=[joinedload(Instrument.telescope)]
                ).where(Instrument.id == instrument_id)
            ).first()
            if instrument is None:
                return self.error(message=f"Invalid instrument ID {instrument_id}")

            data = get_observations(
                session,
                start_date,
                end_date,
                telescope_name=instrument.telescope.name,
                instrument_name=instrument.name,
                localization_dateobs=localization_dateobs,
                localization_name=localization_name,
                localization_cumprob=localization_cumprob,
                return_statistics=True,
            )

            observations = data["observations"]
            if len(observations) == 0:
                return self.error(
                    'Need at least one observation to send to Treasure Map'
                )

            event = session.scalars(
                GcnEvent.select(
                    session.user_or_token, options=[joinedload(GcnEvent.gcn_notices)]
                ).where(GcnEvent.dateobs == localization_dateobs)
            ).first()
            if event is None:
                return self.error(
                    message=f"Invalid GcnEvent dateobs: {localization_dateobs}"
                )

            stmt = Allocation.select(session.user_or_token).where(
                Allocation.instrument_id == instrument.id
            )
            allocations = session.scalars(stmt).all()

            api_token = None
            for allocation in allocations:
                altdata = allocation.altdata
                if altdata and 'TREASUREMAP_API_TOKEN' in altdata:
                    api_token = altdata['TREASUREMAP_API_TOKEN']
            if not api_token:
                raise self.error('Missing allocation information.')

            graceid = event.graceid
            payload = {"graceid": graceid, "api_token": api_token}

            pointings = []
            for obs in observations:
                pointing = {}
                pointing["ra"] = obs["field"].ra
                pointing["dec"] = obs["field"].dec
                pointing["band"] = obs["filt"]
                pointing["instrumentid"] = int(instrument.treasuremap_id)
                pointing["status"] = "completed"
                pointing["time"] = Time(obs["obstime"], format='datetime').isot
                pointing["depth"] = obs["limmag"]
                pointing["depth_unit"] = "ab_mag"
                pointings.append(pointing)
            payload["pointings"] = pointings

            url = urllib.parse.urljoin(TREASUREMAP_URL, 'api/v0/pointings')
            r = requests.post(url=url, json=payload)
            r.raise_for_status()
            request_json = r.json()
            errors = request_json["ERRORS"]
            if len(errors) > 0:
                return self.error(f'TreasureMap upload failed: {errors}')
            self.push_notification('TreasureMap upload succeeded')
            return self.success()

    @auth_or_token
    def delete(self, instrument_id):
        """
        ---
        description: Remove observations from treasuremap.space.
        tags:
          - observationplan_requests
        parameters:
          - in: path
            name: instrument_id
            required: true
            schema:
              type: string
            description: |
              ID for the instrument to submit
          - in: query
            name: localizationDateobs
            schema:
              type: string
            description: |
              Event time in ISO 8601 format (`YYYY-MM-DDTHH:MM:SS.sss`).
              Each localization is associated with a specific GCNEvent by
              the date the event happened, and this date is used as a unique
              identifier. It can be therefore found as Localization.dateobs,
              queried from the /api/localization endpoint or dateobs in the
              GcnEvent page table.
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        data = self.get_json()
        localization_dateobs = data.get('localizationDateobs', None)

        instrument = (
            Instrument.query_records_accessible_by(
                self.current_user,
                options=[
                    joinedload(Instrument.telescope),
                ],
            )
            .filter(
                Instrument.id == instrument_id,
            )
            .first()
        )
        if instrument is None:
            return self.error(message=f"Invalid instrument ID {instrument_id}")

        event = (
            GcnEvent.query_records_accessible_by(
                self.current_user,
                options=[
                    joinedload(GcnEvent.gcn_notices),
                ],
            )
            .filter(GcnEvent.dateobs == localization_dateobs)
            .first()
        )
        if event is None:
            return self.error(
                message=f"Invalid GcnEvent dateobs: {localization_dateobs}"
            )

        allocations = (
            Allocation.query_records_accessible_by(self.current_user)
            .filter(Allocation.instrument_id == instrument.id)
            .all()
        )

        api_token = None
        for allocation in allocations:
            altdata = allocation.altdata
            if altdata and 'TREASUREMAP_API_TOKEN' in altdata:
                api_token = altdata['TREASUREMAP_API_TOKEN']
        if not api_token:
            raise self.error('Missing allocation information.')

        graceid = event.graceid
        payload = {
            "graceid": graceid,
            "api_token": api_token,
            "instrumentid": instrument.treasuremap_id,
        }

        baseurl = urllib.parse.urljoin(TREASUREMAP_URL, 'api/v0/cancel_all')
        url = f"{baseurl}?{urllib.parse.urlencode(payload)}"
        r = requests.post(url=url)
        r.raise_for_status()
        request_text = r.text
        if "successfully" not in request_text:
            return self.error(f'TreasureMap delete failed: {request_text}')
        self.push_notification(f'TreasureMap delete succeeded: {request_text}.')
        return self.success()


def retrieve_observations_and_simsurvey(
    session,
    start_date,
    end_date,
    localization_id,
    instrument_id,
    survey_efficiency_analysis_id,
    survey_efficiency_analysis_type,
):

    """Query for observations and run survey analysis

    Parameters
    ----------

    session: sqlalchemy.Session
        Database session for this transaction
    start_date: datetime
        Start time of the observations
    end_date: datetime
        End time of the observations
    localization_id : int
        The id of the skyportal.models.localization.Localization that the request is made based on
    instrument_id : int
        The id of the skyportal.models.instrument.Instrument that the request is made based on
    survey_efficiency_analysis_id : int
        The id of the survey efficiency analysis for the request (either skyportal.models.survey_efficiency.SurveyEfficiencyForObservations or skyportal.models.survey_efficiency.SurveyEfficiencyForObservationPlan).
    survey_efficiency_analysis_type : str
        Either SurveyEfficiencyForObservations or SurveyEfficiencyForObservationPlan.
    """

    if survey_efficiency_analysis_type == "SurveyEfficiencyForObservations":
        survey_efficiency_analysis = session.scalars(
            sa.select(SurveyEfficiencyForObservations).where(
                SurveyEfficiencyForObservations.id == survey_efficiency_analysis_id
            )
        ).first()
        if survey_efficiency_analysis is None:
            raise ValueError(
                f'No SurveyEfficiencyForObservations with ID {survey_efficiency_analysis_id}'
            )
    elif survey_efficiency_analysis_type == "SurveyEfficiencyForObservations":
        survey_efficiency_analysis = session.scalars(
            sa.select(SurveyEfficiencyForObservationPlan).where(
                SurveyEfficiencyForObservationPlan.id == survey_efficiency_analysis_id
            )
        ).first()
        if survey_efficiency_analysis is None:
            raise ValueError(
                f'No SurveyEfficiencyForObservationPlan with ID {survey_efficiency_analysis_id}'
            )
    else:
        raise ValueError(
            'survey_efficiency_analysis_type must be SurveyEfficiencyForObservations or SurveyEfficiencyForObservationPlan'
        )

    payload = survey_efficiency_analysis.payload

    instrument = session.scalars(
        sa.select(Instrument)
        .options(joinedload(Instrument.telescope))
        .where(Instrument.id == instrument_id)
    ).first()

    localization = session.scalars(
        sa.select(Localization).where(Localization.id == localization_id)
    ).first()

    data = get_observations(
        session,
        start_date,
        end_date,
        telescope_name=instrument.telescope.name,
        instrument_name=instrument.name,
        localization_dateobs=localization.dateobs,
        localization_name=localization.localization_name,
        localization_cumprob=payload["localization_cumprob"],
    )

    observations = data["observations"]

    if len(observations) == 0:
        raise ValueError('Need at least one observation to run SimSurvey')

    unique_filters = list({observation["filt"] for observation in observations})

    if not set(unique_filters).issubset(set(instrument.sensitivity_data.keys())):
        raise ValueError('Need sensitivity_data for all filters present')

    for filt in unique_filters:
        if not {'exposure_time', 'limiting_magnitude', 'zeropoint'}.issubset(
            set(instrument.sensitivity_data[filt].keys())
        ):
            raise ValueError(
                f'Sensitivity_data dictionary missing keys for filter {filt}'
            )

    # get height and width
    stmt = (
        InstrumentField.select(session.user_or_token)
        .where(InstrumentField.id == observations[0]["field"]["id"])
        .options(undefer(InstrumentField.contour_summary))
    )
    field = session.scalars(stmt).first()
    if field is None:
        raise ValueError(
            'Missing field {obs_dict["field"]["id"]} required to estimate field size'
        )
    contour_summary = field.to_dict()["contour_summary"]["features"][0]
    coordinates = np.array(contour_summary["geometry"]["coordinates"])
    width = np.max(coordinates[:, 0]) - np.min(coordinates[:, 0])
    height = np.max(coordinates[:, 1]) - np.min(coordinates[:, 1])

    observation_simsurvey(
        observations,
        localization.id,
        instrument.id,
        survey_efficiency_analysis_id,
        survey_efficiency_analysis_type,
        width=width,
        height=height,
        number_of_injections=payload['number_of_injections'],
        number_of_detections=payload['number_of_detections'],
        detection_threshold=payload['detection_threshold'],
        minimum_phase=payload['minimum_phase'],
        maximum_phase=payload['maximum_phase'],
        model_name=payload['model_name'],
        optional_injection_parameters=payload['optional_injection_parameters'],
    )


class ObservationSimSurveyHandler(BaseHandler):
    @auth_or_token
    async def get(self, instrument_id):
        """
        ---
        description: Perform simsurvey efficiency calculation
        tags:
          - observations
        parameters:
          - in: path
            name: instrument_id
            required: true
            schema:
              type: string
            description: |
              ID for the instrument to submit
          - in: query
            name: startDate
            required: true
            schema:
              type: string
            description: Filter by start date
          - in: query
            name: endDate
            required: true
            schema:
              type: string
            description: Filter by end date
          - in: query
            name: localizationDateobs
            required: true
            schema:
              type: string
            description: |
              Event time in ISO 8601 format (`YYYY-MM-DDTHH:MM:SS.sss`).
              Each localization is associated with a specific GCNEvent by
              the date the event happened, and this date is used as a unique
              identifier. It can be therefore found as Localization.dateobs,
              queried from the /api/localization endpoint or dateobs in the
              GcnEvent page table.
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
              Cumulative probability up to which to include fields.
              Defaults to 0.95.
          - in: query
            name: numberInjections
            nullable: true
            schema:
              type: number
            description: |
              Number of simulations to evaluate efficiency with. Defaults to 1000.
          - in: query
            name: numberDetections
            nullable: true
            schema:
              type: number
            description: |
              Number of detections required for detection. Defaults to 1.
          - in: query
            name: detectionThreshold
            nullable: true
            schema:
              type: number
            description: |
              Threshold (in sigmas) required for detection. Defaults to 5.
          - in: query
            name: minimumPhase
            nullable: true
            schema:
              type: number
            description: |
              Minimum phase (in days) post event time to consider detections. Defaults to 0.
          - in: query
            name: maximumPhase
            nullable: true
            schema:
              type: number
            description: |
              Maximum phase (in days) post event time to consider detections. Defaults to 3.
          - in: query
            name: model_name
            nullable: true
            schema:
              type: string
            description: |
              Model to simulate efficiency for. Must be one of kilonova, afterglow, or linear. Defaults to kilonova.
          - in: query
            name: optionalInjectionParameters
            type: object
            additionalProperties:
              type: array
              items:
                type: string
                description: |
                  Optional parameters to specify the injection type, along
                  with a list of possible values (to be used in a dropdown UI)
          - in: query
            name: group_ids
            nullable: true
            schema:
              type: array
              items:
                type: integer
              description: |
                List of group IDs corresponding to which groups should be
                able to view the analyses. Defaults to all of requesting user's
                groups.
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        start_date = self.get_query_argument('startDate')
        end_date = self.get_query_argument('endDate')
        localization_dateobs = self.get_query_argument('localizationDateobs')
        localization_name = self.get_query_argument('localizationName', None)
        localization_cumprob = self.get_query_argument("localizationCumprob", 0.95)

        number_of_injections = int(self.get_query_argument("numberInjections", 1000))
        number_of_detections = int(self.get_query_argument("numberDetections", 1))
        detection_threshold = float(self.get_query_argument("detectionThreshold", 5))
        minimum_phase = float(self.get_query_argument("minimumPhase", 0))
        maximum_phase = float(self.get_query_argument("maximumPhase", 3))
        model_name = self.get_query_argument("modelName", "kilonova")
        optional_injection_parameters = json.loads(
            self.get_query_argument("optionalInjectionParameters", '{}')
        )

        if model_name not in ["kilonova", "afterglow", "linear"]:
            return self.error(
                f"{model_name} must be one of kilonova, afterglow or linear"
            )

        optional_injection_parameters = get_simsurvey_parameters(
            model_name, optional_injection_parameters
        )

        group_ids = self.get_query_argument('group_ids', None)

        with self.Session() as session:

            if not group_ids:
                group_ids = [
                    g.id for g in self.associated_user_object.accessible_groups
                ]

            try:
                stmt = Group.select(self.current_user).where(Group.id.in_(group_ids))
                groups = session.scalars(stmt).all()
            except AccessError:
                return self.error('Could not find any accessible groups.', status=403)

            if start_date is None:
                return self.error(message="Missing start_date")

            if end_date is None:
                return self.error(message="Missing end_date")

            if localization_dateobs is None:
                return self.error(message="Missing required localizationDateobs")

            start_date = arrow.get(start_date.strip()).datetime
            end_date = arrow.get(end_date.strip()).datetime

            instrument = session.scalars(
                Instrument.select(
                    self.current_user,
                    options=[
                        joinedload(Instrument.telescope),
                    ],
                ).where(
                    Instrument.id == instrument_id,
                )
            ).first()
            if instrument is None:
                return self.error(message=f"Invalid instrument ID {instrument_id}")

            if instrument.sensitivity_data is None:
                return self.error('Need sensitivity_data to evaluate efficiency')

            if localization_name is None:
                localization = session.scalars(
                    Localization.select(
                        self.current_user,
                    )
                    .where(Localization.dateobs == localization_dateobs)
                    .order_by(Localization.created_at.desc())
                ).first()
            else:
                localization = session.scalars(
                    Localization.select(
                        self.current_user,
                    )
                    .where(Localization.dateobs == localization_dateobs)
                    .where(Localization.localization_name == localization_name)
                ).first()

            event = session.scalars(
                GcnEvent.select(
                    self.current_user,
                ).where(GcnEvent.dateobs == localization_dateobs)
            ).first()
            if event is None:
                return self.error("GCN event not found")

            payload = {
                'start_date': Time(start_date).isot,
                'end_date': Time(end_date).isot,
                'telescope_name': instrument.telescope.name,
                'instrument_name': instrument.name,
                'localization_dateobs': localization_dateobs,
                'localization_name': localization_name,
                'localization_cumprob': localization_cumprob,
                'number_of_injections': number_of_injections,
                'number_of_detections': number_of_detections,
                'detection_threshold': detection_threshold,
                'minimum_phase': minimum_phase,
                'maximum_phase': maximum_phase,
                'model_name': model_name,
                'optional_injection_parameters': optional_injection_parameters,
            }

            survey_efficiency_analysis = SurveyEfficiencyForObservations(
                requester_id=self.associated_user_object.id,
                instrument_id=instrument_id,
                gcnevent_id=event.id,
                localization_id=localization.id,
                groups=groups,
                payload=payload,
                status='running',
            )

            session.add(survey_efficiency_analysis)
            session.commit()

            self.push_notification(
                'Simsurvey analysis in progress. Should be available soon.'
            )

            simsurvey_analysis = functools.partial(
                retrieve_observations_and_simsurvey,
                session,
                start_date,
                end_date,
                localization.id,
                instrument.id,
                survey_efficiency_analysis.id,
                "SurveyEfficiencyForObservations",
            )
            IOLoop.current().run_in_executor(None, simsurvey_analysis)

            return self.success(data={"id": survey_efficiency_analysis.id})


class ObservationSimSurveyPlotHandler(BaseHandler):
    @auth_or_token
    async def get(self, survey_efficiency_analysis_id):
        """
        ---
        description: Create a summary plot for a simsurvey efficiency calculation.
        tags:
          - survey_efficiency_for_observations
        parameters:
          - in: path
            name: survey_efficiency_analysis_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        survey_efficiency_analysis = (
            SurveyEfficiencyForObservations.get_if_accessible_by(
                survey_efficiency_analysis_id, self.current_user
            )
        )

        if survey_efficiency_analysis is None:
            return self.error(
                f'Missing survey_efficiency_analysis for id {survey_efficiency_analysis_id}'
            )

        if survey_efficiency_analysis.lightcurves is None:
            return self.error(
                f'survey_efficiency_analysis for id {survey_efficiency_analysis_id} not complete'
            )

        output_format = 'pdf'
        simsurvey_analysis = functools.partial(
            observation_simsurvey_plot,
            lcs=json.loads(survey_efficiency_analysis.lightcurves),
            output_format=output_format,
        )

        self.push_notification(
            'Simsurvey analysis in progress. Should be available soon.'
        )
        rez = await IOLoop.current().run_in_executor(None, simsurvey_analysis)

        filename = rez["name"]
        data = io.BytesIO(rez["data"])

        await self.send_file(data, filename, output_type=output_format)
