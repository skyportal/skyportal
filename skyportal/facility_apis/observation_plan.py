import time
from astropy.time import Time
import healpix_alchemy as ha
import humanize
import json
import pandas as pd
from regions import Regions
from datetime import datetime, timedelta
import numpy as np
import os
from requests import Request, Session
from skyportal.utils import http
import paramiko
from paramiko import SSHClient
from scp import SCPClient
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.orm import joinedload
import tempfile

from baselayer.log import make_log
from baselayer.app.flow import Flow
from baselayer.app.env import load_env

from . import FollowUpAPI

log = make_log('api/observation_plan')

env, cfg = load_env()

default_filters = cfg['app.observation_plan.default_filters']


def combine_healpix_tuples(input_tiles):
    """
    Combine (adjacent?) healpix tiles, given as tuples of (lower,upper).
    Returns a list of tuples that do not overlap.
    """

    # set upper bound to make sure this algorithm isn't crazy expensive
    for i in range(100000):

        input_tiles.sort()
        # check each tuple against all other tuples:
        for j1, t1 in enumerate(input_tiles):
            for j2 in range(j1 + 1, len(input_tiles)):
                t2 = input_tiles[j2]
                # check if overlapping with any of the combined tiles
                if t2[0] < t1[1] and t1[0] < t2[1]:
                    # if overlapping, grow to the union of both tiles
                    input_tiles[j1] = (min(t1[0], t2[0]), max(t1[1], t2[1]))
                    input_tiles[j2] = input_tiles[j1]  # grow both tiles in the list!
                else:
                    # if not overlapping, no need to scan next tiles,
                    # since they are sorted by lower bound
                    break
        output_tiles = list(set(input_tiles))  # remove duplicates

        # when none of the tiles are overlapping,
        # none will be removed by the actions of the loop
        if len(output_tiles) == len(input_tiles):
            return output_tiles

        input_tiles = output_tiles

    raise RuntimeError("Too many iterations (1000) to combine_healpix_tuples!")


