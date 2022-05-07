from baselayer.app.access import permissions, auth_or_token
from baselayer.log import make_log
import arrow
import astropy
import healpix_alchemy as ha
import humanize
from marshmallow.exceptions import ValidationError
import numpy as np
import pandas as pd
from regions import Regions
import requests
import sqlalchemy as sa
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import sessionmaker, scoped_session
from tornado.ioloop import IOLoop
import urllib
from astropy.time import Time
from io import StringIO

from baselayer.app.flow import Flow
from baselayer.app.env import load_env
from ..base import BaseHandler
from ...models import (
    DBSession,
    Allocation,
    GcnEvent,
    Localization,
    LocalizationTile,
    Telescope,
    Instrument,
    InstrumentField,
    InstrumentFieldTile,
    ExecutedObservation,
    QueuedObservation,
)

from ...models.schema import ObservationExternalAPIHandlerPost
from .instrument import add_tiles

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
    user,
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
    f"""Query
    Parameters
    ----------
    user : baselayer.app.models.User
        The user requesting the observations
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
        options = (
            [
                joinedload(Observation.instrument).joinedload(Instrument.telescope),
                joinedload(Observation.field).undefer(InstrumentField.contour_summary),
            ],
        )
    else:
        options = (
            [
                joinedload(Observation.instrument).joinedload(Instrument.telescope),
                joinedload(Observation.field),
            ],
        )

    obs_query = Observation.query_records_accessible_by(
        user,
        mode="read",
        options=options,
    )

    obs_query = obs_query.filter(Observation.obstime >= start_date)
    obs_query = obs_query.filter(Observation.obstime <= end_date)

    # optional: slice by Instrument
    if telescope_name is not None and instrument_name is not None:
        telescope = (
            Telescope.query_records_accessible_by(
                user,
            )
            .filter(
                Telescope.name == telescope_name,
            )
            .first()
        )
        if telescope is None:
            raise ValueError(f"Missing telescope {telescope_name}")

        instrument = (
            Instrument.query_records_accessible_by(
                user,
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
            return ValueError(f"Missing instrument {instrument_name}")

        obs_query = obs_query.filter(Observation.instrument_id == instrument.id)

    # optional: slice by GcnEvent localization
    if localization_dateobs is not None:
        if localization_name is not None:
            localization = (
                Localization.query_records_accessible_by(user)
                .filter(
                    Localization.dateobs == localization_dateobs,
                    Localization.localization_name == localization_name,
                )
                .first()
            )
            if localization is None:
                raise ValueError("Localization not found")
        else:
            event = (
                GcnEvent.query_records_accessible_by(
                    user,
                    options=[
                        joinedload(GcnEvent.localizations),
                    ],
                )
                .filter(GcnEvent.dateobs == localization_dateobs)
                .first()
            )
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
                    .subquery()
                )

            area = sa.func.sum(union.columns.healpix.area)
            prob = sa.func.sum(
                LocalizationTile.probdensity
                * (union.columns.healpix * LocalizationTile.healpix).area
            )
            query_area = sa.select(area).filter(
                LocalizationTile.localization_id == localization.id,
                union.columns.healpix.overlaps(LocalizationTile.healpix),
            )
            query_prob = sa.select(prob).filter(
                LocalizationTile.localization_id == localization.id,
                union.columns.healpix.overlaps(LocalizationTile.healpix),
            )
            intprob = DBSession().execute(query_prob).scalar_one()
            intarea = DBSession().execute(query_area).scalar_one()

            if intprob is None:
                intprob = 0.0
            if intarea is None:
                intarea = 0.0

    total_matches = obs_query.count()
    if n_per_page is not None:
        obs_query = obs_query.limit(n_per_page).offset((page_number - 1) * n_per_page)
    observations = obs_query.all()

    data = {
        "observations": [o.to_dict() for o in observations],
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
    def get(self):
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

        data = get_observations(
            self.current_user,
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
    def get(self, instrument_id):
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

        data = get_observations(
            self.current_user,
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

        event = (
            GcnEvent.query_records_accessible_by(
                self.current_user,
            )
            .filter(GcnEvent.dateobs == localization_dateobs)
            .first()
        )
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
                'Cannot submit executed observation plan requests to this Instrument.'
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

        start_date = self.get_query_argument('startDate')
        end_date = self.get_query_argument('endDate')

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
                'Cannot submit executed observation plan requests to this Instrument.'
            )

        try:
            # we now retrieve and commit to the database the
            # executed observations
            queue_names = instrument.api_class_obsplan.queued(
                allocation, data['start_date'], data['end_date']
            )
            self.push_notification(
                'Planned observation ingestion in progress. Should be available soon.'
            )
            return self.success(data={'queue_names': queue_names})
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

        data = get_observations(
            self.current_user,
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
            return self.error('Need at least one observation to send to Treasure Map')

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
        payload = {"graceid": graceid, "api_token": api_token}

        pointings = []
        for obs in observations:
            pointing = {}
            pointing["ra"] = obs["field"].ra
            pointing["dec"] = obs["field"].dec
            pointing["band"] = obs["filt"]
            pointing["instrumentid"] = 47  # str(instrument.treasuremap_id)
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
