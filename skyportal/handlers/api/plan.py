import datetime
import copy

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import joinedload
from astropy import time
import ephem
import gwemopt
import numpy as np

from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from ...models import (
    DBSession,
    Instrument,
    Localization,
    ObservingPlan,
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
    'schedule_strategy': 'tiling',
    'mindiff': 30.0 * 60.0,
    'doMaxTiles': False,
    'max_nb_tiles': 1000,
    'doRASlice': True,
    'raslice': [0.0, 24.0],
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
                schema: Success
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
            self.error(message=f"Missing telescope {telescope_name}")

        instrument = (
            Instrument.query_records_accessible_by(
                self.current_user,
            )
            .filter(
                Instrument.telescope == telescope,
                Instrument.name == instrument_name,
            )
            .first()
        )
        if instrument is None:
            self.error(message=f"Missing instrument {instrument_name}")

        localization = (
            Localization.query_records_accessible_by(self.current_user)
            .filter(
                Localization.dateobs == dateobs,
                Localization.localization_name == localization_name,
            )
            .first()
        )
        if localization is None:
            self.error(message=f"Missing localization {localization_name}")

        plan_args = copy.deepcopy(plan_args_default)

        create_plan(self, instrument, localization, **plan_args)

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
                schema: ArrayOfObservingPlan
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
            ObservingPlan.query_records_accessible_by(
                self.current_user,
                options=[
                    joinedload(ObservingPlan.planned_observations),
                ],
            )
            .filter(
                ObservingPlan.dateobs == dateobs,
            )
            .all()
        )

        return self.success(data=plans)


def params_struct(
    dateobs,
    instrument,
    tobs=None,
    filt=['r'],
    exposuretimes=[60.0],
    mindiff=30.0 * 60.0,
    probability=0.9,
    airmass=2.5,
    schedule_type='greedy',
    doReferences=True,
    doUsePrimary=False,
    doBalanceExposure=False,
    filterScheduleType='block',
    schedule_strategy='tiling',
    doCompletedObservations=False,
    cobs=None,
    doPlannedObservations=False,
    doMaxTiles=False,
    max_nb_tiles=1000,
    doRASlice=False,
    raslice=[0, 24],
):
    """Set gwemopt parameter dictionary for observing plan."""

    observer = ephem.Observer()
    observer.lat = str(instrument.telescope.lat)
    observer.lon = str(instrument.telescope.lon)
    observer.horizon = str(-12.0)
    observer.elevation = instrument.telescope.elevation

    event_time = time.Time(dateobs, format='datetime', scale='utc')

    params = {
        'airmass': airmass,
        'config': {
            instrument.name: {
                'tesselation': instrument.fields,
                'longitude': instrument.telescope.lon,
                'latitutude': instrument.telescope.lat,
                'elevation': instrument.telescope.elevation,
                'horizon': -12.0,
                'telescope': instrument.name,
                'exposuretime': 30.0,
                'magnitude': 20.4,
                'FOV': 6.86,
                'overhead_per_exposure': 0.0,
            },
        },
        'dateobs': dateobs,
        'doAlternativeFilters': filterScheduleType == "block",
        'doBalanceExposure': doBalanceExposure,
        'doDatabase': True,
        'doMaxTiles': True,
        'doMinimalTiling': True,
        'doRASlice': doRASlice,
        'doReferences': doReferences,
        'doSingleExposure': True,
        'doUsePrimary': doUsePrimary,
        'exposuretimes': exposuretimes,
        'filters': filt,
        'gpstime': event_time.gps,
        'max_nb_tiles': np.array([max_nb_tiles] * len(filt)),
        'mindiff': mindiff,
        'nside': 512,
        'powerlaw_cl': probability,
        'raslice': raslice,
        'scheduleType': schedule_type,
        'telescopes': [instrument.name],
    }

    if schedule_strategy == "catalog":
        params = {
            **params,
            'tilesType': 'galaxy',
            'galaxy_catalog': 'CLU',
            'galaxy_grade': 'S',
            'writeCatalog': False,
            'catalog_n': 1.0,
            'powerlaw_dist_exp': 1.0,
        }
    elif schedule_strategy == "tiling":
        params = {**params, 'tilesType': 'moc'}

    if tobs is None:
        now_time = time.Time.now()
        timediff = now_time.gps - event_time.gps
        timediff_days = timediff / 86400.0
        params["Tobs"] = np.array([timediff_days, timediff_days + 1])
    else:
        params["Tobs"] = tobs

    params = gwemopt.segments.get_telescope_segments(params)
    params = gwemopt.utils.params_checker(params)

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


