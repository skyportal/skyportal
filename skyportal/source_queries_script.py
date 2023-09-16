import time

import arrow
import numpy as np
import sqlalchemy as sa
from astropy.time import Time
import astropy.units as u
from conesearch_alchemy.math import cosd, sind
from geojson import Feature, Point
from sqlalchemy.sql import and_, text
from tqdm import tqdm

from baselayer.app.env import load_env
from baselayer.app.models import init_db
from baselayer.log import make_log
from skyportal.models import (
    Allocation,
    Annotation,
    Classification,
    DBSession,
    Galaxy,
    Group,
    Localization,
    LocalizationTile,
    Obj,
    PhotStat,
    Source,
    Thumbnail,
    User,
    Comment,
    cosmo,
    SourceLabel,
)

_, cfg = load_env()
log = make_log('api/source_queries')

init_db(**cfg['database'])

DEFAULT_SOURCES_PER_PAGE = 1000

SORT_BY = {
    'saved_at': 'most_recent_saved_at',  # default
    'id': 'objs.id',
    'aliaxs': 'objs.alias',
    'origin': 'objs.origin',
    'ra': 'objs.ra',
    'dec': 'objs.dec',
    'redshift': 'objs.redshift',
    # TODO: sort by classification
    # TODO: sort by sourcesconfirmed in GCN status
}

SORT_ORDER = [
    'asc',
    'desc',
]

NULL_FIELDS = [
    "origin",
    "alias",
    "redshift",
]

DEGRA = np.pi / 180.0
HOOG_REDSHIFT_A, HOOG_REDSHIFT_B = 2.99e5 * u.km / u.s, 350 * u.km / u.s


def array2sql(array: list):
    # we make it a tuple
    array = tuple(array)
    return array


def radec2xyz(ra, dec):
    """
        Convert RA, Dec to Cartesian coordinates
    :param ra_deg:
    :param dec_deg:
    :return: x, y, z
    """
    return (cosd(ra) * cosd(dec), sind(ra) * cosd(dec), sind(dec))


def within(ra1, dec1, ra2, dec2, radius):
    """
        Test if this point is within a given radius of another point.
    :param other: Point
        The other point.
    :param radius: float
        The match radius in degrees.
    :return: bool
    """
    sin_radius = sind(radius)
    cos_radius = cosd(radius)
    carts = radec2xyz(ra1, dec1), radec2xyz(ra2, dec2)
    # Evaluate boolean expressions for bounding box test and dot product
    terms = (
        (lhs.between(rhs - 2 * sin_radius, rhs + 2 * sin_radius), lhs * rhs)
        for lhs, rhs in zip(*carts)
    )
    bounding_box_terms, dot_product_terms = zip(*terms)
    return and_(*bounding_box_terms, sum(dot_product_terms) >= cos_radius)


def great_circle_distance(ra1_deg, dec1_deg, ra2_deg, dec2_deg):
    """
        Distance between two points on the sphere
    :param ra1_deg:
    :param dec1_deg:
    :param ra2_deg:
    :param dec2_deg:
    :return: distance in degrees
    """
    # this is orders of magnitude faster than astropy.coordinates.Skycoord.separation

    ra1, dec1, ra2, dec2 = (
        ra1_deg * DEGRA,
        dec1_deg * DEGRA,
        ra2_deg * DEGRA,
        dec2_deg * DEGRA,
    )
    delta_ra = np.abs(ra2 - ra1)
    distance = np.arctan2(
        np.sqrt(
            (np.cos(dec2) * np.sin(delta_ra)) ** 2
            + (
                np.cos(dec1) * np.sin(dec2)
                - np.sin(dec1) * np.cos(dec2) * np.cos(delta_ra)
            )
            ** 2
        ),
        np.sin(dec1) * np.sin(dec2) + np.cos(dec1) * np.cos(dec2) * np.cos(delta_ra),
    )

    return distance * 180.0 / np.pi


def normalize_key(str):
    # convert the string to lowercase and remove underscores
    return str.lower().replace('_', '')


def get_color_mag(annotations, **kwargs):
    # please refer to `ObjColorMagHandler.get` below

    # ignore None inputs from e.g., query arguments
    inputs = {k: v for k, v in kwargs.items() if v is not None}

    catalog = inputs.get('catalog', 'gaia')
    mag_key = inputs.get('apparentMagKey', 'Mag_G')
    parallax_key = inputs.get('parallaxKey', 'Plx')
    absorption_key = inputs.get('absorptionKey', 'A_G')
    abs_mag_key = inputs.get('absoluteMagKey', None)
    blue_mag_key = inputs.get('blueMagKey', 'Mag_Bp')
    red_mag_key = inputs.get('redMagKey', 'Mag_Rp')
    color_key = inputs.get('colorKey', None)

    output = []

    for an in annotations:
        abs_mag = None
        color = None
        absorption = None
        if normalize_key(catalog) in normalize_key(an['origin']):
            # found the right catalog, but does it have the right keys?

            # get the absolute magnitude
            if abs_mag_key is not None:  # get the absolute magnitude directly
                for k in an['data'].keys():
                    if normalize_key(abs_mag_key) == normalize_key(k):
                        abs_mag = an['data'][k]  # found it!
            else:  # we need to look for the apparent magnitude and parallax
                mag = None
                plx = None
                for k in an['data'].keys():
                    if normalize_key(mag_key) == normalize_key(k):
                        mag = an['data'][k]
                    if normalize_key(parallax_key) == normalize_key(k):
                        plx = an['data'][k]
                    if mag is not None and plx is not None:
                        if plx > 0:
                            abs_mag = mag + 5 * np.log10(plx / 100)
                        else:
                            abs_mag = np.nan

            # get the color data
            if color_key is not None:  # get the color value directly
                for k in an['data'].keys():
                    if normalize_key(color_key) == normalize_key(k):
                        color = float(an['data'][k])  # found it!
            else:
                blue = None
                red = None
                for k in an['data'].keys():
                    if normalize_key(blue_mag_key) == normalize_key(k):
                        blue = an['data'][k]
                    if normalize_key(red_mag_key) == normalize_key(k):
                        red = an['data'][k]
                    if blue is not None and red is not None:
                        # calculate the color between these two magnitudes
                        color = float(blue) - float(red)

            # only check this if given an absorption term
            if absorption_key is not None:
                for k in an['data'].keys():
                    if normalize_key(absorption_key) == normalize_key(k):
                        absorption = an['data'][k]

        if abs_mag is not None and color is not None:

            if absorption is not None and not np.isnan(absorption):
                abs_mag = abs_mag + absorption  # apply the absorption term

            output.append({'origin': an['origin'], 'abs_mag': abs_mag, 'color': color})

    return output


def get_period_exists(annotations):
    period_str_options = {'period', 'Period', 'PERIOD'}
    return any(
        [
            isinstance(an['data'], dict)
            and period_str_options.intersection(
                set(an['data'].keys())
            )  # check if the period string is an annotation
            for an in annotations
        ]
    )


