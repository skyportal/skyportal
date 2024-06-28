import time
import traceback

import healpix_alchemy as ha
import humanize
import numpy as np
import pandas as pd
import sqlalchemy as sa
from astropy.time import Time
from regions import Regions
from sqlalchemy.orm import sessionmaker, scoped_session

from baselayer.log import make_log
from baselayer.app.flow import Flow
from baselayer.app.env import load_env

from ..handlers.api.galaxy import get_galaxies
from .cache import Cache, array_to_bytes

log = make_log('api/observation_plan')

env, cfg = load_env()
cache_dir = "cache/localization_instrument_queries"
cache = Cache(
    cache_dir=cache_dir,
    max_items=cfg.get("misc.max_items_in_localization_instrument_query_cache", 100),
    max_age=cfg.get("misc.minutes_to_keep_localization_instrument_query_cache", 24 * 60)
    * 60,  # defaults to 1 day
)

use_skyportal_fields = cfg['app.observation_plan.use_skyportal_fields']
use_parallel = cfg.get('app.observation_plan.use_parallel', False)
Ncores = cfg.get('app.observation_plan.Ncores', 1)


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

        partition_key = event.dateobs
        # now get the dateobs in the format YYYY_MM
        localizationtile_partition_name = (
            f'{partition_key.year}_{partition_key.month:02d}'
        )
        localizationtilescls = LocalizationTile.partitions.get(
            localizationtile_partition_name, None
        )
        if localizationtilescls is None:
            localizationtilescls = LocalizationTile
        else:
            # check that there is actually a localizationTile with the given localization_id in the partition
            # if not, use the default partition
            if not (
                session.scalars(
                    sa.select(localizationtilescls.localization_id).where(
                        localizationtilescls.localization_id == request.localization_id
                    )
                ).first()
            ):
                localizationtilescls = LocalizationTile.partitions.get(
                    'def', LocalizationTile
                )

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
):
    """Use gwemopt to construct multiple observing plans."""

    from ..models import DBSession
    from skyportal.handlers.api.instrument import add_tiles

    import gwemopt
    import gwemopt.coverage
    import gwemopt.io
    import gwemopt.segments

    from ..models import (
        EventObservationPlan,
        InstrumentField,
        InstrumentFieldTile,
        LocalizationTile,
        ObservationPlanRequest,
        PlannedObservation,
        User,
    )

    Session = scoped_session(sessionmaker())
    if Session.registry.has():
        session = Session()
    else:
        session = Session(bind=DBSession.session_factory.kw["bind"])

    plans, requests = [], []
    observation_plan_id_strings = [str(x) for x in observation_plan_ids]

    error = None
    try:
        log(
            f"Creating observation plan(s) for ID(s): {','.join(observation_plan_id_strings)}"
        )

        session = Session()
        for observation_plan_id, request_id in zip(observation_plan_ids, request_ids):
            plan = session.query(EventObservationPlan).get(observation_plan_id)
            request = session.query(ObservationPlanRequest).get(request_id)

            plans.append(plan)
            requests.append(request)

        user = session.query(User).get(user_id)
        log(
            f"Running observation plan(s) for ID(s): {','.join(observation_plan_id_strings)} in session {user._sa_instance_state.session_id}"
        )
        session.user_or_token = user

        event_time = Time(requests[0].gcnevent.dateobs, format='datetime', scale='utc')
        start_time = Time(requests[0].payload["start_date"], format='iso', scale='utc')
        end_time = Time(requests[0].payload["end_date"], format='iso', scale='utc')

        params = {
            # time
            'Tobs': [start_time.mjd - event_time.mjd, end_time.mjd - event_time.mjd],
            # geometry
            'geometry': '3d' if request.localization.is_3d else '2d',
            # gwemopt filter strategy
            # options: block (blocks of single filters), integrated (series of alternating filters)
            'doAlternatingFilters': True
            if request.payload["filter_strategy"] == "block"
            else False,
            'doBlocks': True
            if request.payload["filter_strategy"] == "block"
            else False,
            # flag to indicate fields come from DB
            'doDatabase': True,
            # only keep tiles within powerlaw_cl
            'doMinimalTiling': True,
            # single set of scheduled observations
            'doSingleExposure': True,
            # parallelize computation
            'doParallel': use_parallel,
            'Ncores': Ncores,
            'parallelBackend': 'threading',
            # gwemopt scheduling algorithms
            # options: greedy, greedy_slew, sear, airmass_weighted
            'scheduleType': request.payload["schedule_type"],
            # list of filters to use for observations
            'filters': request.payload["filters"].split(","),
            # GPS time for event
            'gpstime': event_time.gps,
            # Dateobs of the event in UTC, used when doDatabase is True
            'dateobs': requests[0].gcnevent.dateobs,
            # Healpix nside for the skymap
            'nside': 512,
            # maximum integrated probability of the skymap to consider
            'confidence_level': request.payload["integrated_probability"],
            'telescopes': [request.instrument.name for request in requests],
            # minimum difference between observations of the same field
            'doMindifFilt': True
            if request.payload.get("minimum_time_difference", 0) > 0
            else False,
            'mindiff': request.payload.get("minimum_time_difference", 0) * 60,
            # maximum airmass with which to observae
            'airmass': request.payload["maximum_airmass"],
            # array of exposure times (same length as filter array)
            'exposuretimes': np.array(
                [request.payload["exposure_time"]]
                * len(request.payload["filters"].split(","))
            ),
            # avoid the galactic plane?
            'doAvoidGalacticPlane': request.payload.get("galactic_plane", False),
            # galactic latitude to exclude
            'galactic_limit': request.payload.get("galactic_latitude", 10),
            # Maximum number of fields to consider
            'max_nb_tiles': request.payload.get("max_nb_tiles", 100)
            * len(request.payload["filters"].split(","))
            if request.payload.get("max_tiles", False)
            else None,
            # balance observations by filter
            'doBalanceExposure': request.payload.get("balance_exposure", False),
            # slice observations by right ascension
            'doRASlice': request.payload.get("ra_slice", False),
            # try scheduling with multiple RA slices
            'doRASlices': False,
            # right ascension block
            'raslice': [
                request.payload.get("ra_slice_min", 0),
                request.payload.get("ra_slice_max", 360),
            ],
            # use only primary grid
            'doUsePrimary': request.payload.get("use_primary", False),
            'doUseSecondary': request.payload.get("use_secondary", False),
            # iterate through telescopes
            'doIterativeTiling': False,
            # amount of overlap to keep for multiple telescopes
            'iterativeOverlap': 0.0,
            # maximum overlap between telescopes
            'maximumOverlap': 1.0,
            # time allocation strategy
            'timeallocationType': 'powerlaw',
            # check for references, works in gwemopt only for ZTF and DECAM
            'doReferences': request.payload.get("use_references", False),
            # treasuremap interactions
            'treasuremap_token': None,
            # number of scheduling blocks to attempt
            'Nblocks': 1,
            # enable splitting by telescope
            'splitType': None,
            # perturb tiles to maximize probability
            'doPerturbativeTiling': False,
            # check for overlapping telescope schedules
            'doOverlappingScheduling': False,
            # which telescope tiles to turn off
            'unbalanced_tiles': None,
            # turn on diagnostic plotting?
            'plots': [],
            # parameters used for galaxy targeting
            'galaxies_FoV_sep': 1.0,
            'doChipGaps': False,
            'ignore_observability': False,
            # solver type (heuristic or milp)
            'solverType': 'heuristic',
        }

        if len(requests) > 1:
            params['doOrderByObservability'] = True

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

            # setup defaults for observation plans

            # time in seconds to change the filter
            filt_change_time = 0.0
            # extra overhead in seconds
            overhead_per_exposure = 0.0
            # slew rate for the telescope [deg/s]
            slew_rate = 2.6
            # camera readout time
            readout = 0.0

            configuration_data = request.instrument.configuration_data
            if configuration_data:
                filt_change_time = configuration_data.get(
                    'filt_change_time', float(filt_change_time)
                )
                overhead_per_exposure = configuration_data.get(
                    'overhead_per_exposure', float(overhead_per_exposure)
                )
                slew_rate = configuration_data.get('slew_rate', float(slew_rate))
                readout = configuration_data.get('readout', float(readout))

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
                'filt_change_time': filt_change_time,
                # extra overhead in seconds
                'overhead_per_exposure': overhead_per_exposure,
                # slew rate for the telescope [deg/s]
                'slew_rate': slew_rate,
                # camera readout time
                'readout': readout,
                # telescope FOV_type
                'FOV_type': None,  # TODO: use the instrument FOV from the database
                # telescope field of view
                'FOV': 0.0,
                # exposure time for the given limiting magnitude
                'exposuretime': 1.0,
                # limiting magnitude given telescope time
                'magnitude': 0.0,
            }

            if request.payload.get("use_references", False):
                config[request.instrument.name]["reference_images"] = {
                    field.field_id: field.reference_filters
                    if field.reference_filters is not None
                    else []
                    for field in fields
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
                # TODO: Fix gwemopt.coverage.timeallocation doBlocks if statement
                # which doesnt pass catalog_struct to gwemopt.tiles.powerlaw_tiles_struct -> gwemopt.tiles.compute_tiles_map
                # in other methods (outside of doBlocks statement), it does use the catalog_struct we added in the tile_structs
                # until then, we force doBlocks to False
                'doBlocks': False,
            }
        elif request.payload["schedule_strategy"] == "tiling":
            params = {**params, 'tilesType': 'moc'}
        else:
            raise AttributeError('scheduling_strategy should be tiling or galaxy')

        # params = gwemopt.utils.params_checker(params)
        params = gwemopt.segments.get_telescope_segments(params)

        map_struct = {'skymap': request.localization.table}

        log(f"Reading skymap for ID(s): {','.join(observation_plan_id_strings)}")

        # Function to read maps
        params, map_struct = gwemopt.io.read_skymap(params, map_struct=map_struct)

        # get the partition name for the localization tiles using the dateobs
        # that way, we explicitely use the partition that contains the localization tiles we are interested in
        # that should help not reach that "critical point" mentioned by @mcoughlin where the queries almost dont work anymore
        # locally this takes anywhere between 0.08 and 0.5 seconds, but in production right now it takes 45 minutes...
        # that is why we are considering to use a partitioned table for localization tiles
        partition_key = requests[0].gcnevent.dateobs
        # now get the dateobs in the format YYYY_MM
        localizationtile_partition_name = (
            f'{partition_key.year}_{partition_key.month:02d}'
        )
        localizationtilescls = LocalizationTile.partitions.get(
            localizationtile_partition_name, None
        )
        if localizationtilescls is None:
            localizationtilescls = LocalizationTile.partitions.get(
                'def', LocalizationTile
            )
        else:
            # check that there is actually a localizationTile with the given localization_id in the partition
            # if not, use the default partition
            if not (
                session.scalars(
                    sa.select(localizationtilescls.localization_id).where(
                        localizationtilescls.localization_id == request.localization.id
                    )
                ).first()
            ):
                localizationtilescls = LocalizationTile.partitions.get(
                    'def', LocalizationTile
                )

        start = time.time()

        cum_prob = (
            sa.func.sum(
                localizationtilescls.probdensity * localizationtilescls.healpix.area
            )
            .over(order_by=localizationtilescls.probdensity.desc())
            .label('cum_prob')
        )
        localizationtile_subquery = (
            sa.select(localizationtilescls.probdensity, cum_prob).filter(
                localizationtilescls.localization_id == request.localization.id
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

        if params["tilesType"] == "galaxy":
            if "galaxy_sorting" not in request.payload:
                galaxy_sorting = "equal"
            else:
                galaxy_sorting = request.payload["galaxy_sorting"]

            log("querying for galaxies in the localization...")
            start = time.time()
            galaxies = get_galaxies(
                session,
                catalog_name=params["galaxy_catalog"],
                localization_dateobs=request.gcnevent.dateobs,
                localization_name=request.localization.localization_name,
                localization_cumprob=integrated_probability,
                return_probability=True,
                sort_by=galaxy_sorting
                if galaxy_sorting
                in ["sfr_fuv", "mstar", "magb", "magk", "mstar_prob_weighted"]
                else "mstar_prob_weighted",
                sort_order="asc" if galaxy_sorting in ["magb", "magk"] else "desc",
                num_per_page=1000,  # limit to top 1k galaxies
            )
            # the result is a dict with a "galaxies" key, each of these galaxies
            # has a "probability" key that is the probability of the galaxy being in the localization
            # reformat the result to a list of galaxies and a list of probabilities
            galaxies, probs = zip(
                *[(g, g["probability"]) for g in galaxies["galaxies"]]
            )
            log("done querying and reformatting the results")
            end = time.time()
            log(
                f"querying for galaxies took {end - start} seconds: {len(galaxies)} galaxies found"
            )

            catalog_struct = {}
            catalog_struct["ra"] = np.array([g["ra"] for g in galaxies])
            catalog_struct["dec"] = np.array([g["dec"] for g in galaxies])

            if galaxy_sorting == "equal":
                values = np.array([1.0 for g in galaxies])
            elif galaxy_sorting == "sfr_fuv":
                values = np.array([g["sfr_fuv"] for g in galaxies])
            elif galaxy_sorting in "mstar":
                values = np.array([g["mstar"] for g in galaxies])
            elif galaxy_sorting == "magb":
                values = np.array([g["magb"] for g in galaxies])
            elif galaxy_sorting == "magk":
                values = np.array([g["magk"] for g in galaxies])
            elif galaxy_sorting == "mstar_prob_weighted":
                # here the values should be mstar * probability
                values = np.array([g["mstar"] for g in galaxies])
                # replace mstar with 0 if it is None
                values = [0 if v is None else v for v in values]
                values = values * np.array(probs)

            idx = np.where(values != None)[0]  # noqa: E711

            if len(idx) == 0:
                error = "No galaxies available for scheduling."
                raise ValueError(error)

            probs = np.array(probs)[idx]
            values = values[idx]
            if galaxy_sorting in ["magb", "magk"]:
                # weigh brighter more heavily
                values = -values
                values = (values - np.min(values)) / (np.max(values) - np.min(values))

            catalog_struct["ra"] = catalog_struct["ra"][idx]
            catalog_struct["dec"] = catalog_struct["dec"][idx]
            catalog_struct["S"] = values * probs
            catalog_struct["Sloc"] = values * probs
            catalog_struct["Smass"] = values * probs

            catalog_struct = pd.DataFrame.from_dict(catalog_struct)

        elif params["tilesType"] == "moc":
            field_ids = {}
            if use_skyportal_fields is True:
                for request in requests:
                    query_id = f"{str(request.localization.id)}_{str(request.instrument.id)}_{str(int(request.payload['integrated_probability'])/100.0)}"
                    cache_filename = cache[query_id]
                    if cache_filename is not None:
                        field_tiles = np.load(cache_filename).tolist()
                    else:
                        field_tiles_query = sa.select(InstrumentField.field_id).where(
                            localizationtilescls.localization_id
                            == request.localization.id,
                            localizationtilescls.probdensity >= min_probdensity,
                            InstrumentFieldTile.instrument_id == request.instrument.id,
                            InstrumentFieldTile.instrument_field_id
                            == InstrumentField.id,
                            InstrumentFieldTile.healpix.overlaps(
                                localizationtilescls.healpix
                            ),
                        )
                        field_tiles = session.scalars(field_tiles_query).unique().all()
                        if len(field_tiles) > 0:
                            cache[query_id] = array_to_bytes(field_tiles)
                    field_ids[request.instrument.name] = field_tiles

        end = time.time()
        log(f"Queries took {end - start} seconds")

        log(f"Retrieving fields for ID(s): {','.join(observation_plan_id_strings)}")

        if params["tilesType"] == "moc":
            moc_structs = gwemopt.moc.create_moc(
                params,
                map_struct=map_struct,
                field_ids=field_ids if use_skyportal_fields is True else None,
                from_skyportal=True,
            )
            tile_structs = gwemopt.tiles.moc(params, map_struct, moc_structs)
        elif params["tilesType"] == "galaxy":
            for request in requests:
                if request.instrument.region is None:
                    error = "Must define the instrument region in the case of galaxy requests"
                    raise ValueError(error)
                regions = Regions.parse(request.instrument.region, format='ds9')
                tile_structs = gwemopt.tiles.galaxy(
                    params, map_struct, catalog_struct, regions=regions
                )

        log(f"Creating schedule(s) for ID(s): {','.join(observation_plan_id_strings)}")

        tile_structs, coverage_struct = gwemopt.coverage.timeallocation(
            params, map_struct, tile_structs
        )

        # if the fields do not yet exist, we need to add them
        if params["tilesType"] == "galaxy":
            field_ids = np.array([-1] * len(coverage_struct["data"]))
            for request in requests:
                regions = Regions.parse(request.instrument.region, format='ds9')
                idx = np.where(coverage_struct["telescope"] == request.instrument.name)[
                    0
                ]
                data = {
                    'RA': coverage_struct["data"][idx, 0],
                    'Dec': coverage_struct["data"][idx, 1],
                }
                field_data = pd.DataFrame.from_dict(data)
                idx = np.array(idx).astype(int)
                field_id = add_tiles(
                    request.instrument.id,
                    request.instrument.name,
                    regions,
                    field_data,
                    session=session,
                )
                field_ids[idx] = field_id
        log(
            f"Writing planned observations to database for ID(s): {','.join(observation_plan_id_strings)}"
        )

        planned_observations = []
        for ii in range(len(coverage_struct["moc"])):
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
            field = session.scalars(
                sa.select(InstrumentField).where(
                    InstrumentField.instrument_id == request.instrument.id,
                    InstrumentField.field_id == field_id,
                )
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
        session.commit()

        for plan in plans:
            setattr(plan, 'status', 'complete')
            session.merge(plan)

        session.commit()

        log(f"Generating statistics for ID(s): {','.join(observation_plan_id_strings)}")

        generate_observation_plan_statistics(observation_plan_ids, request_ids, session)

        flow = Flow()
        flow.push(
            '*',
            "skyportal/REFRESH_GCNEVENT_OBSERVATION_PLAN_REQUESTS",
            payload={"gcnEvent_dateobs": request.gcnevent.dateobs},
        )

        log(f"Finished plan(s) for ID(s): {','.join(observation_plan_id_strings)}")

    except Exception as e:
        traceback.print_exc()
        log(
            f"Failed to generate plans for ID(s): {','.join(observation_plan_id_strings)}: {str(e)}."
        )
        session.rollback()
        # mark the request and plan as failed
        failed_status = 'failed' if error is None else f'failed: {error}'
        for request in requests:
            request.status = failed_status
            session.merge(request)
        for plan in plans:
            plan.status = failed_status
            session.merge(plan)
        session.commit()

    session.close()
    Session.remove()