def generate_observation_plan_statistics(
    observation_plan_ids,
    request_ids,
    session,
    stats_method='python',
    stats_logging=False,
):
    """
    Generate statistics for a list of observation plan IDs.
    The statistics are posted to the database as an
    EventObservationPlanStatistics object.

    Parameters
    ----------
    observation_plan_ids: list of int
        List of observation plan IDs to generate statistics for.
    request_ids: list of int
        List of request IDs to generate statistics for.
        Should be the same length as observation_plan_ids.
    session: sqlalchemy.orm.session.Session
        Database session.
    stats_method: str
        Method to use for computing statistics. Options are:
        - 'python': Use python to compute statistics (default)
        - 'db': Use database/postgres queries to compute statistics
    stats_logging: bool
        Whether to log statistics computation time.

    """

    from ..models import (
        EventObservationPlan,
        EventObservationPlanStatistics,
        GcnEvent,
        InstrumentField,
        InstrumentFieldTile,
        LocalizationTile,
        PlannedObservation,
        ObservationPlanRequest,
    )

    if stats_method == 'db':
        session.execute('ANALYZE')  # do we need this?

    for observation_plan_id, request_id in zip(observation_plan_ids, request_ids):
        plan = session.query(EventObservationPlan).get(observation_plan_id)
        request = session.query(ObservationPlanRequest).get(request_id)
        event = session.query(GcnEvent).get(request.gcnevent_id)

        statistics = {}

        # Calculate start_observation: time of the first planned observation
        if plan.planned_observations:
            statistics['start_observation'] = min(
                planned_observation.obstime
                for planned_observation in plan.planned_observations
            )
            statistics['dt'] = humanize.naturaldelta(
                statistics['start_observation'] - event.dateobs
            )
            statistics['start_observation'] = Time(
                statistics['start_observation'], format='datetime'
            ).isot

        else:
            statistics['start_observation'] = None

        # Calculate unique_filters: List of filters used in the observations
        if plan.planned_observations:
            statistics['unique_filters'] = list(
                {
                    planned_observation.filt
                    for planned_observation in plan.planned_observations
                }
            )
        else:
            statistics['unique_filters'] = None

        # Calculate num_observations: Number of planned observations
        statistics['num_observations'] = len(plan.planned_observations)

        # Calculate total_time: Total observation time (seconds)
        statistics['total_time'] = sum(
            obs.exposure_time for obs in plan.planned_observations
        )

        # Calculate tot_time_with_overheads: Total observation time including overheads (seconds)
        statistics['tot_time_with_overheads'] = (
            sum(obs.overhead_per_exposure for obs in plan.planned_observations)
            + statistics['total_time']
        )

        # get the localization tiles as python objects
        if stats_method == 'python':

            t0 = time.time()
            localization_tiles = session.scalars(
                sa.select(LocalizationTile)
                .where(LocalizationTile.localization_id == request.localization_id)
                .order_by(LocalizationTile.probdensity.desc())
                .distinct()
            ).all()
            if stats_logging:
                log(
                    "STATS: ",
                    f"{len(localization_tiles)} localization tiles in localization "
                    f"{request.localization_id} retrieved in {time.time() - t0:.2f}s. ",
                )

            # get the instrument field tiles as python objects
            t0 = time.time()
            instrument_field_tiles = session.scalars(
                sa.select(InstrumentFieldTile)
                .where(
                    InstrumentField.instrument_id == plan.instrument_id,
                    InstrumentFieldTile.instrument_field_id == InstrumentField.id,
                    InstrumentFieldTile.instrument_field_id
                    == PlannedObservation.field_id,
                    PlannedObservation.observation_plan_id == plan.id,
                )
                .distinct()
            ).all()
            if stats_logging:
                log(
                    f"STATS: {len(instrument_field_tiles)} instrument "
                    f"fields retrieved in {time.time() - t0:.2f}s. "
                )

            # calculate the area and integrated probability directly:
            t0 = time.time()
            intarea = 0  # total area covered by instrument field tiles
            intprob = 0  # total probability covered by instrument field tiles
            field_lower_bounds = np.array(
                [f.healpix.lower for f in instrument_field_tiles]
            )
            field_upper_bounds = np.array(
                [f.healpix.upper for f in instrument_field_tiles]
            )

            for i, t in enumerate(localization_tiles):
                # has True values where tile t has any overlap with one of the fields
                overlap_array = np.logical_and(
                    t.healpix.lower <= field_upper_bounds,
                    t.healpix.upper >= field_lower_bounds,
                )

                # only add area/prob if there's any overlap
                overlap = 0
                if np.any(overlap_array):
                    lower_upper = zip(
                        field_lower_bounds[overlap_array],
                        field_upper_bounds[overlap_array],
                    )
                    # tuples of (lower, upper) for all fields that overlap with tile t
                    new_fields = [(l, u) for (l, u) in lower_upper]

                    # combine any overlapping fields
                    output_fields = combine_healpix_tuples(new_fields)

                    # get the area of the combined fields that overlaps with tile t
                    for lower, upper in output_fields:
                        mx = np.minimum(t.healpix.upper, upper)
                        mn = np.maximum(t.healpix.lower, lower)
                        overlap += mx - mn

                intarea += overlap
                intprob += t.probdensity * overlap

            intarea *= ha.constants.PIXEL_AREA
            intprob *= ha.constants.PIXEL_AREA

            if stats_logging:
                log(
                    "STATS: ",
                    f'intarea= {intarea * (180 / np.pi) ** 2}, '
                    f'intprob= {intprob}. '
                    f'Runtime= {time.time() - t0:.2f}s. ',
                )

            statistics['area'] = intarea * (180 / np.pi) ** 2
            statistics['probability'] = intprob

        # This code below uses database queries to
        # calculate the stats, instead of python loops over the tiles.
        # It is still too slow at scale, but hopefully we can figure
        # out why and replace the code above with this block at some point.
        elif stats_method == 'db':

            t0 = time.time()
            union = (
                sa.select(ha.func.union(InstrumentFieldTile.healpix).label('healpix'))
                .filter(
                    InstrumentFieldTile.instrument_field_id
                    == PlannedObservation.field_id,
                    PlannedObservation.observation_plan_id == plan.id,
                )
                .subquery()
            )

            area = sa.func.sum(union.columns.healpix.area)
            query_area = sa.select(area)
            intarea = session.execute(query_area).scalar_one()

            if intarea is None:
                intarea = 0.0
            intarea *= (180.0 / np.pi) ** 2
            if stats_logging:
                log(f'STATS: area= {intarea}. Runtime= {time.time() - t0:.2f}s. ')

            prob = sa.func.sum(
                LocalizationTile.probdensity
                * (union.columns.healpix * LocalizationTile.healpix).area
            )

            query_prob = sa.select(prob).filter(
                LocalizationTile.localization_id == request.localization_id,
                union.columns.healpix.overlaps(LocalizationTile.healpix),
            )

            intprob = session.execute(query_prob).scalar_one()
            if intprob is None:
                intprob = 0.0

            if stats_logging:
                log(f'STATS: prob= {intprob}. Runtime= {time.time() - t0:.2f}s. ')
        else:
            raise ValueError(f"Unknown stats_method: {stats_method}")

        plan_statistics = EventObservationPlanStatistics(
            observation_plan_id=observation_plan_id,
            localization_id=request.localization_id,
            statistics=statistics,
        )
        session.add(plan_statistics)
        session.commit()