def create_plan(
    request_handler,
    instrument,
    localization,
    validity_window_start=None,
    validity_window_end=None,
    plan_name=None,
    **plan_args,
):
    """Create and commit gwemopt plan to the database."""

    dateobs = localization.dateobs

    if validity_window_start is None:
        validity_window_start = datetime.datetime.now()
    if validity_window_end is None:
        validity_window_end = validity_window_start + datetime.timedelta(1)

    plan_args = dict(plan_args)
    plan_args.setdefault(
        'tobs',
        [
            time.Time(validity_window_start).mjd - time.Time(dateobs).mjd,
            time.Time(validity_window_end).mjd - time.Time(dateobs).mjd,
        ],
    )

    exposuretimes = plan_args['exposuretimes']
    if plan_args['doDither'] and instrument.nickname == 'DECam':
        # Add dithering
        exposuretimes = [2 * x for x in exposuretimes]

    plan_args.setdefault('probability', 0.9)

    if plan_name is None:
        plan_name = "%s_%s_%s_%d_%d_%s_%d_%d" % (
            localization.localization_name,
            "".join(plan_args['filt']),
            plan_args['schedule_type'],
            plan_args['doDither'],
            plan_args['doReferences'],
            plan_args['filterScheduleType'],
            exposuretimes[0],
            100 * plan_args['probability'],
        )

    try:
        plan = ObservingPlan.query.filter_by(plan_name=plan_name).one()
    except NoResultFound:
        plan = ObservingPlan(
            dateobs=localization.dateobs,
            plan_name=plan_name,
            instrument_id=instrument.id,
            validity_window_start=validity_window_start,
            validity_window_end=validity_window_end,
            plan_args=plan_args,
        )
        DBSession().add(plan)
        request_handler.verify_and_commit()

    planned = plan_args['doPlannedObservations']
    completed = plan_args['doCompletedObservations']
    maxtiles = plan_args['doMaxTiles']

    params = params_struct(
        localization.dateobs,
        tobs=np.asarray(plan_args['tobs']),
        filt=plan_args['filt'],
        exposuretimes=exposuretimes,
        probability=plan_args['probability'],
        instrument=instrument,
        schedule_type=plan_args['schedule_type'],
        doReferences=plan_args['doReferences'],
        doUsePrimary=plan_args['doUsePrimary'],
        filterScheduleType=plan_args['filterScheduleType'],
        schedule_strategy=plan_args['schedule_strategy'],
        mindiff=plan_args['mindiff'],
        doCompletedObservations=completed,
        cobs=plan_args['cobs'],
        doPlannedObservations=planned,
        doMaxTiles=maxtiles,
        max_nb_tiles=plan_args['max_nb_tiles'],
        doRASlice=plan_args['doRASlice'],
        raslice=plan_args['raslice'],
        doBalanceExposure=plan_args['doBalanceExposure'],
        airmass=plan_args['airmass'],
    )

    params['map_struct'] = dict(
        zip(['prob', 'distmu', 'distsigma', 'distnorm'], localization.flat)
    )

    if plan_args['usePrevious']:
        previous_telescope, previous_name = plan_args['previous_plan'].split("-")
        plan_previous = ObservingPlan.query.filter_by(
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
            plan_name=plan_name,
            overhead_per_exposure=overhead_per_exposure,
        )

        DBSession().add(planned_observation)
    plan.status = plan.Status.READY
    DBSession().merge(plan)
    request_handler.verify_and_commit()
