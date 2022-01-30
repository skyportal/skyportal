from astropy.time import Time
from datetime import datetime, timedelta
import numpy as np

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.orm import joinedload

import gwemopt.utils
import gwemopt.segments
import gwemopt.skyportal
from baselayer.log import make_log
from baselayer.app.flow import Flow

from . import FollowUpAPI
from ..models import DBSession

Session = scoped_session(sessionmaker(bind=DBSession.session_factory.kw["bind"]))

log = make_log('api/observation_plan')


def generate_plan(observation_plan_id, request_id):
    """Use gwemopt to construct observing plan."""

    from ..models import (
        EventObservationPlan,
        ObservationPlanRequest,
        InstrumentField,
        PlannedObservation,
    )

    session = Session()
    try:
        plan = session.query(EventObservationPlan).get(observation_plan_id)
        request = session.query(ObservationPlanRequest).get(request_id)

        event_time = Time(request.gcnevent.dateobs, format='datetime', scale='utc')
        start_time = Time(request.payload["start_date"], format='iso', scale='utc')
        end_time = Time(request.payload["end_date"], format='iso', scale='utc')

        params = {
            'config': {
                request.instrument.name: {
                    'tesselation': request.instrument.fields,
                    'longitude': request.instrument.telescope.lon,
                    'latitude': request.instrument.telescope.lat,
                    'elevation': request.instrument.telescope.elevation,
                    'telescope': request.instrument.name,
                    'horizon': -12.0,
                    # consider adding to instrument model?
                    'filt_change_time': 0.0,
                    'overhead_per_exposure': 0.0,
                    # does not change anything
                    'FOV': 0.0,
                    'exposuretime': 1.0,
                    'magnitude': 0.0,
                },
            },
            'doAlternativeFilters': request.payload["scheduling_type"] == "block",
            'doDatabase': True,
            'doMinimalTiling': True,
            'doSingleExposure': True,
            'filters': request.payload["filters"].split(","),
            'gpstime': event_time.gps,
            'nside': 512,
            'powerlaw_cl': request.payload["integrated_probability"],
            'telescopes': [request.instrument.name],
            'mindiff': request.payload["minimum_time_difference"],
            'airmass': request.payload["maximum_airmass"],
            'exposuretimes': np.array(
                [int(request.payload["exposure_time"])]
                * len(request.payload["filters"].split(","))
            ),
        }

        if request.payload["scheduling_strategy"] == "catalog":
            params = {
                **params,
                'tilesType': 'galaxy',
                'galaxy_catalog': 'CLU',
                'galaxy_grade': 'S',
                'writeCatalog': False,
                'catalog_n': 1.0,
                'powerlaw_dist_exp': 1.0,
            }
        elif request.payload["scheduling_strategy"] == "tiling":
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

        moc_structs = gwemopt.skyportal.create_moc_from_skyportal(
            params, map_struct=map_struct
        )
        tile_structs = gwemopt.tiles.moc(params, map_struct, moc_structs)

        tile_structs, coverage_struct = gwemopt.coverage.timeallocation(
            params, map_struct, tile_structs
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

            exposure_time, field_id, prob = data[4], data[5], data[6]

            field = InstrumentField.query.filter(
                InstrumentField.instrument_id == request.instrument.id,
                InstrumentField.id == field_id,
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
        session.merge(plan)
        session.commit()

        flow = Flow()
        flow.push(
            '*',
            "skyportal/REFRESH_GCNEVENT",
            payload={"gcnEvent_dateobs": request.gcnevent.dateobs},
        )

        return log(f"Generated plan for observation plan {observation_plan_id}")

    except Exception as e:
        return log(
            f"Unable to generate plan for observation plan {observation_plan_id}: {e}"
        )
    finally:
        Session.remove()


class MMAAPI(FollowUpAPI):

    """An interface to MMA operations."""

    # subclasses *must* implement the method below
    @staticmethod
    def submit(request):

        """Generate an observation plan.

        Parameters
        ----------
        request: skyportal.models.ObservationPlanRequest
            The request to generate the observation plan and the SkyPortal database.
        """

        from tornado.ioloop import IOLoop
        from ..models import DBSession, EventObservationPlan

        plan = EventObservationPlan.query.filter_by(
            plan_name=request.payload["queue_name"]
        ).first()
        if plan is None:
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
                None, lambda: generate_plan(plan.id, request.id)
            )
        else:
            raise ValueError(
                f'plan_name {request.payload["queue_name"]} already exists.'
            )

    @staticmethod
    def delete(request):
        """Delete an observation plan from list.

        Parameters
        ----------
        request: skyportal.models.ObservationPlanRequest
            The request to delete from the queue and the SkyPortal database.
        """

        from ..models import DBSession, ObservationPlanRequest

        req = (
            DBSession.execute(
                sa.select(ObservationPlanRequest)
                .filter(ObservationPlanRequest.id == request.id)
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
                "default": str(datetime.utcnow()).replace("T", ""),
                "title": "Start Date (UT)",
            },
            "end_date": {
                "type": "string",
                "title": "End Date (UT)",
                "default": str(datetime.utcnow() + timedelta(days=1)).replace("T", ""),
            },
            "program_id": {
                "type": "string",
                "enum": ["Partnership", "Caltech"],
                "default": "Partnership",
            },
            "subprogram_name": {
                "type": "string",
                "enum": ["GW", "GRB", "Neutrino", "SolarSystem", "Other"],
                "default": "GRB",
            },
            "scheduling_type": {
                "type": "string",
                "enum": ["block", "integrated"],
                "default": "block",
            },
            "scheduling_strategy": {
                "type": "string",
                "enum": ["tiling", "catalog"],
                "default": "tiling",
            },
            "exposure_time": {"type": "string", "default": "300"},
            "filters": {"type": "string", "default": "g,r,i"},
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
            "queue_name": {"type": "string", "default": f"ToO_{datetime.utcnow()}"},
        },
        "required": [
            "start_date",
            "end_date",
            "program_id",
            "filters",
            "queue_name",
            "subprogram_name",
            "scheduling_type",
            "scheduling_strategy",
            "exposure_time",
            "maximum_airmass",
            "integrated_probability",
            "minimum_time_difference",
        ],
    }

    ui_json_schema = {}