def get_localization(localization_dateobs, localization_name, session):
    startTime = time.time()
    localization_dateobs_str = localization_dateobs.strftime('%Y-%m-%d %H:%M:%S')
    if localization_name is None:
        localization_id = session.scalars(
            sa.select(Localization.id)
            .where(Localization.dateobs == localization_dateobs_str)
            .order_by(Localization.created_at.desc())
        ).first()
    else:
        localization_id = session.scalars(
            sa.select(Localization.id)
            .where(Localization.dateobs == localization_dateobs_str)
            .where(Localization.localization_name == localization_name)
            .order_by(Localization.modified.desc())
        ).first()
    if localization_id is None:
        if localization_name is not None:
            raise ValueError(
                f"Localization {localization_dateobs_str} with name {localization_name} not found",
            )
        else:
            raise ValueError(
                f"Localization {localization_dateobs_str} not found",
            )

    partition_key = localization_dateobs
    localizationtile_partition_name = f'{partition_key.year}_{partition_key.month:02d}'
    localizationtilescls = LocalizationTile.partitions.get(
        localizationtile_partition_name, None
    )
    if localizationtilescls is None:
        localizationtilescls = LocalizationTile.partitions.get('def', LocalizationTile)
    else:
        if not (
            session.scalars(
                sa.select(localizationtilescls.id).where(
                    localizationtilescls.localization_id == localization_id
                )
            ).first()
        ):
            localizationtilescls = LocalizationTile.partitions.get(
                'def', LocalizationTile
            )

    endTime = time.time()
    log(f"get_localization took {endTime - startTime} seconds")

    return localization_id, localizationtilescls.__tablename__


# Rotation matrix for the conversion : x_galactic = R * x_equatorial (J2000)
# http://adsabs.harvard.edu/abs/1989A&A...218..325M
RGE = np.array(
    [
        [-0.054875539, -0.873437105, -0.483834992],
        [+0.494109454, -0.444829594, +0.746982249],
        [-0.867666136, -0.198076390, +0.455983795],
    ]
)


def radec2lb(ra, dec):
    """
        Convert $R.A.$ and $Decl.$ into Galactic coordinates $l$ and $b$
    ra [deg]
    dec [deg]

    return l [deg], b [deg]
    """
    ra_rad, dec_rad = np.deg2rad(ra), np.deg2rad(dec)
    u = np.array(
        [
            np.cos(ra_rad) * np.cos(dec_rad),
            np.sin(ra_rad) * np.cos(dec_rad),
            np.sin(dec_rad),
        ]
    )

    ug = np.dot(RGE, u)

    x, y, z = ug
    galactic_l = np.arctan2(y, x)
    galactic_b = np.arctan2(z, (x * x + y * y) ** 0.5)
    return np.rad2deg(galactic_l), np.rad2deg(galactic_b)


def get_luminosity_distance(obj):
    """
    The luminosity distance in Mpc, using either DM or distance data
    in the altdata fields or using the cosmology/redshift. Specifically
    the user can add `dm` (mag), `parallax` (arcsec), `dist_kpc`,
    `dist_Mpc`, `dist_pc` or `dist_cm` to `altdata` and
    those will be picked up (in that order) as the distance
    rather than the redshift.

    Return None if the redshift puts the source not within the Hubble flow
    """

    # there may be a non-redshift based measurement of distance
    # for nearby sources
    if isinstance(obj['altdata'], dict):
        if obj['altdata'].get("dm") is not None:
            # see eq (24) of https://ned.ipac.caltech.edu/level5/Hogg/Hogg7.html
            return (
                (10 ** (float(obj['altdata'].get("dm")) / 5.0)) * 1e-5 * u.Mpc
            ).value
        if obj['altdata'].get("parallax") is not None:
            if float(obj['altdata'].get("parallax")) > 0:
                # assume parallax in arcsec
                return (1e-6 * u.Mpc / float(obj['altdata'].get("parallax"))).value

        if obj['altdata'].get("dist_kpc") is not None:
            return (float(obj['altdata'].get("dist_kpc")) * 1e-3 * u.Mpc).value
        if obj['altdata'].get("dist_Mpc") is not None:
            return (float(obj['altdata'].get("dist_Mpc")) * u.Mpc).value
        if obj['altdata'].get("dist_pc") is not None:
            return (float(obj['altdata'].get("dist_pc")) * 1e-6 * u.Mpc).value
        if obj['altdata'].get("dist_cm") is not None:
            return (float(obj['altdata'].get("dist_cm")) * u.Mpc / 3.085e18).value

    if obj['redshift']:
        if obj['redshift'] * HOOG_REDSHIFT_A < HOOG_REDSHIFT_B:
            # stubbornly refuse to give a distance if the source
            # is not in the Hubble flow
            # cf. https://www.aanda.org/articles/aa/full/2003/05/aa3077/aa3077.html
            # within ~5 Mpc (cz ~ 350 km/s) a given galaxy velocty
            # can be between between ~0-500 km/s
            return None
        return (cosmo.luminosity_distance(obj['redshift'])).to(u.Mpc).value
    return None


