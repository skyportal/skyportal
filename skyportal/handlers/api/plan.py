import datetime
import copy
from tornado.ioloop import IOLoop
import functools

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import joinedload
from astropy import time
import ephem
import gwemopt.utils
import gwemopt.skyportal
import gwemopt.gracedb
import gwemopt.rankedTilesGenerator
import gwemopt.waw
import gwemopt.lightcurve
import gwemopt.coverage
import gwemopt.efficiency
import gwemopt.tiles
import gwemopt.segments
import gwemopt.catalog
import numpy as np

from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from ...models import (
    DBSession,
    Instrument,
    InstrumentField,
    Localization,
    EventObservingPlan,
    PlannedObservation,
    Telescope,
)

plan_args_default = {
    'filt': ['g', 'r', 'g'],
    'exposuretimes': [300.0, 300.0, 300.0],
    'doReferences': False,
    'doUsePrimary': True,
    'doBalanceExposure': False,
    'doDither': False,
    'usePrevious': False,
    'doCompletedObservations': False,
    'doPlannedObservations': False,
    'cobs': [None, None],
    'schedule_type': 'greedy',
    'filterScheduleType': 'block',
    'airmass': 2.5,
    'scheduleStrategy': 'tiling',
    'mindiff': 30.0 * 60.0,
    'doMaxTiles': False,
    'max_nb_tiles': 1000,
    'doRASlice': True,
    'raslice': [0.0, 24.0],
    'probability': 0.9,
}


class PlanHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """
        ---
        description: Create an observation plan
        tags:
          - observingplans
        requestBody:
          content:
            application/json:
              schema: PlanHandlerPost
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          type: object
                          properties:
                            id:
                              type: integer
                              description: New plan ID
          400:
            content:
              application/json:
                schema: Error
        """

        data = self.get_json()

        telescope_name = data.get('telescope_name')
        instrument_name = data.get('instrument_name')
        dateobs = data.get('dateobs')
        localization_name = data.get('localization_name')

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

        localization = (
            Localization.query_records_accessible_by(
                self.current_user,
            )
            .filter(
                Localization.dateobs == dateobs,
                Localization.localization_name == localization_name,
            )
            .first()
        )
        if localization is None:
            return self.error(message=f"Missing localization {localization_name}")
        # force localization.flat to be loaded for async process
        localization.flat

        plan_args = copy.copy(plan_args_default)

        plan = setup_plan(self, instrument, localization, plan_args)

        plan_func = functools.partial(
            create_plan, self, instrument, localization, plan, plan_args
        )
        IOLoop.current().run_in_executor(None, plan_func)

        return self.success(data={"id": plan.id})

    @auth_or_token
    def get(self):
        """
        ---
        description: Retrieve observing plans
        tags:
          - observingplans
        parameters:
          - in: catalog_query
            name: dateobs
            schema:
              type: string
            description: Filter by event name (exact match)
        responses:
          200:
            content:
              application/json:
                schema: ArrayOfEventObservingPlan
          400:
            content:
              application/json:
                schema: Error
        """

        data = self.get_json()

        dateobs = data.get('dateobs')
        if dateobs is None:
            self.error(message="Missing required dateobs")

        plans = (
            EventObservingPlan.query_records_accessible_by(
                self.current_user,
                options=[
                    joinedload(EventObservingPlan.planned_observations),
                ],
            )
            .filter(
                EventObservingPlan.dateobs == dateobs,
            )
            .all()
        )

        return self.success(data=plans)


def params_struct(
    dateobs,
    instrument,
    plan_args,
):
    """Set gwemopt parameter dictionary for observing plan."""

    observer = ephem.Observer()
    observer.lat = str(instrument.telescope.lat)
    observer.lon = str(instrument.telescope.lon)
    observer.horizon = str(-12.0)
    observer.elevation = instrument.telescope.elevation

    event_time = time.Time(dateobs, format='datetime', scale='utc')

    params = {
        **plan_args,
        'config': {
            instrument.name: {
                'tesselation': instrument.fields,
                'longitude': instrument.telescope.lon,
                'latitude': instrument.telescope.lat,
                'elevation': instrument.telescope.elevation,
                'horizon': -12.0,
                'telescope': instrument.name,
                'exposuretime': 30.0,
                'magnitude': 20.4,
                'FOV': 6.86,
                'overhead_per_exposure': 0.0,
                'filt_change_time': 0.0,
            },
        },
        'doAlternativeFilters': plan_args["filterScheduleType"] == "block",
        'doDatabase': True,
        'doMinimalTiling': True,
        'doSingleExposure': True,
        'filters': plan_args["filt"],
        'gpstime': event_time.gps,
        'nside': 512,
        'powerlaw_cl': plan_args["probability"],
        'telescopes': [instrument.name],
    }
    params['max_nb_tiles'] = np.array(
        [plan_args['max_nb_tiles']] * len(plan_args['filt'])
    )

    if plan_args['scheduleStrategy'] == "catalog":
        params = {
            **params,
            'tilesType': 'galaxy',
            'galaxy_catalog': 'CLU',
            'galaxy_grade': 'S',
            'writeCatalog': False,
            'catalog_n': 1.0,
            'powerlaw_dist_exp': 1.0,
        }
    elif plan_args['scheduleStrategy'] == "tiling":
        params = {**params, 'tilesType': 'moc'}

    params = gwemopt.utils.params_checker(params)
    params = gwemopt.segments.get_telescope_segments(params)

    return params


