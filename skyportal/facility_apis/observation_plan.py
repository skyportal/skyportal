from astropy.time import Time
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

default_filters = cfg.get('app.observation_plan.default_filters', ['g', 'r', 'i'])


def generate_plan(observation_plan_id, request_id, user_id):
    """Use gwemopt to construct observing plan."""

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
        ObservationPlanRequest,
        InstrumentField,
        PlannedObservation,
        User,
    )

    session = Session()
    # try:
    if True:
        plan = session.query(EventObservationPlan).get(observation_plan_id)
        request = session.query(ObservationPlanRequest).get(request_id)
        user = session.query(User).get(user_id)

        event_time = Time(request.gcnevent.dateobs, format='datetime', scale='utc')
        start_time = Time(request.payload["start_date"], format='iso', scale='utc')
        end_time = Time(request.payload["end_date"], format='iso', scale='utc')

        params = {
            'config': {
                request.instrument.name: {
                    # field list from skyportal
                    'tesselation': request.instrument.fields,
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
                },
            },
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
            'telescopes': [request.instrument.name],
            # minimum difference between observations of the same field
            'mindiff': request.payload["minimum_time_difference"],
            # maximum airmass with which to observae
            'airmass': request.payload["maximum_airmass"],
            # array of exposure times (same length as filter array)
            'exposuretimes': np.array(
                [int(request.payload["exposure_time"])]
                * len(request.payload["filters"].split(","))
            ),
        }

        if request.payload["schedule_strategy"] == "catalog":
            params = {
                **params,
                'tilesType': 'galaxy',
                'galaxy_catalog': 'CLU_mini',
                'galaxy_grade': 'S',
                'writeCatalog': False,
                'catalog_n': 1.0,
                'powerlaw_dist_exp': 1.0,
            }
        elif request.payload["schedule_strategy"] == "tiling":
            params = {**params, 'tilesType': 'moc'}
        else:
            raise AttributeError('scheduling_strategy should be tiling or catalog')

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
            galaxies = query.all()
            catalog_struct = {}
            catalog_struct["ra"] = np.array([g.ra for g in galaxies])
            catalog_struct["dec"] = np.array([g.dec for g in galaxies])
            catalog_struct["S"] = np.array([1.0 for g in galaxies])
            catalog_struct["Sloc"] = np.array([1.0 for g in galaxies])
            catalog_struct["Smass"] = np.array([1.0 for g in galaxies])

        if params["tilesType"] == "moc":
            moc_structs = gwemopt.skyportal.create_moc_from_skyportal(
                params, map_struct=map_struct
            )
            tile_structs = gwemopt.tiles.moc(params, map_struct, moc_structs)
        elif params["tilesType"] == "galaxy":
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
            regions = Regions.parse(request.instrument.region, format='ds9')
            data = {
                'RA': coverage_struct["data"][:, 0],
                'Dec': coverage_struct["data"][:, 1],
            }
            field_data = pd.DataFrame.from_dict(data)
            field_ids = add_tiles(
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

            overhead_per_exposure = params["config"][request.instrument.name][
                "overhead_per_exposure"
            ]

            exposure_time, prob = data[4], data[6]
            if params["tilesType"] == "galaxy":
                field_id = field_ids[ii]
            else:
                field_id = data[5]

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
        plan.status = 'complete'
        session.merge(plan)
        session.commit()

        request.status = 'complete'
        session.merge(request)
        session.commit()

        flow = Flow()
        flow.push(
            '*',
            "skyportal/REFRESH_GCNEVENT",
            payload={"gcnEvent_dateobs": request.gcnevent.dateobs},
        )

        return log(f"Generated plan for observation plan {observation_plan_id}")

    # except Exception as e:
    #    return log(
    #        f"Unable to generate plan for observation plan {observation_plan_id}: {e}"
    #    )
    # finally:
    #    Session.remove()


class MMAAPI(FollowUpAPI):

    """An interface to MMA operations."""

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
            IOLoop.current().run_in_executor(
                None, lambda: generate_plan(plan.id, request.id, request.requester.id)
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

        observation_plan = req.observation_plans[0]
        DBSession().delete(observation_plan)

        DBSession().delete(req)
        DBSession().commit()

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
                "enum": ["tiling", "catalog"],
                "default": "tiling",
            },
            "exposure_time": {"type": "string", "default": "300"},
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

    ui_json_schema = {}