def get_sources(
    user_id,
    session,
    include_thumbnails=False,
    include_comments=False,
    include_photometry_exists=False,
    include_spectrum_exists=False,
    include_comment_exists=False,
    include_period_exists=False,
    include_detection_stats=False,
    include_labellers=False,
    include_hosts=False,
    exclude_forced_photometry=False,
    is_token_request=False,
    include_requested=False,
    requested_only=False,
    include_color_mag=False,
    remove_nested=False,
    first_detected_date=None,
    last_detected_date=None,
    has_tns_name=False,
    has_no_tns_name=False,
    has_spectrum=False,
    has_no_spectrum=False,
    has_followup_request=False,
    has_been_labelled=False,
    has_not_been_labelled=False,
    current_user_labeller=False,
    sourceID=None,
    rejectedSourceIDs=None,
    ra=None,
    dec=None,
    radius=None,
    has_spectrum_before=None,
    has_spectrum_after=None,
    followup_request_status=None,
    saved_before=None,
    saved_after=None,
    created_or_modified_after=None,
    list_name=None,
    simbad_class=None,
    alias=None,
    origin=None,
    min_redshift=None,
    max_redshift=None,
    min_peak_magnitude=None,
    max_peak_magnitude=None,
    min_latest_magnitude=None,
    max_latest_magnitude=None,
    number_of_detections=None,
    classifications=None,
    classifications_simul=False,
    nonclassifications=None,
    classified=None,
    unclassified=False,
    annotations_filter=None,
    annotations_filter_origin=None,
    annotations_filter_before=None,
    annotations_filter_after=None,
    comments_filter=None,
    comments_filter_author=None,
    comments_filter_before=None,
    comments_filter_after=None,
    localization_dateobs=None,
    localization_name=None,
    localization_cumprob=None,
    localization_reject_sources=False,
    include_sources_in_gcn=False,
    spatial_catalog_name=None,
    spatial_catalog_entry_name=None,
    page_number=1,
    num_per_page=DEFAULT_SOURCES_PER_PAGE,
    sort_by='saved_at',
    sort_order="asc",
    group_ids=[],
    user_accessible_group_ids=None,
    save_summary=False,
    total_matches=None,
    includeGeoJSON=False,
    use_cache=False,
    query_id=None,
    verbose=False,
):
    # it takes one query argument, which is the query type
    # and the group_ids to query
    startMethodTime = time.time()

    if user_id is None:
        raise ValueError('No user_id provided.')

    if sort_by not in SORT_BY:
        raise ValueError(f'Invalid sort_by: {sort_by}')

    if sort_order.lower() not in SORT_ORDER:
        raise ValueError(f'Invalid sort_order: {sort_order}')

    user = session.scalar(sa.select(User).where(User.id == user_id))
    if user is None:
        raise ValueError(f'Invalid user_id: {user_id}')
    is_admin = user.is_admin

    user_group_ids = [g.id for g in user.accessible_groups]
    if len(group_ids) == 0 and not is_admin:
        group_ids = user_group_ids
    elif not set(group_ids).issubset(set(user_group_ids)):
        raise ValueError('Selected group(s) not all accessible to user.')

    allocation_ids = []
    if not is_admin:
        allocation_ids = (
            session.scalars(
                Allocation.select(user)
                .options(sa.orm.load_only(Allocation.id))
                .where(Allocation.group_id.in_(group_ids))
            )
            .unique()
            .all()
        )
        allocation_ids = [a.id for a in allocation_ids]

    statements = []
    query_params = {}
    # we use query parameters to avoid SQL injection, can be improved

    # GROUPS
    if len(group_ids) > 0:
        statements.append(
            """
            sources.group_id IN :group_ids
            """
        )
        query_params['group_ids'] = array2sql(group_ids)

    # OBJ
    if sourceID is not None:
        try:
            query_params['sourceID'] = str(sourceID).strip().lower()
            statements.append(
                """
                (lower(objs.id) LIKE '%' || :sourceID || '%')
                """
            )
        except Exception as e:
            raise ValueError(f'Invalid sourceID: {sourceID} ({e})')
    if rejectedSourceIDs is not None:
        try:
            query_params['rejectedSourceIDs'] = array2sql(rejectedSourceIDs)
            statements.append(
                """
                objs.id NOT IN :rejectedSourceIDs
                """
            )
        except Exception as e:
            raise ValueError(f'Invalid rejectedSourceIDs: {rejectedSourceIDs} ({e})')
    if alias is not None:
        if alias in ["", None]:
            raise ValueError(f'Invalid alias: {alias}')
        query_params['alias'] = alias.strip().lower()
        statements.append(
            """
            (lower(objs.alias) LIKE '%' || :alias || '%')
            """
        )
    if origin not in [None, ""]:
        query_params['origin'] = origin.strip().lower()
        # use a LIKE query to allow for partial matches
        statements.append(
            """
            (lower(objs.origin) LIKE '%' || :origin || '%')
            """
        )
    if simbad_class not in [None, ""]:
        query_params['simbad_class'] = str(simbad_class).strip().lower()
        # cast simba_class to a string
        statements.append(
            """
            lower(((objs.altdata['simbad']) ->> 'class')) LIKE '%' || :simbad_class || '%'
            """
        )
    if has_tns_name:
        statements.append(
            """
            objs.tns_name IS NOT NULL
            """
        )
    elif has_no_tns_name:
        statements.append(
            """
            objs.tns_name IS NULL
            """
        )
    if min_redshift is not None:
        try:
            query_params['min_redshift'] = float(min_redshift)
            statements.append(
                """
                objs.redshift >= :min_redshift
                """
            )
        except Exception as e:
            raise ValueError(f'Invalid min_redshift: {min_redshift} ({e})')
    if max_redshift is not None:
        try:
            query_params['max_redshift'] = float(max_redshift)
            statements.append(
                """
                objs.redshift <= :max_redshift
                """
            )
        except Exception as e:
            raise ValueError(f'Invalid max_redshift: {max_redshift} ({e})')
    if created_or_modified_after is not None:
        try:
            query_params['created_or_modified_after'] = arrow.get(
                created_or_modified_after
            ).datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
            statements.append(
                """
                (objs.created_at > :created_or_modified_after OR objs.modified > :created_or_modified_after)
                """
            )
        except Exception as e:
            raise ValueError(
                f'Invalid created_or_modified_after: {created_or_modified_after} ({e})'
            )

    # PHOTSTATS
    photstat_query = []
    if first_detected_date is not None:
        try:
            col = (
                'first_detected_mjd'
                if not exclude_forced_photometry
                else 'first_detected_no_forced_phot_mjd'
            )
            query_params['first_detected_date'] = Time(
                arrow.get(first_detected_date).datetime
            ).mjd
            photstat_query.append(f"""photstats.{col} >= :first_detected_date""")

        except Exception as e:
            raise ValueError(
                f'Invalid first_detected_date: {first_detected_date} ({e})'
            )
    if last_detected_date is not None:
        try:
            col = (
                'last_detected_mjd'
                if not exclude_forced_photometry
                else 'last_detected_no_forced_phot_mjd'
            )
            query_params['last_detected_date'] = Time(
                arrow.get(last_detected_date).datetime
            ).mjd
            photstat_query.append(f"""photstats.{col} <= :last_detected_date""")
        except Exception as e:
            raise ValueError(f'Invalid last_detected_date: {last_detected_date} ({e})')
    if number_of_detections is not None:
        try:
            col = (
                'num_det_global'
                if not exclude_forced_photometry
                else 'num_det_no_forced_phot_global'
            )
            query_params['number_of_detections'] = int(number_of_detections)
            photstat_query.append(f"""photstats.{col} >= :number_of_detections""")
        except Exception as e:
            raise ValueError(
                f'Invalid number_of_detections: {number_of_detections} ({e})'
            )
    if min_peak_magnitude is not None:
        try:
            query_params['min_peak_magnitude'] = float(min_peak_magnitude)
            photstat_query.append(
                """photstats.peak_mag_global <= :min_peak_magnitude"""
            )
        except Exception as e:
            raise ValueError(f'Invalid min_peak_magnitude: {min_peak_magnitude} ({e})')
    if max_peak_magnitude is not None:
        try:
            query_params['max_peak_magnitude'] = float(max_peak_magnitude)
            photstat_query.append(
                """photstats.peak_mag_global >= :max_peak_magnitude"""
            )
        except Exception as e:
            raise ValueError(f'Invalid max_peak_magnitude: {max_peak_magnitude} ({e})')
    if min_latest_magnitude is not None:
        try:
            query_params['min_latest_magnitude'] = float(min_latest_magnitude)
            photstat_query.append(
                """photstats.last_detected_mag <= :min_latest_magnitude"""
            )
        except Exception as e:
            raise ValueError(
                f'Invalid min_latest_magnitude: {min_latest_magnitude} ({e})'
            )
    if max_latest_magnitude is not None:
        try:
            query_params['max_latest_magnitude'] = float(max_latest_magnitude)
            photstat_query.append(
                """photstats.last_detected_mag >= :max_latest_magnitude"""
            )
        except Exception as e:
            raise ValueError(
                f'Invalid max_latest_magnitude: {max_latest_magnitude} ({e})'
            )
    if len(photstat_query) > 0:
        statements.append(
            f"""
            EXISTS (SELECT obj_id from photstats where photstats.obj_id=objs.id and {' AND '.join(photstat_query)})
            """
        )

    # CONE SEARCH
    if any([ra, dec, radius]):
        if not all([ra, dec, radius]):
            raise ValueError(f'Invalid ra, dec, radius: {ra}, {dec}, {radius}')
        try:
            ra, dec, radius = (
                float(ra),
                float(dec),
                float(radius),
            )
            statements.append(
                f"""
                {within(Obj.ra, Obj.dec, ra, dec, radius).compile(compile_kwargs={"literal_binds": True})}
                """
            )
            pass
        except Exception as e:
            raise ValueError(f'Invalid ra, dec, radius: {ra}, {dec}, {radius} ({e})')

    # SOURCES
    if include_requested:
        # if include requested, we are fine with active sources and requested sources
        statements.append(
            """
            (sources.active = true OR sources.requested = true)
            """
        )
    elif requested_only:
        # if requested only, we only want requested sources
        statements.append(
            """
            sources.requested = true
            """
        )
    else:
        # otherwise, we want active sources
        statements.append(
            """
            sources.active = true
            """
        )
    if saved_before is not None:
        try:
            query_params['saved_before'] = arrow.get(saved_before).datetime.strftime(
                '%Y-%m-%d %H:%M:%S.%f'
            )
            statements.append(
                """
                sources.saved_at < :saved_before
                """
            )
        except Exception as e:
            raise ValueError(f'Invalid saved_before: {saved_before} ({e})')
    if saved_after is not None:
        try:
            query_params['saved_after'] = arrow.get(saved_after).datetime.strftime(
                '%Y-%m-%d %H:%M:%S.%f'
            )
            statements.append(
                """
                sources.saved_at > :saved_after
                """
            )
        except Exception as e:
            raise ValueError(f'Invalid saved_after: {saved_after} ({e})')

    # CLASSIFICATIONS
    if classified:
        statements.append(
            f"""
            EXISTS (SELECT obj_id from classifications where classifications.obj_id=objs.id and classifications.ml=false {"and classifications.id in (select classification_id from group_classifications where group_id in :group_ids)" if len(group_ids) > 0 else ""})
            """
        )
    elif unclassified:
        statements.append(
            f"""
            NOT EXISTS (SELECT obj_id from classifications where classifications.obj_id=objs.id and classifications.ml=false {"and classifications.id in (select classification_id from group_classifications where group_id in :group_ids)" if len(group_ids) > 0 else ""})
            """
        )
    else:
        if classifications and len(classifications) > 0:
            statements.append(
                f"""
                EXISTS (SELECT obj_id from classifications where classifications.obj_id=objs.id and classifications.ml=false and classifications.classification in :classifications {"and classifications.id in (select classification_id from group_classifications where group_id in :group_ids)" if len(group_ids) > 0 else ""})
                """
            )
            query_params['classifications'] = array2sql(
                [str(c) for c in classifications]
            )
        if nonclassifications and len(nonclassifications) > 0:
            statements.append(
                f"""
                NOT EXISTS (SELECT obj_id from classifications where classifications.obj_id=objs.id and classifications.ml=false and classifications.classification in :nonclassifications {"and classifications.id in (select classification_id from group_classifications where group_id in :group_ids)" if len(group_ids) > 0 else ""})
                """
            )
            query_params['nonclassifications'] = array2sql(
                [str(c) for c in nonclassifications]
            )

    # SPECTRA
    if has_spectrum:
        statements.append(
            f"""
            EXISTS (SELECT obj_id from spectra where spectra.obj_id=objs.id {"and spectra.id in (select spectr_id from group_spectra where group_id in :group_ids)" if len(group_ids) > 0 else ""})
            """
        )
    elif has_no_spectrum:
        statements.append(
            f"""
            NOT EXISTS (SELECT obj_id from spectra where spectra.obj_id=objs.id {"and spectra.id in (select spectr_id from group_spectra where group_id in :group_ids)" if len(group_ids) > 0 else ""})
            """
        )
    if not has_no_spectrum:
        if has_spectrum_before is not None:
            try:
                query_params['has_spectrum_before'] = arrow.get(
                    has_spectrum_before
                ).datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
                statements.append(
                    f"""
                    EXISTS (SELECT obj_id from spectra where spectra.obj_id=objs.id and spectra.observed_at <= :has_spectrum_before {"and spectra.id in (select spectr_id from group_spectra where group_id in :group_ids)" if len(group_ids) > 0 else ""})
                    """
                )
            except Exception as e:
                raise ValueError(
                    f'Invalid has_spectrum_before: {has_spectrum_before} ({e})'
                )
        if has_spectrum_after is not None:
            try:
                query_params['has_spectrum_after'] = arrow.get(
                    has_spectrum_after
                ).datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
                statements.append(
                    f"""
                    EXISTS (SELECT obj_id from spectra where spectra.obj_id=objs.id and spectra.observed_at >= :has_spectrum_after {"and spectra.id in (select spectr_id from group_spectra where group_id in :group_ids)" if len(group_ids) > 0 else ""})
                    """
                )
            except Exception as e:
                raise ValueError(
                    f'Invalid has_spectrum_after: {has_spectrum_after} ({e})'
                )

    # FOLLOWUP REQUESTS
    if has_followup_request:
        # we already grabbed the allocation's ids in advance, so we can use them here
        try:
            query_params['allocation_ids'] = array2sql(allocation_ids)
            if followup_request_status is not None:
                query_params['has_followup_request_status'] = str(
                    followup_request_status
                ).strip()
                # if it contains the string, both lowercased, then we have a match
                statements.append(
                    f"""
                    EXISTS (SELECT obj_id from followuprequests where followuprequests.obj_id=objs.id and lower(followuprequests.status) LIKE '%' || lower(:has_followup_request_status) || '%' {"and followuprequests.allocation_id in :allocation_ids" if len(allocation_ids) > 0 else ""})
                    """
                )
            else:
                statements.append(
                    f"""
                    EXISTS (SELECT obj_id from followuprequests where followuprequests.obj_id=objs.id {"and followuprequests.allocation_id in :allocation_ids" if len(allocation_ids) > 0 else ""})
                    """
                )
        except Exception as e:
            raise ValueError(
                f'Invalid has_followup_request: {has_followup_request} ({e})'
            )

    # LISTINGS
    if list_name is not None:
        query_params['list_name'] = str(list_name)
        query_params['user_id'] = int(user_id)
        statements.append(
            """
            EXISTS (SELECT obj_id from listings where listings.obj_id=objs.id and listings.list_name = :list_name and listings.user_id = :user_id)
            """
        )

    # SOURCE LABELS
    if has_been_labelled:
        if current_user_labeller:
            query_params['current_user_labeller'] = int(user_id)
            statements.append(
                f"""
                EXISTS (SELECT obj_id from sourcelabels where sourcelabels.obj_id=objs.id and sourcelabels.labeller_id = :current_user_labeller {"and sourcelabels.group_id in :group_ids" if len(group_ids) > 0 else ""})
                """
            )
        else:
            statements.append(
                f"""
                EXISTS (SELECT obj_id from sourcelabels where sourcelabels.obj_id=objs.id {"and sourcelabels.group_id in :group_ids" if len(group_ids) > 0 else ""})
                """
            )
    elif has_not_been_labelled:
        if current_user_labeller:
            query_params['current_user_labeller'] = int(user_id)
            statements.append(
                f"""
                NOT EXISTS (SELECT obj_id from sourcelabels where sourcelabels.obj_id=objs.id and sourcelabels.labeller_id = :current_user_labeller {"and sourcelabels.group_id in :group_ids" if len(group_ids) > 0 else ""})
                """
            )
        else:
            statements.append(
                f"""
                NOT EXISTS (SELECT obj_id from sourcelabels where sourcelabels.obj_id=objs.id {"and sourcelabels.group_id in :group_ids " if len(group_ids) > 0 else ""})
                """
            )

    def create_annotation_query(
        annotations_filter,
        annotations_filter_origin,
        annotations_filter_before,
        annotations_filter_after,
        param_index,
        group_ids,
    ):
        stmts = []
        params = {}
        if annotations_filter_origin is not None:
            params[f'annotations_filter_origin_{param_index}'] = array2sql(
                annotations_filter_origin
            )
            stmts.append(
                f"""
                lower(annotations.origin) in :annotations_filter_origin_{param_index}
                """
            )
        if annotations_filter_before is not None:
            try:
                params[f'annotations_filter_before_{param_index}'] = arrow.get(
                    annotations_filter_before
                ).datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
                stmts.append(
                    f"""
                    annotations.created_at <= :annotations_filter_before_{param_index}
                    """
                )
            except Exception as e:
                raise ValueError(
                    f'Invalid annotations_filter_before: {annotations_filter_before} ({e})'
                )
        if annotations_filter_after is not None:
            try:
                params[f'annotations_filter_after_{param_index}'] = arrow.get(
                    annotations_filter_after
                ).datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
                stmts.append(
                    f"""
                    annotations.created_at >= :annotations_filter_after_{param_index}
                    """
                )
            except Exception as e:
                raise ValueError(
                    f'Invalid annotations_filter_after: {annotations_filter_after} ({e})'
                )
        if annotations_filter is not None:
            if len(annotations_filter) == 3:
                value = annotations_filter[1].strip()
                try:
                    value = float(value)
                except ValueError as e:
                    raise ValueError(f"Invalid annotation filter value: {e}")
                op = annotations_filter[2].strip()
                op_options = ["lt", "le", "eq", "ne", "ge", "gt"]
                if op not in op_options:
                    raise ValueError(f"Invalid operator: {op}")
                # find the equivalent postgres operator
                if op == "lt":
                    comp_function = "<"
                elif op == "le":
                    comp_function = "<="
                elif op == "eq":
                    comp_function = "="
                elif op == "ne":
                    comp_function = "!="
                elif op == "ge":
                    comp_function = ">="
                elif op == "gt":
                    comp_function = ">"

                params[f'annotations_filter_name_{param_index}'] = annotations_filter[
                    0
                ].strip()
                print(
                    f'annotations_filter_name_{param_index}: {annotations_filter[0].strip()}'
                )
                params[f'annotations_filter_value_{param_index}'] = value
                print(f'annotations_filter_value_{param_index}: {value}')
                print(f'comp_function: {comp_function}')
                # the query will apply the operator to compare the value
                # in annotation.data[annotations_filter_name] to the value
                # we'll need to cast the value to JSONB to do the comparison
                stmts.append(
                    f"""
                    ((annotations.data ->> :annotations_filter_name_{param_index})::float {comp_function} (:annotations_filter_value_{param_index})::float)
                    """
                )
            else:
                # else we just want to check if the annotation exists (IS NOT NULL)
                params[f'annotations_filter_name_{param_index}'] = annotations_filter[
                    0
                ].strip()
                stmts.append(
                    f"""
                    (annotations.data ->> :annotations_filter_name_{param_index} IS NOT NULL)
                    """
                )
        if len(stmts) > 0:
            return (
                f"""
            EXISTS (SELECT obj_id from annotations where annotations.obj_id=objs.id and {' AND '.join(stmts)} {"and annotations.id in (select annotation_id from group_annotations where group_id in :group_ids)" if len(group_ids) > 0 else ""})
            """,
                params,
            )

        return None, None

    # ANNOTATIONS
    if (
        annotations_filter is not None
        or annotations_filter_origin is not None
        or annotations_filter_before is not None
        or annotations_filter_after is not None
    ):
        if annotations_filter_origin is not None:
            if (
                isinstance(annotations_filter_origin, str)
                and "," in annotations_filter_origin
            ):
                annotations_filter_origin = [
                    a.strip() for a in annotations_filter_origin.split(",")
                ]
            elif isinstance(annotations_filter_origin, str):
                annotations_filter_origin = [annotations_filter_origin]

        if annotations_filter is not None:
            if isinstance(annotations_filter, str) and "," in annotations_filter:
                annotations_filter = [a.strip() for a in annotations_filter.split(",")]
            elif isinstance(annotations_filter, str):
                annotations_filter = [annotations_filter]
            for i, ann_filter in enumerate(annotations_filter):
                ann_split = ann_filter.split(":")
                if not (len(ann_split) == 1 or len(ann_split) == 3):
                    raise ValueError(
                        "Invalid annotationsFilter value -- annotation filter must have 1 or 3 values"
                    )

                annotations_query, annotations_query_params = create_annotation_query(
                    ann_split,
                    annotations_filter_origin,
                    annotations_filter_before,
                    annotations_filter_after,
                    i,
                    group_ids,
                )
                if annotations_query is not None:
                    statements.append(annotations_query)
                    query_params = {**query_params, **annotations_query_params}
        else:
            annotations_query, annotations_query_params = create_annotation_query(
                None,
                annotations_filter_origin,
                annotations_filter_before,
                annotations_filter_after,
                0,
                group_ids,
            )
            if annotations_query is not None:
                statements.append(annotations_query)
                query_params = {**query_params, **annotations_query_params}

    # COMMENTS
    comments_query = []
    if comments_filter is not None:
        if isinstance(comments_filter, str) and "," in comments_filter:
            comments_filter = [c.strip() for c in comments_filter.split(",")]
        elif isinstance(comments_filter, str):
            comments_filter = [comments_filter]
        query_params['comments_filter'] = array2sql(comments_filter)
        comments_query.append("""comments.text LIKE ANY (array[:comments_filter])""")
    if comments_filter_before is not None:
        try:
            query_params['comments_filter_before'] = arrow.get(
                comments_filter_before
            ).datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
            comments_query.append("""comments.created_at <= :comments_filter_before""")
        except Exception as e:
            raise ValueError(
                f'Invalid comments_filter_before: {comments_filter_before} ({e})'
            )
    if comments_filter_after is not None:
        try:
            query_params['comments_filter_after'] = arrow.get(
                comments_filter_after
            ).datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
            comments_query.append("""comments.created_at >= :comments_filter_after""")
        except Exception as e:
            raise ValueError(
                f'Invalid comments_filter_after: {comments_filter_after} ({e})'
            )
    if comments_filter_author is not None:
        try:
            query_params['comments_filter_author'] = int(comments_filter_author)
            comments_query.append("""comments.author_id = :comments_filter_author""")
        except Exception as e:
            raise ValueError(
                f'Invalid comments_filter_author: {comments_filter_author} ({e})'
            )
    if len(comments_query) > 0:
        statements.append(
            f"""
            EXISTS (SELECT obj_id from comments where comments.obj_id=objs.id and {' AND '.join(comments_query)} {"and comments.id in (select comment_id from group_comments where group_id in :group_ids)" if len(group_ids) > 0 else ""})
            """
        )

    # GCN
    if localization_dateobs is not None:
        try:
            localization_dateobs = arrow.get(localization_dateobs).datetime
            localization_cumprob = float(localization_cumprob)
            localization_id, partition = get_localization(
                localization_dateobs,
                localization_name,
                session,
            )
            # this is twice as fast as if we ran each query (the localization tiles query,
            # and its overall with the sources) separately.
            # we used caching for that in prod, but now that we have partitions, we can do it this way
            localization_query = f"""EXISTS (
                SELECT lt.id
                FROM (
                    SELECT  {partition}.id,
                            {partition}.healpix,
                            {partition}.probdensity,
                            SUM({partition}.probdensity *
                                (upper({partition}.healpix) - lower({partition}.healpix)) * 3.6331963520923245e-18
                            ) OVER (ORDER BY {partition}.probdensity DESC) AS cum_prob
                    FROM {partition}
                    WHERE {partition}.localization_id = {localization_id}
                ) AS lt
                WHERE lt.cum_prob <= {localization_cumprob} and lt.healpix @> objs.healpix
                ORDER BY lt.probdensity DESC
                )"""
            if localization_reject_sources:
                # reject the sources if there is an entry in the sourcesconfirmedingcns table
                # with that dateobs, and with confirmed = False
                localization_query += f""" AND NOT EXISTS (
                    SELECT obj_id
                    FROM sourcesconfirmedingcns
                    WHERE sourcesconfirmedingcns.obj_id = objs.id
                    AND sourcesconfirmedingcns.dateobs = '{localization_dateobs.strftime('%Y-%m-%d %H:%M:%S')}'
                    AND sourcesconfirmedingcns.confirmed = false
                )"""
            if include_sources_in_gcn:
                # include sourcesconfirmedingcns with confirmed != False
                # or reversing that condition, NOT EXISTS with confirmed = False
                # we can do this because there is a unique index on obj_id and dateobs
                # as a source can't be confirmed and rejected in an event at the same time
                localization_query = f"""(({localization_query}) OR NOT EXISTS (
                    SELECT obj_id
                    FROM sourcesconfirmedingcns
                    WHERE sourcesconfirmedingcns.obj_id = objs.id
                    AND sourcesconfirmedingcns.dateobs = '{localization_dateobs.strftime('%Y-%m-%d %H:%M:%S')}'
                    AND sourcesconfirmedingcns.confirmed = false
                ))"""
            statements.append(localization_query)
        except Exception as e:
            raise ValueError(f'Invalid localization query parameters ({e})')

    # SPATIAL CATALOGS
    if spatial_catalog_name is not None:
        if spatial_catalog_entry_name is None:
            raise ValueError(
                'must provide spatial_catalog_entry_name if using spatial_catalog_name'
            )
        try:
            # first try to find the catalog
            entry_stmt = """
            SELECT id
            FROM spatial_catalog_entries
            WHERE lower(entry_name) = :spatial_catalog_entry_name
            AND catalog_id in (
                SELECT id
                FROM spatial_catalogs
                WHERE lower(catalog_name) = :spatial_catalog_name
            )
            """
            entry_id = session.execute(
                text(entry_stmt).bindparams(
                    **{
                        'spatial_catalog_entry_name': str(spatial_catalog_entry_name)
                        .strip()
                        .lower(),
                        'spatial_catalog_name': str(spatial_catalog_name)
                        .strip()
                        .lower(),
                    }
                )
            )
            if entry_id is None:
                raise ValueError('spatial catalog entry not found')

            query_params['spatial_catalog_entry_name'] = (
                str(spatial_catalog_entry_name).strip().lower()
            )

            # this query will be very similar to the localization query, as the catalog entries are made of tiles
            statements.append(
                """
                EXISTS (
                    SELECT id
                    FROM spatial_catalog_entriess
                    WHERE spatial_catalog_entriess.entry_name = :spatial_catalog_entry_name
                    AND spatial_catalog_entriess.healpix @> objs.healpix
                )
                """
            )
        except Exception as e:
            raise ValueError(f'Invalid spatial catalog query parameters ({e})')

    # ADD QUERY STATEMENTS
    statement = f"""SELECT objs.id AS id, MAX(sources.saved_at) AS most_recent_saved_at
        FROM objs INNER JOIN sources ON objs.id = sources.obj_id
        WHERE {' AND '.join(statements)}
        GROUP BY objs.id
    """

    # SORTING
    if sort_by in NULL_FIELDS:
        statement += f"""ORDER BY {SORT_BY[sort_by]} {sort_order.upper()} NULLS LAST"""
    else:
        statement += f"""ORDER BY {SORT_BY[sort_by]} {sort_order.upper()}"""

    statement = (
        text(statement)
        .bindparams(**query_params)
        .columns(id=sa.String, most_recent_saved_at=sa.DateTime)
    )
    if verbose:
        log(f'Params:\n{query_params}')
        log(f'Query:\n{statement}')

    startTime = time.time()

    connection = DBSession().connection()
    results = connection.execute(statement)
    all_obj_ids = [r[0] for r in results]
    if len(all_obj_ids) != len(set(all_obj_ids)):
        raise ValueError(
            f'Duplicate obj_ids in query results, query is incorrect: {all_obj_ids}'
        )

    endTime = time.time()
    if verbose:
        log(
            f'1. MAIN Query took {endTime - startTime} seconds, returned {len(all_obj_ids)} results.'
        )

    data = {}
    start, end = (page - 1) * nbPerPage, page * nbPerPage
    objs, total_matches = [], len(all_obj_ids)
    if total_matches > 0 and start <= total_matches:
        if end > total_matches:
            end = total_matches

        if save_summary:
            raise NotImplementedError('save_summary not implemented yet')
        else:
            startTime = time.time()

            obj_ids = all_obj_ids[start:end]
            objs = session.query(Obj).filter(Obj.id.in_(obj_ids)).distinct().all()
            # keep the original order
            objs = sorted(objs, key=lambda obj: obj_ids.index(obj.id))
            objs = [
                {
                    **obj.to_dict(),
                    'groups': [],
                    'host': None,
                    'host_offset': None,
                }
                for obj in objs
            ]  # convert to dict

            endTime = time.time()
            if verbose:
                log(f'2. Objs Query took {endTime - startTime} seconds.')

            # SOURCES
            startTime = time.time()

            sources = (
                session.scalars(Source.select(user).where(Source.obj_id.in_(obj_ids)))
                .unique()
                .all()
            )
            sources = sorted(
                (s.to_dict() for s in sources), key=lambda s: s['created_at']
            )

            endTime = time.time()
            if verbose:
                log(f'3. Sources Query took {endTime - startTime} seconds.')

            # REFORMAT SOURCES (SAVE INFO)
            start = time.time()
            source_group_ids, source_user_ids = [], []
            for source in sources:
                source_group_ids.append(source['group_id']), source_user_ids.append(
                    source['saved_by_id']
                )

            source_group_ids, source_user_ids = set(source_group_ids), set(
                source_user_ids
            )

            groups = (
                session.query(Group)
                .filter(Group.id.in_(source_group_ids))
                .distinct()
                .all()
            )
            groups = {group.id: group.to_dict() for group in groups}

            users = (
                session.query(User)
                .filter(User.id.in_(source_user_ids))
                .distinct()
                .all()
            )
            users = {user.id: user.to_dict() for user in users}

            # for each obj, add a 'groups' key with the groups tho which it has been saved as a source
            for source in sources:
                obj = next((obj for obj in objs if obj['id'] == source['obj_id']), None)
                obj['groups'].append(
                    {
                        **groups[source['group_id']],
                        "active": source['active'],
                        "requested": source['requested'],
                        "saved_at": source['saved_at'],
                        "saved_by": users[source['saved_by_id']],
                    }
                )

            endTime = time.time()
            if verbose:
                log(f'4. Sources Refomatting took {endTime - startTime} seconds.')

            startTime = time.time()
            obj_coords = np.array([[obj['ra'], obj['dec']] for obj in objs])
            obj_coords_gal = radec2lb(obj_coords[:, 0], obj_coords[:, 1])
            for i in range(len(objs)):
                objs[i]['gal_lon'] = obj_coords_gal[0][i]
                objs[i]['gal_lat'] = obj_coords_gal[1][i]
                redshift = objs[i]['redshift']
                luminosity_distance = get_luminosity_distance(objs[i])
                objs[i]['luminosity_distance'] = luminosity_distance
                objs[i]['dm'] = (
                    5.0 * np.log10((luminosity_distance * u.Mpc) / (10 * u.pc)).value
                    if luminosity_distance
                    else None
                )
                if luminosity_distance:
                    if redshift and redshift * HOOG_REDSHIFT_A > HOOG_REDSHIFT_B:
                        objs[i]['angular_diameter_distance'] = (
                            luminosity_distance / (1 + redshift) ** 2
                        )
                    else:
                        objs[i]['angular_diameter_distance'] = luminosity_distance
                else:
                    objs[i]['angular_diameter_distance'] = None

            endTime = time.time()
            if verbose:
                log(f'5. Various obj computations took {endTime - startTime} seconds.')

            if include_thumbnails and not remove_nested:
                startTime = time.time()
                thumbnails = (
                    session.scalars(
                        Thumbnail.select(user).where(Thumbnail.obj_id.in_(obj_ids))
                    )
                    .unique()
                    .all()
                )
                thumbnails = sorted(
                    (t.to_dict() for t in thumbnails), key=lambda t: t['created_at']
                )
                print(thumbnails[0])
                for obj in objs:
                    obj['thumbnails'] = [
                        t for t in thumbnails if t['obj_id'] == obj['id']
                    ]

                endTime = time.time()
                if verbose:
                    log(f'6. Thumbnails Query took {endTime - startTime} seconds.')

            if include_detection_stats:
                # PHOTSTATS
                startTime = time.time()

                photstats = (
                    session.scalars(
                        PhotStat.select(user).where(PhotStat.obj_id.in_(obj_ids))
                    )
                    .unique()
                    .all()
                )
                photstats = sorted(
                    (p.to_dict() for p in photstats), key=lambda p: p['created_at']
                )
                for obj in objs:
                    obj['photstats'] = [
                        p for p in photstats if p['obj_id'] == obj['id']
                    ]

                endTime = time.time()
                if verbose:
                    log(f'7. Photstats Query took {endTime - startTime} seconds.')

            if not remove_nested:
                # CLASSIFICATIONS
                startTime = time.time()

                classifications = (
                    session.scalars(
                        Classification.select(user).where(
                            Classification.obj_id.in_(obj_ids)
                        )
                    )
                    .unique()
                    .all()
                )
                classifications = [
                    {
                        **c.to_dict(),
                        'groups': [],  # TODO
                        'votes': [],  # TODO
                    }
                    for c in classifications
                ]
                classifications = sorted(classifications, key=lambda c: c['created_at'])
                for obj in objs:
                    obj['classifications'] = [
                        c for c in classifications if c['obj_id'] == obj['id']
                    ]

                endTime = time.time()
                if verbose:
                    log(f'8. Classifications Query took {endTime - startTime} seconds.')

            if not remove_nested or include_period_exists:
                # ANNOTATIONS
                startTime = time.time()

                annotations = (
                    session.scalars(
                        Annotation.select(user).where(Annotation.obj_id.in_(obj_ids))
                    )
                    .unique()
                    .all()
                )
                annotations = sorted(
                    (a.to_dict() for a in annotations), key=lambda a: a['created_at']
                )

                for obj in objs:
                    obj['annotations'] = [
                        a for a in annotations if a['obj_id'] == obj['id']
                    ]

                endTime = time.time()
                if verbose:
                    log(f'9. Annotations Query took {endTime - startTime} seconds.')

            if include_hosts:
                # HOST GALAXY
                startTime = time.time()
                host_ids = list(
                    {obj['host_id'] for obj in objs if obj['host_id'] is not None}
                )
                if len(host_ids) > 0:
                    hosts = (
                        session.query(Galaxy)
                        .filter(Galaxy.id.in_(host_ids))
                        .distinct()
                        .all()
                    )
                    hosts = {host.id: host.to_dict() for host in hosts}

                    objs_with_host = [
                        (i, obj['host_id'], (obj['ra'], obj['dec']))
                        for i, obj in enumerate(objs)
                        if obj['host_id'] is not None
                    ]
                    objs_with_host_coords = np.array([obj[2] for obj in objs_with_host])

                    hosts = [hosts[obj[1]] for obj in objs_with_host]
                    hosts_coords = np.array(
                        [[host['ra'], host['dec']] for host in hosts]
                    )

                    # now we can compute the offset for all of them at once
                    offsets = (
                        great_circle_distance(
                            objs_with_host_coords[:, 0],
                            objs_with_host_coords[:, 1],
                            hosts_coords[:, 0],
                            hosts_coords[:, 1],
                        )
                        * 3600
                    )  # in arcsec
                    for i, offset in enumerate(offsets):
                        objs[objs_with_host[i][0]]['host'] = hosts[i]
                        objs[objs_with_host[i][0]]['host_offset'] = offset

                endTime = time.time()
                if verbose:
                    log(
                        f'10. Hosts Query (+offset) took {endTime - startTime} seconds.'
                    )

            if include_spectrum_exists:
                startTime = time.time()
                if has_spectrum:
                    # if we already filtered for sources with spectra, we can just set the flag to True
                    for obj in objs:
                        obj['spectrum_exists'] = True
                else:
                    stmt = """
                    SELECT DISTINCT obj_id
                    FROM spectra
                    WHERE obj_id IN :obj_ids
                    """
                    spectrum_exists = session.execute(
                        text(stmt).bindparams(obj_ids=array2sql(obj_ids))
                    )
                    spectrum_exists = [r[0] for r in spectrum_exists]
                    for obj in objs:
                        obj['spectrum_exists'] = obj['id'] in spectrum_exists

                endTime = time.time()
                if verbose:
                    log(
                        f'11. Spectrum Exists Query took {endTime - startTime} seconds.'
                    )

            if include_comment_exists:
                startTime = time.time()
                if (
                    comments_filter is not None
                    or comments_filter_before is not None
                    or comments_filter_after is not None
                    or comments_filter_author is not None
                ):
                    # if we already filtered for sources with comments, we can just set the flag to True
                    for obj in objs:
                        obj['comment_exists'] = True
                else:
                    stmt = """
                    SELECT DISTINCT obj_id
                    FROM comments
                    WHERE obj_id IN :obj_ids
                    """
                    comment_exists = session.execute(
                        text(stmt).bindparams(obj_ids=array2sql(obj_ids))
                    )
                    comment_exists = [r[0] for r in comment_exists]
                    for obj in objs:
                        obj['comment_exists'] = obj['id'] in comment_exists

                endTime = time.time()
                if verbose:
                    log(f'12. Comment Exists Query took {endTime - startTime} seconds.')

            if include_photometry_exists:
                startTime = time.time()

                # it seemed that for num_per_page that are not too big, the UNION query was faster
                # TODO: verify that
                # if len(obj_ids) <= 1000:
                #     print('using UNION')
                # stmts = [
                #     f"""
                #     SELECT DISTINCT obj_id
                #     FROM photometry
                #     WHERE obj_id = :obj_{i}
                #     """
                #     for i in range(len(obj_ids))
                # ]
                # stmt = ' UNION '.join(stmts)
                # photometry_exists = session.execute(
                #     text(stmt).bindparams(**{f'obj_{i}': obj_ids[i] for i in range(len(obj_ids))})
                # )
                # else:
                # print('using WHERE IN')
                stmt = """
                SELECT DISTINCT obj_id
                FROM photometry
                WHERE obj_id IN :obj_ids
                """
                photometry_exists = session.execute(
                    text(stmt).bindparams(obj_ids=array2sql(obj_ids))
                )
                photometry_exists = [r[0] for r in photometry_exists]
                for obj in objs:
                    obj['photometry_exists'] = obj['id'] in photometry_exists
                objs_missing_photometry = [
                    obj['id']
                    for i, obj in enumerate(objs)
                    if not obj['photometry_exists']
                ]
                if len(objs_missing_photometry) > 0:
                    # if it doesn't exist, check if it has a photometric series
                    stmt = """
                        SELECT DISTINCT obj_id
                        FROM photometric_series
                        WHERE obj_id IN :obj_ids
                    """
                    photometric_series_exists = session.execute(
                        text(stmt).bindparams(
                            obj_ids=array2sql(objs_missing_photometry)
                        )
                    )
                    photometric_series_exists = [
                        r[0] for r in photometric_series_exists
                    ]
                    for obj in objs:
                        obj['photometry_exists'] = (
                            obj['photometry_exists']
                            or obj['id'] in photometric_series_exists
                        )

                endTime = time.time()
                if verbose:
                    log(
                        f'13. Photometry Exists Query took {endTime - startTime} seconds.'
                    )

            if include_period_exists:
                startTime = time.time()

                # the period, like the color_mag, is computed from the annotations
                # we already have the annotations, so we can compute the period for each obj
                for obj in objs:
                    obj['period'] = get_period_exists(obj['annotations'])

                endTime = time.time()
                if remove_nested:
                    # if we don't need the annotations anymore, we can remove them
                    for obj in objs:
                        del obj['annotations']
                if verbose:
                    log(f'14. Period Exists Query took {endTime - startTime} seconds.')

            if include_comments:
                startTime = time.time()

                comments = (
                    session.scalars(
                        Comment.select(user).where(Comment.obj_id.in_(obj_ids))
                    )
                    .unique()
                    .all()
                )
                comments = [c.to_dict() for c in comments]
                comments = sorted(comments, key=lambda c: c['created_at'])
                if len(comments) > 0:
                    for obj in objs:
                        obj['comments'] = [
                            {
                                k: v
                                for k, v in comment.items()
                                if k != "attachment_bytes"
                            }
                            for comment in [
                                c for c in comments if c['obj_id'] == obj['id']
                            ]
                        ]

                endTime = time.time()
                if verbose:
                    log(f'15. Comments Query took {endTime - startTime} seconds.')

            if include_labellers:
                startTime = time.time()

                labellers = (
                    session.scalars(
                        SourceLabel.select(user).where(SourceLabel.obj_id.in_(obj_ids))
                    )
                    .unique()
                    .all()
                )
                labellers = sorted(
                    (lab.to_dict() for lab in labellers),
                    key=lambda lab: lab['created_at'],
                )
                for obj in objs:
                    obj['labellers'] = [
                        lab for lab in labellers if lab['obj_id'] == obj['id']
                    ]

                endTime = time.time()
                if verbose:
                    log(f'16. Labellers Query took {endTime - startTime} seconds.')

            if include_color_mag:
                startTime = time.time()
                for obj in objs:
                    obj['color_mag'] = get_color_mag(obj['annotations'])

                endTime = time.time()
                if verbose:
                    log(f'17. Color Mag Query took {endTime - startTime} seconds.')

        data = {'totalMatches': total_matches, 'sources': objs}

        if includeGeoJSON:
            startTime = time.time()
            features = []
            for source in data["sources"]:
                point = Point((source["ra"], source["dec"]))
                aliases = [alias for alias in (source["alias"] or []) if alias]
                source_name = ", ".join(
                    [
                        source["id"],
                    ]
                    + aliases
                )

                features.append(
                    Feature(
                        geometry=point,
                        properties={
                            "name": source_name,
                            "url": f"/source/{source['id']}",
                        },
                    )
                )
            data["geojson"] = {
                "type": "FeatureCollection",
                "features": features,
            }

    endMethodTime = time.time()
    if verbose:
        log(f'TOTAL took {endMethodTime - startMethodTime} seconds.')

    return data