def gen_structs(params):
    """Use gwemopt to create observing plan for specified instrument
    and time window."""

    # Function to read maps
    map_struct = gwemopt.utils.read_skymap(
        params, is3D=params["do3D"], map_struct=params['map_struct']
    )
    moc_structs = gwemopt.skyportal.create_moc_from_skyportal(
        params, map_struct=map_struct
    )
    tile_structs = gwemopt.tiles.moc(params, map_struct, moc_structs)

    if "previous_coverage_struct" in params:
        tile_structs, coverage_struct = gwemopt.coverage.timeallocation(
            params,
            map_struct,
            tile_structs,
            previous_coverage_struct=params["previous_coverage_struct"],
        )
    else:
        tile_structs, coverage_struct = gwemopt.coverage.timeallocation(
            params, map_struct, tile_structs
        )

    return map_struct, tile_structs, coverage_struct


def setup_plan(
    request_handler,
    instrument,
    localization,
    plan_args,
    validity_window_start=None,
    validity_window_end=None,
):
    """Setup gwemopt plan in the database (as PENDING)."""

    dateobs = localization.dateobs

    if validity_window_start is None:
        validity_window_start = datetime.datetime.now()
    if validity_window_end is None:
        validity_window_end = validity_window_start + datetime.timedelta(1)

    plan_args = dict(plan_args)
    plan_args.setdefault(
        'Tobs',
        [
            time.Time(validity_window_start).mjd - time.Time(dateobs).mjd,
            time.Time(validity_window_end).mjd - time.Time(dateobs).mjd,
        ],
    )

    if plan_args['doDither'] and instrument.nickname == 'DECam':
        # Add dithering
        plan_args['exposuretimes'] = [2 * x for x in plan_args['exposuretimes']]

    if 'plan_name' not in plan_args:
        plan_args['plan_name'] = "%s_%s_%s_%d_%d_%s_%d_%d" % (
            localization.localization_name,
            "".join(plan_args['filt']),
            plan_args['schedule_type'],
            plan_args['doDither'],
            plan_args['doReferences'],
            plan_args['filterScheduleType'],
            plan_args['exposuretimes'][0],
            100 * plan_args['probability'],
        )

    try:
        plan = EventObservingPlan.query.filter_by(
            plan_name=plan_args['plan_name']
        ).one()
    except NoResultFound:
        plan = EventObservingPlan(
            dateobs=localization.dateobs,
            plan_name=plan_args['plan_name'],
            instrument_id=instrument.id,
            validity_window_start=validity_window_start,
            validity_window_end=validity_window_end,
            plan_args=plan_args,
        )
        DBSession().add(plan)
        request_handler.verify_and_commit()

    return plan


def create_plan(
    request_handler,
    instrument,
    localization,
    plan,
    plan_args,
):
    """Create and commit gwemopt plan to the database."""

    dateobs = localization.dateobs

    params = params_struct(localization.dateobs, instrument, plan_args)

    params['map_struct'] = dict(
        zip(['prob', 'distmu', 'distsigma', 'distnorm'], localization.flat)
    )

    if plan_args['usePrevious']:
        previous_telescope, previous_name = plan_args['previous_plan'].split("-")
        plan_previous = EventObservingPlan.query.filter_by(
            dateobs=dateobs, telescope=previous_telescope, plan_name=previous_name
        ).one()
        ipix_previous = list(
            {
                i
                for planned_observation in plan_previous.planned_observations
                if planned_observation.field.ipix is not None
                for i in planned_observation.field.ipix
            }
        )
        params['map_struct']['prob'][ipix_previous] = 0.0

    params['is3D'] = localization.is_3d
    params['localization_name'] = localization.localization_name
    map_struct, tile_structs, coverage_struct = gen_structs(params)

    filter_ids = {"g": 1, "r": 2, "i": 3, "z": 4, "J": 5}
    for ii in range(len(coverage_struct["ipix"])):
        data = coverage_struct["data"][ii, :]
        filt = coverage_struct["filters"][ii]
        filter_id = filter_ids[filt]
        mjd = data[2]
        tt = time.Time(mjd, format='mjd')

        overhead_per_exposure = params["config"][instrument.name][
            "overhead_per_exposure"
        ]

        exposure_time, field_id, prob = data[4], data[5], data[6]

        planned_observation = PlannedObservation(
            obstime=tt.datetime,
            dateobs=dateobs,
            field_id=field_id,
            exposure_time=exposure_time,
            weight=prob,
            filter_id=filter_id,
            instrument_id=instrument.id,
            planned_observation_id=ii,
            plan_name=plan.plan_name,
            overhead_per_exposure=overhead_per_exposure,
        )

        DBSession().add(planned_observation)
    plan.status = plan.Status.READY
    DBSession().merge(plan)
    request_handler.verify_and_commit()
