from astropy.time import Time
import healpix_alchemy as ha
import humanize
import pandas as pd
from regions import Regions
from datetime import datetime, timedelta
import numpy as np

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.orm import joinedload

from baselayer.log import make_log
from baselayer.app.flow import Flow
from baselayer.app.env import load_env

from . import FollowUpAPI

log = make_log('api/observation_plan')

env, cfg = load_env()

default_filters = cfg['app.observation_plan.default_filters']


def generate_observation_plan_statistics(
    observation_plan_ids, request_ids, user_id, session, cumulative_probability=1.0
):

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

        # Calculate area: Integrated area in sq. deg within localization
        cum_prob = (
            sa.func.sum(LocalizationTile.probdensity * LocalizationTile.healpix.area)
            .over(order_by=LocalizationTile.probdensity.desc())
            .label('cum_prob')
        )
        localizationtile_subquery = (
            sa.select(LocalizationTile.probdensity, cum_prob)
            .where(
                LocalizationTile.localization_id == request.localization_id,
            )
            .distinct()
        ).subquery()

        min_probdensity = (
            sa.select(sa.func.min(localizationtile_subquery.columns.probdensity)).where(
                localizationtile_subquery.columns.cum_prob <= cumulative_probability
            )
        ).scalar_subquery()

        tiles_subquery = (
            sa.select(InstrumentFieldTile.id)
            .where(
                LocalizationTile.localization_id == request.localization_id,
                LocalizationTile.probdensity >= min_probdensity,
                InstrumentFieldTile.instrument_id == plan.instrument_id,
                InstrumentFieldTile.instrument_field_id == InstrumentField.id,
                InstrumentFieldTile.instrument_field_id == PlannedObservation.field_id,
                PlannedObservation.observation_plan_id == plan.id,
                InstrumentFieldTile.healpix.overlaps(LocalizationTile.healpix),
            )
            .distinct()
            .subquery()
        )

        union = sa.select(ha.func.union(InstrumentFieldTile.healpix).label('healpix'))
        union = union.join(
            tiles_subquery, tiles_subquery.c.id == InstrumentFieldTile.id
        )
        area = sa.func.sum(union.columns.healpix.area)
        query_area = sa.select(area)
        intarea = session.execute(query_area).scalar_one()

        if intarea is None:
            intarea = 0.0

        statistics['area'] = intarea * (180.0 / np.pi) ** 2

        prob = sa.func.sum(
            LocalizationTile.probdensity
            * (union.columns.healpix * LocalizationTile.healpix).area
        )
        query_prob = sa.select(prob)
        intprob = session.execute(query_prob).scalar_one()
        if intprob is None:
            intprob = 0.0

        statistics['probability'] = intprob

        plan_statistics = EventObservationPlanStatistics(
            observation_plan_id=observation_plan_id,
            localization_id=request.localization_id,
            statistics=statistics,
        )
        session.add(plan_statistics)
        session.commit()


def generate_plan(observation_plan_ids, request_ids, user_id):
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
        plan.status = 'complete'
        session.merge(plan)
    session.commit()

    for request in requests:
        request.status = 'complete'
        session.merge(request)
    session.commit()

    generate_observation_plan_statistics(
        observation_plan_ids, request_ids, user_id, session
    )

    flow = Flow()
    flow.push(
        '*',
        "skyportal/REFRESH_GCNEVENT",
        payload={"gcnEvent_dateobs": request.gcnevent.dateobs},
    )


class MMAAPI(FollowUpAPI):

    """An interface to MMA operations."""

    # subclasses *must* implement the method below
    @staticmethod
    def submit_multiple(requests):

        """Generate multiple observation plans.

        Parameters
        ----------
        requests: skyportal.models.ObservationPlanRequest
            The list of requests to generate the observation plan.
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
                    "skyportal/REFRESH_GCNEVENT",
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
        IOLoop.current().run_in_executor(
            None, lambda: generate_plan(plan_ids, request_ids, requester_id)
        )

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request):

        """Generate an observation plan.

        Parameters
        ----------
        request: skyportal.models.ObservationPlanRequest
            The request to generate the observation plan.
        """

        from tornado.ioloop import IOLoop
        from ..models import DBSession, EventObservationPlan

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
                raise ValueError('filter_strategy must be either block or integrated')

            start_time = Time(request.payload["start_date"], format='iso', scale='utc')
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
                "skyportal/REFRESH_GCNEVENT",
                payload={"gcnEvent_dateobs": request.gcnevent.dateobs},
            )

            log(f"Generating schedule for observation plan {plan.id}")
            requester_id = request.requester.id
            IOLoop.current().run_in_executor(
                None, lambda: generate_plan([plan.id], [request.id], requester_id)
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
                    "default": f"ToO_{str(datetime.utcnow()).replace(' ','T')}",
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

    ui_json_schema = {}