def benchmark(filters, user_id, group_ids, page, nbPerPage):
    combinations = []
    for sort_by in SORT_BY:
        for sort_order in ['asc', 'desc']:
            combinations.append((sort_by, sort_order))

    results = []

    # then, run each combination 10 times and take the average
    for sort_by, sort_order in combinations:
        totalTime = 0
        for i in tqdm(
            range(10),
            desc=f'{str(filters)}, sort_by={sort_by}, sort_order={sort_order}',
        ):
            startTime = time.time()
            get_sources(
                user_id=user_id,
                session=DBSession(),
                group_ids=group_ids,
                page_number=page,
                num_per_page=nbPerPage,
                sort_by=sort_by,
                sort_order=sort_order,
                verbose=False,
            )
            endTime = time.time()
            totalTime += endTime - startTime
        avgTime = totalTime / 10
        results.append((sort_by, sort_order, avgTime))

    print()
    # summarize the results in a table
    print(f'{"sort_by":<10}{"sort_order":<10}{"avgTime":<10}')
    for sort_by, sort_order, avgTime in results:
        print(f'{sort_by:<10}{sort_order:<10}{avgTime:<10}')


if __name__ == '__main__':
    user_id = 1260
    group_ids = []
    page = 1
    nbPerPage = 500
    filters = {
        # 'has_spectrum': True,
        # 'has_no_classifications': True,
        # 'has_no_classifications': ["Type II"],
        # 'has_no_tnsname': True,
        # 'saved_after': '2021-01-01',
        # 'saved_before': '2023-09-01',
        # 'created_or_modified_after': '2023-01-01',
        # 'min_redshift': '0.1',
        # 'max_redshift': '2.0',
        # 'has_followup_request': True,
        # 'has_followup_request_status': 'complete',
        # 'radius': 10,
        # 'ra': 50.0,
        # 'dec': 50.0,
        # 'first_detected_date': '2021-01-01',
        # 'last_detected_date': '2023-09-01',
        # 'number_of_detections': 15,
        # 'min_peak_magnitude': 18,
        # 'sourceID': 'ZTF23aauekqf',
        # 'rejectedSourceIDs': ['ZTF23aauekqf'],
        # 'list_name': 'favorites',
        # 'simbad_class': 'Ia',
        # 'has_been_labelled': True,
        # 'current_user_labeller': True,
        # 'comments_filter': ["blue featureless"],
        # 'comments_filter_author': 23,
        # 'localization_dateobs': '2023-08-08T04:03:46',
        # 'first_detected_date': '2023-08-08T04:03:46',
        # 'last_detected_date': '2023-08-15T04:03:46',
        # 'number_of_detections': 2,
        # 'exclude_forced_photometry': True,
        # 'localization_reject_sources': True,
        # 'include_sources_in_gcn': True,
        # 'spatial_catalog_name': '4FGL-DR2',
        # 'spatial_catalog_entry_name': '4FGL-J0000.3-7355',
    }
    sort_by = 'saved_at'
    sort_order = 'desc'

    # run just one query first to make sure it works
    data = get_sources(
        user_id=user_id,
        session=DBSession(),
        # has_spectrum=True,
        # unclassified=True,
        annotations_filter=['acai_h:0.97284:eq'],
        annotations_filter_origin='au-caltech:hosted',
        # has_no_tns_name=True,
        include_thumbnails=True,
        include_hosts=True,
        include_comments=True,
        include_labellers=True,
        include_color_mag=True,
        include_detection_stats=True,
        include_comment_exists=True,
        include_photometry_exists=True,
        include_spectrum_exists=True,
        include_period_exists=True,
        group_ids=group_ids,
        page_number=page,
        num_per_page=nbPerPage,
        sort_by=sort_by,
        sort_order=sort_order,
        verbose=True,
    )
    print()
    if len(data['sources']) < 10:
        print([obj['id'] for obj in data['sources']])
    log(
        f'Query returned {data["totalMatches"]} matches. Limited to {len(data["sources"])} results.'
    )

    # benchmark(filters, user_id, group_ids, page, nbPerPage)

# TODOs:
# - take taxonomy into account when filtering on classifications but with names (not just booleans)
# - annotations_filter, annotations_filter_origin