def generate_plan(
    observation_plan_ids,
    request_ids,
    user_id,
    stats_method='python',
    stats_logging=False,
):
    """Use gwemopt to construct multiple observing plans."""

    from ..models import DBSession
    from skyportal.handlers.api.instrument import add_tiles

    Session = scoped_session(sessionmaker(bind=DBSession.session_factory.kw["bind"]))

    import gwemopt
    import gwemopt.utils
    import gwemopt.segments
    import gwemopt.skyportal

    from ..models import (
        EventObservationPlan,
        Galaxy,
        InstrumentField,
        LocalizationTile,
        ObservationPlanRequest,
        PlannedObservation,
        User,
    )

    plans, requests = [], []

    session = Session()
    for observation_plan_id, request_id in zip(observation_plan_ids, request_ids):
        plan = session.query(EventObservationPlan).get(observation_plan_id)
        request = session.query(ObservationPlanRequest).get(request_id)

        plans.append(plan)
        requests.append(request)

    user = session.query(User).get(user_id)

    event_time = Time(requests[0].gcnevent.dateobs, format='datetime', scale='utc')
    start_time = Time(requests[0].payload["start_date"], format='iso', scale='utc')
    end_time = Time(requests[0].payload["end_date"], format='iso', scale='utc')

    params = {
        # gwemopt filter strategy
        # options: block (blocks of single filters), integrated (series of alternating filters)
        'doAlternativeFilters': request.payload["filter_strategy"] == "block",
        # flag to indicate fields come from DB
        'doDatabase': True,
        # only keep tiles within powerlaw_cl
        'doMinimalTiling': True,
        # single set of scheduled observations
        'doSingleExposure': True,
        # gwemopt scheduling algorithms
        # options: greedy, greedy_slew, sear, airmass_weighted
        'scheduleType': request.payload["schedule_type"],
        # list of filters to use for observations
        'filters': request.payload["filters"].split(","),
        # GPS time for event
        'gpstime': event_time.gps,
        # Healpix nside for the skymap
        'nside': 512,
        # maximum integrated probability of the skymap to consider
        'powerlaw_cl': request.payload["integrated_probability"],
        'telescopes': [request.instrument.name for request in requests],
        # minimum difference between observations of the same field
        'mindiff': request.payload["minimum_time_difference"],
        # maximum airmass with which to observae
        'airmass': request.payload["maximum_airmass"],
        # array of exposure times (same length as filter array)
        'exposuretimes': np.array(
            [request.payload["exposure_time"]]
            * len(request.payload["filters"].split(","))
        ),
    }

    config = {}
    for request in requests:
        if "field_ids" in request.payload and len(request.payload["field_ids"]) > 0:
            fields = [
                f
                for f in request.instrument.fields
                if f.field_id in request.payload["field_ids"]
            ]
        else:
            fields = request.instrument.fields
        config[request.instrument.name] = {
            # field list from skyportal
            'tesselation': fields,
            # telescope longitude [deg]
            'longitude': request.instrument.telescope.lon,
            # telescope latitude [deg]
            'latitude': request.instrument.telescope.lat,
            # telescope elevation [m]
            'elevation': request.instrument.telescope.elevation,
            # telescope name
            'telescope': request.instrument.name,
            # telescope horizon
            'horizon': -12.0,
            # time in seconds to change the filter
            'filt_change_time': 0.0,
            # extra overhead in seconds
            'overhead_per_exposure': 0.0,
            # slew rate for the telescope [deg/s]
            'slew_rate': 2.6,
            # camera readout time
            'readout': 0.0,
            # telescope field of view
            'FOV': 0.0,
            # exposure time for the given limiting magnitude
            'exposuretime': 1.0,
            # limiting magnitude given telescope time
            'magnitude': 0.0,
        }
    params['config'] = config

    if request.payload["schedule_strategy"] == "galaxy":
        params = {
            **params,
            'tilesType': 'galaxy',
            'galaxy_catalog': request.payload["galaxy_catalog"],
            'galaxy_grade': 'S',
            'writeCatalog': False,
            'catalog_n': 1.0,
            'powerlaw_dist_exp': 1.0,
        }
    elif request.payload["schedule_strategy"] == "tiling":
        params = {**params, 'tilesType': 'moc'}
    else:
        raise AttributeError('scheduling_strategy should be tiling or galaxy')

    params = gwemopt.utils.params_checker(params)
    params = gwemopt.segments.get_telescope_segments(params)

    params["Tobs"] = [
        start_time.mjd - event_time.mjd,
        end_time.mjd - event_time.mjd,
    ]

    params['map_struct'] = dict(
        zip(['prob', 'distmu', 'distsigma', 'distnorm'], request.localization.flat)
    )

    params['is3D'] = request.localization.is_3d

    # Function to read maps
    map_struct = gwemopt.utils.read_skymap(
        params, is3D=params["do3D"], map_struct=params['map_struct']
    )

    if params["tilesType"] == "galaxy":
        query = Galaxy.query_records_accessible_by(user, mode="read")
        query = query.filter(Galaxy.catalog_name == params["galaxy_catalog"])

        cum_prob = (
            sa.func.sum(LocalizationTile.probdensity * LocalizationTile.healpix.area)
            .over(order_by=LocalizationTile.probdensity.desc())
            .label('cum_prob')
        )
        localizationtile_subquery = (
            sa.select(LocalizationTile.probdensity, cum_prob).filter(
                LocalizationTile.localization_id == request.localization.id
            )
        ).subquery()

        # convert to 0-1
        integrated_probability = request.payload["integrated_probability"] * 0.01
        min_probdensity = (
            sa.select(
                sa.func.min(localizationtile_subquery.columns.probdensity)
            ).filter(
                localizationtile_subquery.columns.cum_prob <= integrated_probability
            )
        ).scalar_subquery()

        tiles_subquery = (
            sa.select(Galaxy.id)
            .filter(
                LocalizationTile.localization_id == request.localization.id,
                LocalizationTile.healpix.contains(Galaxy.healpix),
                LocalizationTile.probdensity >= min_probdensity,
            )
            .subquery()
        )

        query = query.join(
            tiles_subquery,
            Galaxy.id == tiles_subquery.c.id,
        )

        galaxies = query.all()
        catalog_struct = {}
        catalog_struct["ra"] = np.array([g.ra for g in galaxies])
        catalog_struct["dec"] = np.array([g.dec for g in galaxies])

        if "galaxy_sorting" not in request.payload:
            galaxy_sorting = "equal"
        else:
            galaxy_sorting = request.payload["galaxy_sorting"]

        if galaxy_sorting == "equal":
            values = np.array([1.0 for g in galaxies])
        elif galaxy_sorting == "sfr_fuv":
            values = np.array([g.sfr_fuv for g in galaxies])
        elif galaxy_sorting == "mstar":
            values = np.array([g.mstar for g in galaxies])
        elif galaxy_sorting == "magb":
            values = np.array([g.magb for g in galaxies])
        elif galaxy_sorting == "magk":
            values = np.array([g.magk for g in galaxies])

        idx = np.where(values != None)[0]  # noqa: E711

        if len(idx) == 0:
            raise ValueError('No galaxies available for scheduling.')

        values = values[idx]
        if galaxy_sorting in ["magb", "magk"]:
            # weigh brighter more heavily
            values = -values
            values = (values - np.min(values)) / (np.max(values) - np.min(values))

        catalog_struct["ra"] = catalog_struct["ra"][idx]
        catalog_struct["dec"] = catalog_struct["dec"][idx]
        catalog_struct["S"] = values
        catalog_struct["Sloc"] = values
        catalog_struct["Smass"] = values

    if params["tilesType"] == "moc":
        moc_structs = gwemopt.skyportal.create_moc_from_skyportal(
            params, map_struct=map_struct
        )
        tile_structs = gwemopt.tiles.moc(params, map_struct, moc_structs)
    elif params["tilesType"] == "galaxy":
        for request in requests:
            if request.instrument.region is None:
                raise ValueError(
                    'Must define the instrument region in the case of galaxy requests'
                )
            regions = Regions.parse(request.instrument.region, format='ds9')
            tile_structs = gwemopt.skyportal.create_galaxy_from_skyportal(
                params, map_struct, catalog_struct, regions=regions
            )

    tile_structs, coverage_struct = gwemopt.coverage.timeallocation(
        params, map_struct, tile_structs
    )

    # if the fields do not yet exist, we need to add them
    if params["tilesType"] == "galaxy":
        field_ids = np.array([-1] * len(coverage_struct["data"]))
        for request in requests:
            regions = Regions.parse(request.instrument.region, format='ds9')
            idx = np.where(coverage_struct["telescope"] == request.instrument.name)[0]
            data = {
                'RA': coverage_struct["data"][idx, 0],
                'Dec': coverage_struct["data"][idx, 1],
            }
            field_data = pd.DataFrame.from_dict(data)
            idx = np.array(idx).astype(int)
            field_ids[idx] = add_tiles(
                request.instrument.id,
                request.instrument.name,
                regions,
                field_data,
                session=session,
            )

    planned_observations = []
    for ii in range(len(coverage_struct["ipix"])):
        data = coverage_struct["data"][ii, :]
        filt = coverage_struct["filters"][ii]
        mjd = data[2]
        tt = Time(mjd, format='mjd')
        instrument_name = coverage_struct["telescope"][ii]

        overhead_per_exposure = params["config"][instrument_name][
            "overhead_per_exposure"
        ]

        exposure_time, prob = data[4], data[6]
        if params["tilesType"] == "galaxy":
            field_id = int(field_ids[ii])
        else:
            field_id = data[5]

        for plan, request in zip(plans, requests):
            if request.instrument.name == instrument_name:
                break
        field = InstrumentField.query.filter(
            InstrumentField.instrument_id == request.instrument.id,
            InstrumentField.field_id == field_id,
        ).first()
        if field is None:
            return log(f"Missing field {field_id} from list")

        planned_observation = PlannedObservation(
            obstime=tt.datetime,
            dateobs=request.gcnevent.dateobs,
            field_id=field.id,
            exposure_time=exposure_time,
            weight=prob,
            filt=filt,
            instrument_id=request.instrument.id,
            planned_observation_id=ii,
            observation_plan_id=plan.id,
            overhead_per_exposure=overhead_per_exposure,
        )
        planned_observations.append(planned_observation)

    session.add_all(planned_observations)
    for plan in plans:
        setattr(plan, 'status', 'complete')
        session.merge(plan)

    for request in requests:
        setattr(request, 'status', 'complete')
        session.merge(request)
    session.commit()

    generate_observation_plan_statistics(observation_plan_ids, request_ids, session)

    flow = Flow()
    flow.push(
        '*',
        "skyportal/REFRESH_GCN_EVENT",
        payload={"gcnEvent_dateobs": request.gcnevent.dateobs},
    )


class GenericRequest:

    """A dictionary structure for ToO requests."""

    def _build_observation_plan_payload(self, request):
        """Payload json for observation plan queue requests.

        Parameters
        ----------

        request: skyportal.models.ObservationPlanRequest
            The request to add to the queue and the SkyPortal database.

        Returns
        ----------
        payload: json
            payload for requests.
        """

        start_mjd = Time(request.payload["start_date"], format='iso').mjd
        end_mjd = Time(request.payload["end_date"], format='iso').mjd

        json_data = {
            'queue_name': "ToO_" + request.payload["queue_name"],
            'validity_window_mjd': [start_mjd, end_mjd],
        }

        # One observation plan per request
        if not len(request.observation_plans) == 1:
            raise ValueError('Should be one observation plan for this request.')

        observation_plan = request.observation_plans[0]
        planned_observations = observation_plan.planned_observations

        if len(planned_observations) == 0:
            raise ValueError('Cannot submit observing plan with no observations.')

        targets = []
        cnt = 1
        for obs in planned_observations:
            target = {
                'request_id': cnt,
                'field_id': obs.field.field_id,
                'ra': obs.field.ra,
                'dec': obs.field.dec,
                'filter': obs.filt,
                'exposure_time': obs.exposure_time,
                'program_pi': request.requester.username,
            }
            targets.append(target)
            cnt = cnt + 1

        json_data['targets'] = targets

        return json_data


class MMAAPI(FollowUpAPI):
    """An interface to MMA operations."""

    # subclasses *must* implement the method below
    @staticmethod
    def submit_multiple(requests, asynchronous=True):

        """Generate multiple observation plans.

        Parameters
        ----------
        requests: skyportal.models.ObservationPlanRequest
            The list of requests to generate the observation plan.
        asynchronous : bool
            Create asynchronous request. Defaults to True.
        """

        from tornado.ioloop import IOLoop
        from ..models import DBSession, EventObservationPlan

        plan_ids, request_ids = [], []
        for request in requests:
            plan = EventObservationPlan.query.filter_by(
                plan_name=request.payload["queue_name"]
            ).first()
            if plan is None:

                # check payload
                required_parameters = {
                    'start_date',
                    'end_date',
                    'schedule_type',
                    'schedule_strategy',
                    'filter_strategy',
                    'exposure_time',
                    'filters',
                    'maximum_airmass',
                    'integrated_probability',
                    'minimum_time_difference',
                }

                if not required_parameters.issubset(set(request.payload.keys())):
                    raise ValueError('Missing required planning parameter')

                if request.payload["schedule_type"] not in [
                    "greedy",
                    "greedy_slew",
                    "sear",
                    "airmass_weighted",
                ]:
                    raise ValueError(
                        'schedule_type must be one of greedy, greedy_slew, sear, or airmass_weighted'
                    )

                if (
                    request.payload["integrated_probability"] < 0
                    or request.payload["integrated_probability"] > 100
                ):
                    raise ValueError('integrated_probability must be between 0 and 100')

                if request.payload["filter_strategy"] not in ["block", "integrated"]:
                    raise ValueError(
                        'filter_strategy must be either block or integrated'
                    )

                start_time = Time(
                    request.payload["start_date"], format='iso', scale='utc'
                )
                end_time = Time(request.payload["end_date"], format='iso', scale='utc')

                plan = EventObservationPlan(
                    observation_plan_request_id=request.id,
                    dateobs=request.gcnevent.dateobs,
                    plan_name=request.payload['queue_name'],
                    instrument_id=request.instrument.id,
                    validity_window_start=start_time.datetime,
                    validity_window_end=end_time.datetime,
                )

                DBSession().add(plan)
                DBSession().commit()

                request.status = 'running'
                DBSession().merge(request)
                DBSession().commit()

                flow = Flow()
                flow.push(
                    '*',
                    "skyportal/REFRESH_GCN_EVENT",
                    payload={"gcnEvent_dateobs": request.gcnevent.dateobs},
                )

                plan_ids.append(plan.id)
                request_ids.append(request.id)
            else:
                raise ValueError(
                    f'plan_name {request.payload["queue_name"]} already exists.'
                )

        log(f"Generating schedule for observation plan {plan.id}")
        requester_id = request.requester.id

        if asynchronous:
            IOLoop.current().run_in_executor(
                None,
                lambda: generate_plan(
                    observation_plan_ids=plan_ids,
                    request_ids=request_ids,
                    user_id=requester_id,
                    stats_method=request.payload.get('stats_method'),
                    stats_logging=request.payload.get('stats_logging'),
                ),
            )
        else:
            generate_plan(
                observation_plan_ids=plan_ids,
                request_ids=request_ids,
                user_id=requester_id,
                stats_method=request.payload.get('stats_method'),
                stats_logging=request.payload.get('stats_logging'),
            )

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request_id, asynchronous=True):

        """Generate an observation plan.

        Parameters
        ----------
        request_id : int
            The ID of the ObservationPlanRequest to generate the observation plan.
        asynchronous : bool
            Create asynchronous request. Defaults to True.
        """

        from tornado.ioloop import IOLoop
        from ..models import DBSession, EventObservationPlan, ObservationPlanRequest

        with DBSession() as session:
            request = session.scalar(
                sa.select(ObservationPlanRequest).where(
                    ObservationPlanRequest.id == request_id
                )
            )
            plan = session.scalars(
                sa.select(EventObservationPlan).where(
                    EventObservationPlan.plan_name == request.payload["queue_name"]
                )
            ).first()

            if plan is None:

                # check payload
                required_parameters = {
                    'start_date',
                    'end_date',
                    'schedule_type',
                    'schedule_strategy',
                    'filter_strategy',
                    'exposure_time',
                    'filters',
                    'maximum_airmass',
                    'integrated_probability',
                    'minimum_time_difference',
                }

                if not required_parameters.issubset(set(request.payload.keys())):
                    raise ValueError('Missing required planning parameter')

                if request.payload["schedule_type"] not in [
                    "greedy",
                    "greedy_slew",
                    "sear",
                    "airmass_weighted",
                ]:
                    raise ValueError(
                        'schedule_type must be one of greedy, greedy_slew, sear, or airmass_weighted'
                    )

                if (
                    request.payload["integrated_probability"] < 0
                    or request.payload["integrated_probability"] > 100
                ):
                    raise ValueError('integrated_probability must be between 0 and 100')

                if request.payload["filter_strategy"] not in ["block", "integrated"]:
                    raise ValueError(
                        'filter_strategy must be either block or integrated'
                    )

                start_time = Time(
                    request.payload["start_date"], format='iso', scale='utc'
                )
                end_time = Time(request.payload["end_date"], format='iso', scale='utc')

                plan = EventObservationPlan(
                    observation_plan_request_id=request.id,
                    dateobs=request.gcnevent.dateobs,
                    plan_name=request.payload['queue_name'],
                    instrument_id=request.instrument.id,
                    validity_window_start=start_time.datetime,
                    validity_window_end=end_time.datetime,
                )

                session.add(plan)
                session.commit()

                request.status = 'running'
                session.merge(request)
                session.commit()

                flow = Flow()
                flow.push(
                    '*',
                    "skyportal/REFRESH_GCN_EVENT",
                    payload={"gcnEvent_dateobs": request.gcnevent.dateobs},
                )

                flow.push(
                    '*',
                    "skyportal/REFRESH_OBSERVATION_PLAN_NAMES",
                )

                log(f"Generating schedule for observation plan {plan.id}")
                requester_id = request.requester.id

                if asynchronous:
                    IOLoop.current().run_in_executor(
                        # TODO: add stats_method and stats_logging to the arguments
                        None,
                        lambda: generate_plan(
                            observation_plan_ids=[plan.id],
                            request_ids=[request.id],
                            user_id=requester_id,
                            stats_method=request.payload.get('stats_method'),
                            stats_logging=request.payload.get('stats_logging'),
                        ),
                    )
                else:
                    generate_plan(
                        observation_plan_ids=[plan.id],
                        request_ids=[request.id],
                        user_id=requester_id,
                        stats_method=request.payload.get('stats_method'),
                        stats_logging=request.payload.get('stats_logging'),
                    )
            else:
                raise ValueError(
                    f'plan_name {request.payload["queue_name"]} already exists.'
                )

    @staticmethod
    def delete(request_id):
        """Delete an observation plan from list.

        Parameters
        ----------
        request_id: integer
            The id of the skyportal.models.ObservationPlanRequest to delete from the queue and the SkyPortal database.
        """

        from ..models import DBSession, ObservationPlanRequest

        req = (
            DBSession.execute(
                sa.select(ObservationPlanRequest)
                .filter(ObservationPlanRequest.id == request_id)
                .options(joinedload(ObservationPlanRequest.observation_plans))
            )
            .unique()
            .one()
        )
        req = req[0]

        if len(req.observation_plans) > 1:
            raise ValueError(
                'Should only be one observation plan associated to this request'
            )

        if len(req.observation_plans) > 0:
            observation_plan = req.observation_plans[0]
            DBSession().delete(observation_plan)

        DBSession().delete(req)
        DBSession().commit()

    def custom_json_schema(instrument, user):

        from ..models import DBSession, Galaxy

        galaxies = [g for g, in DBSession().query(Galaxy.catalog_name).distinct().all()]

        form_json_schema = {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "default": str(datetime.utcnow()),
                    "title": "Start Date (UT)",
                },
                "end_date": {
                    "type": "string",
                    "title": "End Date (UT)",
                    "default": str(datetime.utcnow() + timedelta(days=1)),
                },
                "filter_strategy": {
                    "type": "string",
                    "enum": ["block", "integrated"],
                    "default": "block",
                },
                "schedule_type": {
                    "type": "string",
                    "enum": ["greedy", "greedy_slew", "sear", "airmass_weighted"],
                    "default": "greedy_slew",
                },
                "schedule_strategy": {
                    "type": "string",
                    "enum": ["tiling", "galaxy"],
                    "default": "tiling",
                },
                "galaxy_catalog": {
                    "type": "string",
                    "enum": galaxies,
                    "default": galaxies[0] if len(galaxies) > 0 else "",
                },
                "galaxy_sorting": {
                    "type": "string",
                    "enum": ["equal", "sfr_fuv", "mstar", "magb", "magk"],
                    "default": "equal",
                },
                "exposure_time": {
                    "title": "Exposure Time [s]",
                    "type": "number",
                    "default": 300,
                    "minimum": 1,
                },
                "filters": {"type": "string", "default": ",".join(default_filters)},
                "maximum_airmass": {
                    "title": "Maximum Airmass (1-3)",
                    "type": "number",
                    "default": 2.0,
                    "minimum": 1,
                    "maximum": 3,
                },
                "integrated_probability": {
                    "title": "Integrated Probability (0-100)",
                    "type": "number",
                    "default": 90.0,
                    "minimum": 0,
                    "maximum": 100,
                },
                "minimum_time_difference": {
                    "title": "Minimum time difference [min] (0-180)",
                    "type": "number",
                    "default": 30.0,
                    "minimum": 0,
                    "maximum": 180,
                },
                "queue_name": {
                    "type": "string",
                    "default": f"ToO_{str(datetime.utcnow()).replace(' ', 'T')}",
                },
            },
            "required": [
                "start_date",
                "end_date",
                "filters",
                "queue_name",
                "filter_strategy",
                "schedule_type",
                "schedule_strategy",
                "exposure_time",
                "maximum_airmass",
                "integrated_probability",
                "minimum_time_difference",
            ],
        }

        return form_json_schema

    @staticmethod
    def send(request, session):

        """Submit an EventObservationPlan.

        Parameters
        ----------
        request : skyportal.models.ObservationPlanRequest
            The request to add to the queue and the SkyPortal database.
        """

        from ..models import FacilityTransaction

        altdata = request.allocation.altdata
        if not altdata:
            raise ValueError('Missing allocation information.')

        req = GenericRequest()
        requestgroup = req._build_observation_plan_payload(request)

        payload = {
            'targets': requestgroup["targets"],
            'queue_name': requestgroup["queue_name"],
            'validity_window_mjd': requestgroup["validity_window_mjd"],
            'queue_type': 'list',
            'user': request.requester.username,
        }

        if 'type' in altdata and altdata['type'] == 'scp':
            with tempfile.NamedTemporaryFile(mode='w') as f:
                json.dump(payload, f, indent=4, sort_keys=True)
                f.flush()

                ssh = SSHClient()
                ssh.load_system_host_keys()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    hostname=altdata['host'],
                    port=altdata['port'],
                    username=altdata['username'],
                    password=altdata['password'],
                )
                scp = SCPClient(ssh.get_transport())
                scp.put(
                    f.name,
                    os.path.join(altdata['directory'], payload["queue_name"] + '.json'),
                )
                scp.close()

                request.status = 'submitted'

                transaction = FacilityTransaction(
                    request=None,
                    response=None,
                    observation_plan_request=request,
                    initiator_id=request.last_modified_by_id,
                )

        else:
            headers = {"Authorization": f"token {altdata['access_token']}"}

            # default to API
            url = (
                altdata['protocol']
                + '://'
                + ('127.0.0.1' if 'localhost' in altdata['host'] else altdata['host'])
                + ':'
                + altdata['port']
                + '/api/obsplans'
            )
            s = Session()
            genericreq = Request('PUT', url, json=payload, headers=headers)
            prepped = genericreq.prepare()
            r = s.send(prepped)

            if r.status_code == 200:
                request.status = 'submitted to telescope queue'
            else:
                request.status = f'rejected from telescope queue: {r.content}'

            transaction = FacilityTransaction(
                request=http.serialize_requests_request(r.request),
                response=None,
                observation_plan_request=request,
                initiator_id=request.last_modified_by_id,
            )

        session.add(transaction)

    ui_json_schema = {}
