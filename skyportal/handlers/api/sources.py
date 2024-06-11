import re
import time

import arrow
import astropy.units as u
import numpy as np
import sqlalchemy as sa
from astropy.time import Time
from conesearch_alchemy.math import cosd, sind
from geojson import Feature, Point
from sqlalchemy.sql import and_, text, bindparam

from baselayer.app.env import load_env
from baselayer.log import make_log
from skyportal.models import (
    Allocation,
    Annotation,
    Classification,
    Comment,
    Galaxy,
    Group,
    Localization,
    LocalizationTile,
    Obj,
    PhotStat,
    Source,
    SourceLabel,
    Thumbnail,
    User,
    cosmo,
)

_, cfg = load_env()
log = make_log('api/sources')
log_verbose = make_log('sources_verbose')

DEFAULT_SOURCES_PER_PAGE = 1000

SORT_BY = {
    'saved_at': 'most_recent_saved_at',  # default
    'id': 'objs.id',
    'alias': 'objs.alias',
    'origin': 'objs.origin',
    'ra': 'objs.ra',
    'dec': 'objs.dec',
    'redshift': 'objs.redshift',
    'gcn_status': None,
    'favorites': None,
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

OPERATORS = {
    'eq': '=',
    'ne': '!=',
    'gt': '>',
    'ge': '>=',
    'lt': '<',
    'le': '<=',
}

tns_name_with_designation_pattern = re.compile(
    r'(at|sn)\d{1,4}[a-zA-Z]*', re.IGNORECASE
)
tns_name_no_designation_pattern = re.compile(r'^\d{1,4}[a-zA-Z]*', re.IGNORECASE)


def array2sql(array: list, type=sa.String, prefix='array'):
    binparam_names = [f'{prefix}_{i}' for i in range(len(array))]
    query_str = f"({','.join(f':{name}' for name in binparam_names)})"
    bindparams = [
        bindparam(name, value=value, type_=type)
        for name, value in zip(binparam_names, array)
    ]
    return query_str, bindparams


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


def create_annotation_query(
    annotations_filter,
    annotations_filter_origin,
    annotations_filter_before,
    annotations_filter_after,
    param_index,
    is_admin,
):
    stmts = []
    params = []
    if annotations_filter_origin is not None:
        query_str, bindparams = array2sql(
            annotations_filter_origin,
            type=sa.String,
            prefix=f'annotations_filter_origin_{param_index}',
        )
        params.extend(bindparams)
        stmts.append(
            f"""
            lower(annotations.origin) in {query_str}
            """
        )
    if annotations_filter_before is not None:
        try:
            params.append(
                bindparam(
                    f'annotations_filter_before_{param_index}',
                    value=arrow.get(annotations_filter_before).datetime.strftime(
                        '%Y-%m-%d %H:%M:%S.%f'
                    ),
                    type_=sa.DateTime,
                )
            )
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
            params.append(
                bindparam(
                    f'annotations_filter_after_{param_index}',
                    value=arrow.get(annotations_filter_after).datetime.strftime(
                        '%Y-%m-%d %H:%M:%S.%f'
                    ),
                    type_=sa.DateTime,
                )
            )
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
            if op not in OPERATORS.keys():
                raise ValueError(f"Invalid operator: {op}")
            # find the equivalent postgres operator
            comp_function = OPERATORS.get(op)

            params.append(
                bindparam(
                    f'annotations_filter_name_{param_index}',
                    value=annotations_filter[0].strip(),
                    type_=sa.String,
                )
            )
            params.append(
                bindparam(
                    f'annotations_filter_value_{param_index}',
                    value=value,
                    type_=sa.Float,
                )
            )
            stmts.append(
                f"""
                ((annotations.data ->> :annotations_filter_name_{param_index})::float {comp_function} (:annotations_filter_value_{param_index})::float)
                """
            )
        else:
            # else we just want to check if the annotation exists (IS NOT NULL)
            params.append(
                bindparam(
                    f'annotations_filter_name_{param_index}',
                    value=annotations_filter[0].strip(),
                    type_=sa.String,
                )
            )
            stmts.append(
                f"""
                (annotations.data ->> :annotations_filter_name_{param_index} IS NOT NULL)
                """
            )
    if len(stmts) > 0:
        return (
            f"""
        EXISTS (SELECT obj_id from annotations where annotations.obj_id=objs.id and {' AND '.join(stmts)} {"and annotations.id in (select annotation_id from group_annotations where group_id in :accessible_group_ids)" if not is_admin else ""})
        """,
            params,
        )

    return None, None


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
    log_verbose(f"get_localization took {endTime - startTime} seconds")

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


async def get_sources(
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
    require_detections=False,
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
    sort_by=None,
    sort_order=None,
    group_ids=[],
    user_accessible_group_ids=None,
    save_summary=False,
    total_matches=None,
    includeGeoJSON=False,
    use_cache=False,
    query_id=None,
    verbose=False,
):
    try:
        page_number = int(page_number)
        num_per_page = int(num_per_page)
    except Exception as e:
        log(f'Invalid pagination arguments: {e}')
        raise ValueError(f'Invalid pagination arguments: {e}')

    try:
        # it takes one query argument, which is the query type
        # and the group_ids to query
        startMethodTime = time.time()

        if user_id is None:
            raise ValueError('No user_id provided.')

        if sort_order in [None, "", "none"]:
            sort_order = 'desc'
        elif sort_order.lower() not in SORT_ORDER:
            raise ValueError(f'Invalid sort_order: {sort_order}')

        if sort_by in [None, "", "none"]:
            if localization_dateobs is not None:
                sort_by = 'gcn_status'
            else:
                sort_by = 'saved_at'
        elif sort_by not in SORT_BY:
            raise ValueError(f'Invalid sort_by: {sort_by}')

        if sort_by == 'gcn_status' and localization_dateobs is None:
            raise ValueError('Cannot sort by gcn_status without localization_dateobs')
        elif sort_by == 'favorites':
            # we reverse the condition here, so we can use bool_and later on
            sort_order = "desc" if sort_order.lower() == "asc" else "asc"

        user = session.scalar(sa.select(User).where(User.id == user_id))
        if user is None:
            raise ValueError(f'Invalid user_id: {user_id}')
        is_admin = user.is_admin
        if user_accessible_group_ids is None:
            user_accessible_group_ids = [g.id for g in user.accessible_groups]

        if group_ids is None:
            group_ids = []
        if len(group_ids) == 0 and not is_admin:
            group_ids = user_accessible_group_ids
        elif (
            not set(group_ids).issubset(set(user_accessible_group_ids)) and not is_admin
        ):
            raise ValueError('Selected group(s) not all accessible to user.')

        allocation_ids = []
        if not is_admin and len(group_ids) > 0:
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

        groups_query_str, groups_bindparams = array2sql(
            group_ids, type=sa.Integer, prefix='group'
        )
        accessible_groups_query_str, accessible_groups_bindparams = array2sql(
            user_accessible_group_ids, type=sa.Integer, prefix='accessible_groups'
        )
        allocation_query_str, allocation_bindparams = array2sql(
            allocation_ids, type=sa.Integer, prefix='allocation'
        )

        statements = []
        joins = []
        query_params = []

        # GROUPS
        if len(group_ids) > 0:
            query_params.extend(groups_bindparams)
            statements.append(
                f"""
                sources.group_id IN {groups_query_str}
                """
            )

        # OBJ
        if sourceID not in [None, ""]:
            try:
                sourceID = str(sourceID).strip()
                query_params.append(
                    bindparam('sourceID', value=sourceID, type_=sa.String)
                )

                # we try to detect a potential TNS name as the sourceID,
                # and if so only keep the name without the designation
                # e.g. SN2011fe -> 2011fe, AT 2019abc -> 2019abc
                tns_name = sourceID.lower().replace(' ', '')
                if tns_name_with_designation_pattern.match(tns_name) is not None:
                    # keep only what's after the designation
                    tns_name = tns_name[2:]
                    query_params.append(
                        bindparam(
                            'tns_name',
                            value=tns_name,
                            type_=sa.String,
                        )
                    )
                elif tns_name_no_designation_pattern.match(tns_name) is not None:
                    query_params.append(
                        bindparam(
                            'tns_name',
                            value=tns_name,
                            type_=sa.String,
                        )
                    )
                else:
                    tns_name = None
                statements.append(
                    f"""
                        (objs.id LIKE '%' || :sourceID || '%'{" OR objs.tns_name LIKE '%' || :tns_name || '%'" if tns_name is not None else ""})
                        """
                )
            except Exception as e:
                raise ValueError(f'Invalid sourceID: {sourceID} ({e})')
        if rejectedSourceIDs is not None:
            try:
                query_str, bindparams = array2sql(
                    rejectedSourceIDs, type=sa.String, prefix='rejectedSourceIDs'
                )
                query_params.extend(bindparams)
                statements.append(
                    f"""
                    objs.id NOT IN {query_str}
                    """
                )
            except Exception as e:
                raise ValueError(
                    f'Invalid rejectedSourceIDs: {rejectedSourceIDs} ({e})'
                )
        if alias is not None:
            if alias in ["", None]:
                raise ValueError(f'Invalid alias: {alias}')
            query_params.append(
                bindparam('alias', value=str(alias).strip().lower(), type_=sa.String)
            )
            statements.append(
                """
                (lower(objs.alias) LIKE '%' || :alias || '%')
                """
            )
        if origin not in [None, ""]:
            query_params.append(
                bindparam('origin', value=str(origin).strip().lower(), type_=sa.String)
            )
            # use a LIKE query to allow for partial matches
            statements.append(
                """
                (lower(objs.origin) LIKE '%' || :origin || '%')
                """
            )
        if simbad_class not in [None, ""]:
            query_params.append(
                bindparam(
                    'simbad_class',
                    value=str(simbad_class).strip().lower(),
                    type_=sa.String,
                )
            )
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
                query_params.append(
                    bindparam('min_redshift', value=float(min_redshift), type_=sa.Float)
                )
                statements.append(
                    """
                    objs.redshift >= :min_redshift
                    """
                )
            except Exception as e:
                raise ValueError(f'Invalid min_redshift: {min_redshift} ({e})')
        if max_redshift is not None:
            try:
                query_params.append(
                    bindparam('max_redshift', value=float(max_redshift), type_=sa.Float)
                )
                statements.append(
                    """
                    objs.redshift <= :max_redshift
                    """
                )
            except Exception as e:
                raise ValueError(f'Invalid max_redshift: {max_redshift} ({e})')
        if created_or_modified_after is not None:
            try:
                query_params.append(
                    bindparam(
                        'created_or_modified_after',
                        value=arrow.get(created_or_modified_after).datetime.strftime(
                            '%Y-%m-%d %H:%M:%S.%f'
                        ),
                        type_=sa.DateTime,
                    )
                )
                statements.append(
                    """
                    (objs.created_at > :created_or_modified_after OR objs.modified > :created_or_modified_after)
                    """
                )
            except Exception as e:
                raise ValueError(
                    f'Invalid created_or_modified_after: {created_or_modified_after} ({e})'
                )

        if require_detections:
            # PHOTSTATS
            photstat_query = []
            if first_detected_date is not None:
                try:
                    col = (
                        'first_detected_mjd'
                        if not exclude_forced_photometry
                        else 'first_detected_no_forced_phot_mjd'
                    )
                    query_params.append(
                        bindparam(
                            'first_detected_date',
                            value=Time(arrow.get(first_detected_date).datetime).mjd,
                            type_=sa.Float,
                        )
                    )
                    photstat_query.append(
                        f"""photstats.{col} >= :first_detected_date"""
                    )

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
                    query_params.append(
                        bindparam(
                            'last_detected_date',
                            value=Time(arrow.get(last_detected_date).datetime).mjd,
                            type_=sa.Float,
                        )
                    )
                    photstat_query.append(f"""photstats.{col} <= :last_detected_date""")
                except Exception as e:
                    raise ValueError(
                        f'Invalid last_detected_date: {last_detected_date} ({e})'
                    )
            if number_of_detections is not None:
                try:
                    col = (
                        'num_det_global'
                        if not exclude_forced_photometry
                        else 'num_det_no_forced_phot_global'
                    )
                    query_params.append(
                        bindparam(
                            'number_of_detections',
                            value=int(number_of_detections),
                            type_=sa.Integer,
                        )
                    )
                    photstat_query.append(
                        f"""photstats.{col} >= :number_of_detections"""
                    )
                except Exception as e:
                    raise ValueError(
                        f'Invalid number_of_detections: {number_of_detections} ({e})'
                    )
            if min_peak_magnitude is not None:
                try:
                    query_params.append(
                        bindparam(
                            'min_peak_magnitude',
                            value=float(min_peak_magnitude),
                            type_=sa.Float,
                        )
                    )
                    photstat_query.append(
                        """photstats.peak_mag_global <= :min_peak_magnitude"""
                    )
                except Exception as e:
                    raise ValueError(
                        f'Invalid min_peak_magnitude: {min_peak_magnitude} ({e})'
                    )
            if max_peak_magnitude is not None:
                try:
                    query_params.append(
                        bindparam(
                            'max_peak_magnitude',
                            value=float(max_peak_magnitude),
                            type_=sa.Float,
                        )
                    )
                    photstat_query.append(
                        """photstats.peak_mag_global >= :max_peak_magnitude"""
                    )
                except Exception as e:
                    raise ValueError(
                        f'Invalid max_peak_magnitude: {max_peak_magnitude} ({e})'
                    )
            if min_latest_magnitude is not None:
                try:
                    query_params.append(
                        bindparam(
                            'min_latest_magnitude',
                            value=float(min_latest_magnitude),
                            type_=sa.Float,
                        )
                    )
                    photstat_query.append(
                        """photstats.last_detected_mag <= :min_latest_magnitude"""
                    )
                except Exception as e:
                    raise ValueError(
                        f'Invalid min_latest_magnitude: {min_latest_magnitude} ({e})'
                    )
            if max_latest_magnitude is not None:
                try:
                    query_params.append(
                        bindparam(
                            'max_latest_magnitude',
                            value=float(max_latest_magnitude),
                            type_=sa.Float,
                        )
                    )
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
                raise ValueError(
                    f'Invalid ra, dec, radius: {ra}, {dec}, {radius} ({e})'
                )

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
                query_params.append(
                    bindparam(
                        'saved_before',
                        value=arrow.get(saved_before).datetime.strftime(
                            '%Y-%m-%d %H:%M:%S.%f'
                        ),
                        type_=sa.DateTime,
                    )
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
                query_params.append(
                    bindparam(
                        'saved_after',
                        value=arrow.get(saved_after).datetime.strftime(
                            '%Y-%m-%d %H:%M:%S.%f'
                        ),
                        type_=sa.DateTime,
                    )
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
                EXISTS (SELECT obj_id from classifications where classifications.obj_id=objs.id and classifications.ml=false {"and classifications.id in (select classification_id from group_classifications where group_id in :accessible_group_ids)" if not is_admin else ""})
                """
            )
        elif unclassified:
            statements.append(
                f"""
                NOT EXISTS (SELECT obj_id from classifications where classifications.obj_id=objs.id and classifications.ml=false {"and classifications.id in (select classification_id from group_classifications where group_id in :accessible_group_ids)" if not is_admin else ""})
                """
            )
        else:
            taxonomy_name_to_id = {}
            all_taxonomy_names = []
            classification_taxonomy_names, classifications_text = [], []
            nonclassification_taxonomy_names, nonclassifications_text = [], []
            classifications_query, nonclassifications_query = [], []

            if classifications is not None:
                if isinstance(classifications, str) and "," in classifications:
                    classifications = [c.strip() for c in classifications.split(",")]
                elif isinstance(classifications, str):
                    classifications = [classifications]
                elif not isinstance(classifications, list):
                    raise ValueError(
                        "Invalid classifications value -- must provide at least one string value"
                    )
                elif not all([":" in c for c in classifications]):
                    raise ValueError(
                        "Invalid classifications value -- must provide a list of strings with each string in the format 'taxonomy_name:classification'"
                    )

                classification_taxonomy_names, classifications_text = list(
                    zip(
                        *list(
                            map(
                                lambda c: (
                                    c.split(":")[0].strip(),
                                    c.split(":")[1].strip(),
                                ),
                                classifications,
                            )
                        )
                    )
                )
                all_taxonomy_names.extend(classification_taxonomy_names)

            if nonclassifications is not None:
                if isinstance(nonclassifications, str) and "," in nonclassifications:
                    nonclassifications = [
                        c.strip() for c in nonclassifications.split(",")
                    ]
                elif isinstance(nonclassifications, str):
                    nonclassifications = [nonclassifications]
                elif not isinstance(nonclassifications, list):
                    raise ValueError(
                        "Invalid nonclassifications value -- must provide at least one string value"
                    )
                elif not all([":" in c for c in nonclassifications]):
                    raise ValueError(
                        "Invalid nonclassifications value -- must provide a list of strings with each string in the format 'taxonomy_name:classification'"
                    )
                nonclassification_taxonomy_names, nonclassifications_text = list(
                    zip(
                        *list(
                            map(
                                lambda c: (
                                    c.split(":")[0].strip(),
                                    c.split(":")[1].strip(),
                                ),
                                nonclassifications,
                            )
                        )
                    )
                )
                all_taxonomy_names.extend(nonclassification_taxonomy_names)

            if len(all_taxonomy_names) > 0:
                # fetch the taxonomy_ids for the taxonomy names
                # so we can have a mapper from name to id
                query_str, bindparams = array2sql(
                    all_taxonomy_names, type=sa.String, prefix='all_taxonomy_names'
                )
                stmt = f"""
                SELECT id, name FROM taxonomies WHERE name IN {query_str}
                """
                taxonomies = session.execute(text(stmt).bindparams(*bindparams))
                taxonomy_name_to_id = {}
                for taxonomy in taxonomies:
                    if taxonomy[1] not in taxonomy_name_to_id:
                        taxonomy_name_to_id[taxonomy[1]] = []
                    taxonomy_name_to_id[taxonomy[1]].append(taxonomy[0])

                for taxonomy_name in all_taxonomy_names:
                    if taxonomy_name not in taxonomy_name_to_id:
                        raise ValueError(
                            f"Invalid taxonomy_name: {taxonomy_name} -- no taxonomy with that name exists"
                        )

            if len(classification_taxonomy_names) > 0:
                for i, (taxonomy_name, classification_text) in enumerate(
                    zip(classification_taxonomy_names, classifications_text)
                ):
                    taxonomy_query_str, taxonomy_bindparams = array2sql(
                        taxonomy_name_to_id[taxonomy_name],
                        type=sa.Integer,
                        prefix=f"classification_taxonomy_name_{i}",
                    )
                    query_params.extend(taxonomy_bindparams)
                    query_params.append(
                        bindparam(
                            f"classification_text_{i}",
                            value=classification_text,
                            type_=sa.String,
                        )
                    )
                    classifications_query.append(
                        f"""
                        (classifications.taxonomy_id IN {taxonomy_query_str} AND classifications.classification = :classification_text_{i})
                        """
                    )

                if not is_admin:
                    classification_statement = f"""
                RIGHT JOIN (SELECT obj_id, array_agg(DISTINCT classification) as classifications FROM classifications WHERE ({' OR '.join(classifications_query)}) and classifications.id in (select classification_id from group_classifications where group_id in :accessible_group_ids)
                GROUP BY obj_id) classifications ON classifications.obj_id=objs.id
                """
                else:
                    classification_statement = f"""
                    RIGHT JOIN (SELECT obj_id, array_agg(DISTINCT classification) as classifications FROM classifications WHERE {' OR '.join(classifications_query)}
                    GROUP BY obj_id) classifications ON classifications.obj_id=objs.id
                    """
                # add the join before any WHERE statements
                joins.append(classification_statement)

                # if classifications_simul is True, we want to match all of the classifications
                # that is, that the length of the array_agg of classifications is equal to the number of classifications we are searching for
                if classifications_simul:
                    statements.append(
                        f"""
                        array_length(classifications.classifications, 1) = {len(list(set(classifications_text)))}
                        """
                    )

            if len(nonclassification_taxonomy_names) > 0:
                for i, (taxonomy_name, classification_text) in enumerate(
                    zip(nonclassification_taxonomy_names, nonclassifications_text)
                ):
                    taxonomy_query_str, taxonomy_bindparams = array2sql(
                        taxonomy_name_to_id[taxonomy_name],
                        type=sa.Integer,
                        prefix=f"nonclassification_taxonomy_name_{i}",
                    )
                    query_params.extend(taxonomy_bindparams)
                    query_params.append(
                        bindparam(
                            f"nonclassification_text_{i}",
                            value=classification_text,
                            type_=sa.String,
                        )
                    )
                    nonclassifications_query.append(
                        f"""
                        (classifications.taxonomy_id IN {taxonomy_query_str} AND classifications.classification = :nonclassification_text_{i})
                        """
                    )
                # a left outer join was the fastest way to do this
                if not is_admin:
                    nonclassification_statement = f"""
                    LEFT OUTER JOIN (SELECT obj_id, array_agg(DISTINCT classification) as nonclassifications FROM classifications WHERE ({' OR '.join(nonclassifications_query)}) and classifications.id in (select classification_id from group_classifications where group_id in :accessible_group_ids)
                    GROUP BY obj_id) nonclassifications ON nonclassifications.obj_id=objs.id
                    """
                else:
                    nonclassification_statement = f"""
                    LEFT OUTER JOIN (SELECT obj_id, array_agg(DISTINCT classification) as nonclassifications FROM classifications WHERE {' OR '.join(nonclassifications_query)}
                    GROUP BY obj_id) nonclassifications ON nonclassifications.obj_id=objs.id
                    """
                # add the join before any WHERE statements
                joins.append(nonclassification_statement)
                statements.append(
                    """
                    nonclassifications.obj_id IS NULL
                    """
                )

        # SPECTRA
        if has_spectrum:
            statements.append(
                f"""
                EXISTS (SELECT obj_id from spectra where spectra.obj_id=objs.id {"and spectra.id in (select spectr_id from group_spectra where group_id in :accessible_group_ids)" if not is_admin else ""})
                """
            )
        elif has_no_spectrum:
            statements.append(
                f"""
                NOT EXISTS (SELECT obj_id from spectra where spectra.obj_id=objs.id {"and spectra.id in (select spectr_id from group_spectra where group_id in :accessible_group_ids)" if not is_admin else ""})
                """
            )
        if not has_no_spectrum:
            if has_spectrum_before is not None:
                try:
                    query_params.append(
                        bindparam(
                            'has_spectrum_before',
                            value=arrow.get(has_spectrum_before).datetime.strftime(
                                '%Y-%m-%d %H:%M:%S.%f'
                            ),
                            type_=sa.DateTime,
                        )
                    )
                    statements.append(
                        f"""
                        EXISTS (SELECT obj_id from spectra where spectra.obj_id=objs.id and spectra.observed_at <= :has_spectrum_before {"and spectra.id in (select spectr_id from group_spectra where group_id in :accessible_group_ids)" if not is_admin else ""})
                        """
                    )
                except Exception as e:
                    raise ValueError(
                        f'Invalid has_spectrum_before: {has_spectrum_before} ({e})'
                    )
            if has_spectrum_after is not None:
                try:
                    query_params.append(
                        bindparam(
                            'has_spectrum_after',
                            value=arrow.get(has_spectrum_after).datetime.strftime(
                                '%Y-%m-%d %H:%M:%S.%f'
                            ),
                            type_=sa.DateTime,
                        )
                    )
                    statements.append(
                        f"""
                        EXISTS (SELECT obj_id from spectra where spectra.obj_id=objs.id and spectra.observed_at >= :has_spectrum_after {"and spectra.id in (select spectr_id from group_spectra where group_id in :accessible_group_ids)" if not is_admin else ""})
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
                if followup_request_status is not None:
                    query_params.append(
                        bindparam(
                            'has_followup_request_status',
                            value=str(followup_request_status).strip(),
                            type_=sa.String,
                        )
                    )
                    # if it contains the string, both lowercased, then we have a match
                    statements.append(
                        f"""
                        EXISTS (SELECT obj_id from followuprequests where followuprequests.obj_id=objs.id and lower(followuprequests.status) LIKE '%' || lower(:has_followup_request_status) || '%' {"and followuprequests.allocation_id in :allocation_ids" if not is_admin else ""})
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
            query_params.append(
                bindparam('list_name', value=str(list_name), type_=sa.String)
            )
            query_params.append(
                bindparam('user_id', value=int(user_id), type_=sa.Integer)
            )
            statements.append(
                """
                EXISTS (SELECT obj_id from listings where listings.obj_id=objs.id and listings.list_name = :list_name and listings.user_id = :user_id)
                """
            )

        # SOURCE LABELS
        if has_been_labelled:
            if current_user_labeller:
                query_params.append(
                    bindparam(
                        'current_user_labeller', value=int(user_id), type_=sa.Integer
                    )
                )
                statements.append(
                    f"""
                    EXISTS (SELECT obj_id from sourcelabels where sourcelabels.obj_id=objs.id and sourcelabels.labeller_id = :current_user_labeller {"and sourcelabels.group_id in :accessible_group_ids" if not is_admin else ""})
                    """
                )
            else:
                statements.append(
                    f"""
                    EXISTS (SELECT obj_id from sourcelabels where sourcelabels.obj_id=objs.id {"and sourcelabels.group_id in :accessible_group_ids" if not is_admin else ""})
                    """
                )
        elif has_not_been_labelled:
            if current_user_labeller:
                query_params.append(
                    bindparam(
                        'current_user_labeller', value=int(user_id), type_=sa.Integer
                    )
                )
                statements.append(
                    f"""
                    NOT EXISTS (SELECT obj_id from sourcelabels where sourcelabels.obj_id=objs.id and sourcelabels.labeller_id = :current_user_labeller {"and sourcelabels.group_id in :accessible_group_ids" if not is_admin else ""})
                    """
                )
            else:
                statements.append(
                    f"""
                    NOT EXISTS (SELECT obj_id from sourcelabels where sourcelabels.obj_id=objs.id {"and sourcelabels.group_id in :accessible_group_ids " if not is_admin else ""})
                    """
                )

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
                    annotations_filter = [
                        a.strip() for a in annotations_filter.split(",")
                    ]
                elif isinstance(annotations_filter, str):
                    annotations_filter = [annotations_filter]
                for i, ann_filter in enumerate(annotations_filter):
                    ann_split = ann_filter.split(":")
                    if not (len(ann_split) == 1 or len(ann_split) == 3):
                        raise ValueError(
                            "Invalid annotationsFilter value -- annotation filter must have 1 or 3 values"
                        )

                    (
                        annotations_query,
                        annotations_query_params,
                    ) = create_annotation_query(
                        ann_split,
                        annotations_filter_origin,
                        annotations_filter_before,
                        annotations_filter_after,
                        i,
                        is_admin,
                    )
                    if annotations_query is not None:
                        statements.append(annotations_query)
                        query_params.extend(annotations_query_params)
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
                    query_params.extend(annotations_query_params)

        # COMMENTS
        comments_query = []
        if comments_filter is not None:
            if isinstance(comments_filter, str) and "," in comments_filter:
                comments_filter = [c.strip() for c in comments_filter.split(",")]
            elif isinstance(comments_filter, str):
                comments_filter = [comments_filter]
            elif isinstance(comments_filter, list):
                comments_filter = [str(c) for c in comments_filter]
            for i, c in enumerate(comments_filter):
                query_params.append(
                    bindparam(f'comments_filter_{i}', value=c, type_=sa.String)
                )
            comments_query.append(
                f"""comments.text ilike any(array[:{', :'.join([f'comments_filter_{i}' for i in range(len(comments_filter))])}])"""
            )
        if comments_filter_before is not None:
            try:
                query_params.append(
                    bindparam(
                        'comments_filter_before',
                        value=arrow.get(comments_filter_before).datetime.strftime(
                            '%Y-%m-%d %H:%M:%S.%f'
                        ),
                        type_=sa.DateTime,
                    )
                )
                comments_query.append(
                    """comments.created_at <= :comments_filter_before"""
                )
            except Exception as e:
                raise ValueError(
                    f'Invalid comments_filter_before: {comments_filter_before} ({e})'
                )
        if comments_filter_after is not None:
            try:
                query_params.append(
                    bindparam(
                        'comments_filter_after',
                        value=arrow.get(comments_filter_after).datetime.strftime(
                            '%Y-%m-%d %H:%M:%S.%f'
                        ),
                        type_=sa.DateTime,
                    )
                )
                comments_query.append(
                    """comments.created_at >= :comments_filter_after"""
                )
            except Exception as e:
                raise ValueError(
                    f'Invalid comments_filter_after: {comments_filter_after} ({e})'
                )
        if comments_filter_author is not None:
            try:
                query_params.append(
                    bindparam(
                        'comments_filter_author',
                        value=int(comments_filter_author),
                        type_=sa.Integer,
                    )
                )
                comments_query.append(
                    """comments.author_id = :comments_filter_author"""
                )
            except Exception as e:
                raise ValueError(
                    f'Invalid comments_filter_author: {comments_filter_author} ({e})'
                )
        if len(comments_query) > 0:
            statements.append(
                f"""
                EXISTS (SELECT obj_id from comments where comments.obj_id=objs.id and {' AND '.join(comments_query)} {"and comments.id in (select comment_id from group_comments where group_id in :accessible_group_ids)" if not is_admin else ""})
                """
            )
        localization_queries = []
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
                localization_queries.append(
                    f"""EXISTS (
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
                )
                if localization_reject_sources or sort_by == "gcn_status":
                    joins.append(
                        f"""
                        LEFT JOIN sourcesconfirmedingcns ON sourcesconfirmedingcns.obj_id = objs.id AND sourcesconfirmedingcns.dateobs = '{localization_dateobs.strftime('%Y-%m-%d %H:%M:%S')}'
                        """
                    )
                    if localization_reject_sources:
                        statements.append(
                            """
                            sourcesconfirmedingcns.confirmed is not false
                            """
                        )
                if include_sources_in_gcn:
                    localization_queries.append(
                        f"""
                        EXISTS (SELECT sourcesconfirmedingcns.obj_id FROM sourcesconfirmedingcns WHERE sourcesconfirmedingcns.obj_id = objs.id AND sourcesconfirmedingcns.dateobs = '{localization_dateobs.strftime('%Y-%m-%d %H:%M:%S')}' AND sourcesconfirmedingcns.confirmed is not false)
                    """
                    )
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
                        bindparam(
                            'spatial_catalog_entry_name',
                            value=str(spatial_catalog_entry_name).strip().lower(),
                            type_=sa.String,
                        ),
                        bindparam(
                            'spatial_catalog_name',
                            value=str(spatial_catalog_name).strip().lower(),
                            type_=sa.String,
                        ),
                    )
                )
                if entry_id is None:
                    raise ValueError('spatial catalog entry not found')

                query_params.append(
                    bindparam(
                        'spatial_catalog_entry_name',
                        value=str(spatial_catalog_entry_name).strip().lower(),
                        type_=sa.String,
                    )
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

        start, end = (int(page_number) - 1) * int(num_per_page), int(page_number) * int(
            num_per_page
        )

        data = {
            'totalMatches': 0,
            'sources': [],
            'pageNumber': page_number,
            'numPerPage': num_per_page,
        }

        if save_summary:
            all_source_ids = []
            if len(localization_queries) > 0:
                for localization_query in localization_queries:
                    statement = f"""
                        SELECT sources.id
                        FROM sources INNER JOIN objs ON sources.obj_id = objs.id
                        {' '.join(joins)}
                        WHERE {' AND '.join(statements + [localization_query])}
                        GROUP BY sources.id
                    """

                    if ":accessible_group_ids" in statement:
                        statement = statement.replace(
                            ":accessible_group_ids", accessible_groups_query_str
                        )
                        query_params.extend(accessible_groups_bindparams)
                    if ':allocation_ids' in statement:
                        statement = statement.replace(
                            ':allocation_ids', allocation_query_str
                        )
                        query_params.extend(allocation_bindparams)

                    statement = (
                        text(statement).bindparams(*query_params).columns(id=sa.String)
                    )
                    if verbose:
                        log_verbose(f'Params:\n{query_params}')
                        log_verbose(f'Query:\n{statement}')

                    startTime = time.time()

                    connection = session.connection()
                    results = connection.execute(statement)
                    all_source_ids.extend([r[0] for r in results])

                    endTime = time.time()
                    if verbose:
                        log_verbose(
                            f'1. SUB SAVE SUMMARY Query took {endTime - startTime} seconds, returned {len(all_source_ids)} results.'
                        )

                all_source_ids = list(set(all_source_ids))
                if verbose:
                    log_verbose(
                        f'1. COMBINING BOTH QUERY RESULTS TOOK {endTime - startTime} seconds, returned {len(all_source_ids)} results.'
                    )
            else:
                statement = f"""
                    SELECT sources.id
                    FROM sources INNER JOIN objs ON sources.obj_id = objs.id
                    {' '.join(joins)}
                    WHERE {' AND '.join(statements)}
                    GROUP BY sources.id
                """
                if ":accessible_group_ids" in statement:
                    statement = statement.replace(
                        ":accessible_group_ids", accessible_groups_query_str
                    )
                    query_params.extend(accessible_groups_bindparams)
                if ':allocation_ids' in statement:
                    statement = statement.replace(
                        ':allocation_ids', allocation_query_str
                    )
                    query_params.extend(allocation_bindparams)

                statement = (
                    text(statement).bindparams(*query_params).columns(id=sa.String)
                )
                if verbose:
                    log_verbose(f'Params:\n{query_params}')
                    log_verbose(f'Query:\n{statement}')

                startTime = time.time()

                connection = session.connection()
                results = connection.execute(statement)
                all_source_ids = [r[0] for r in results]

                endTime = time.time()
                if verbose:
                    log_verbose(
                        f'1. MAIN SAVE SUMMARY Query took {endTime - startTime} seconds, returned {len(all_source_ids)} results.'
                    )

            if len(all_source_ids) == 0:
                return data

            sources, total_matches = [], len(all_source_ids)

            data['totalMatches'] = total_matches
            if start > total_matches:
                return data
            if end > total_matches:
                end = total_matches

            source_ids = all_source_ids[start:end]

            startTime = time.time()

            sources = session.scalars(
                Source.select(user).where(Source.id.in_(source_ids))
            ).all()

            endTime = time.time()
            if verbose:
                log_verbose(f'2. Sources Query took {endTime - startTime} seconds.')

            return {
                'totalMatches': total_matches,
                'sources': sources,
                'pageNumber': page_number,
                'numPerPage': num_per_page,
            }

        else:
            all_obj_ids = []
            if len(localization_queries) > 0:
                for localization_query in localization_queries:
                    # ADD QUERY STATEMENTS
                    statement = f"""SELECT objs.id AS id, MAX(sources.saved_at) AS most_recent_saved_at
                        FROM objs INNER JOIN sources ON objs.id = sources.obj_id
                        {' '.join(joins)}
                        WHERE {' AND '.join(statements + [localization_query])}
                        GROUP BY objs.id
                    """

                    if ":accessible_group_ids" in statement:
                        statement = statement.replace(
                            ":accessible_group_ids", accessible_groups_query_str
                        )
                        query_params.extend(accessible_groups_bindparams)
                    if ':allocation_ids' in statement:
                        statement = statement.replace(
                            ':allocation_ids', allocation_query_str
                        )
                        query_params.extend(allocation_bindparams)

                    statement = (
                        text(statement)
                        .bindparams(*query_params)
                        .columns(id=sa.String, most_recent_saved_at=sa.DateTime)
                    )
                    if verbose:
                        log_verbose(f'Params:\n{query_params}')
                        log_verbose(f'Query:\n{statement}')

                    startTime = time.time()

                    connection = session.connection()
                    results = connection.execute(statement)
                    all_obj_ids.extend([r[0] for r in results])

                    endTime = time.time()
                    if verbose:
                        log_verbose(
                            f'1. SUB MAIN Query took {endTime - startTime} seconds, returned {len(all_obj_ids)} results.'
                        )

                all_obj_ids = list(set(all_obj_ids))
                if len(all_obj_ids) == 0:
                    return data
                # by running 2 seperate queries, we lost the ordering, so we need rerun a query with the ordering
                joins = []
                query_params = []

                # SORTING JOINS
                if sort_by == "gcn_status":
                    joins.append(
                        f"""
                        LEFT JOIN sourcesconfirmedingcns ON sourcesconfirmedingcns.obj_id = objs.id AND sourcesconfirmedingcns.dateobs = '{localization_dateobs.strftime('%Y-%m-%d %H:%M:%S')}'
                        """
                    )
                elif sort_by == "favorites":
                    joins.append(
                        f"""
                        LEFT JOIN listings ON listings.obj_id = objs.id AND listings.list_name = 'favorites' AND listings.user_id = {user_id}
                        """
                    )

                query_str, bindparams = array2sql(
                    all_obj_ids,
                    type=sa.String,
                    prefix="obj_id",
                )
                query_params.extend(bindparams)
                statement = f"""SELECT objs.id AS id, MAX(sources.saved_at) AS most_recent_saved_at
                    FROM objs INNER JOIN sources ON objs.id = sources.obj_id
                    {' '.join(joins)}
                    where objs.id in {query_str}
                    GROUP BY objs.id
                """

                if ":accessible_group_ids" in statement:
                    statement = statement.replace(
                        ":accessible_group_ids", accessible_groups_query_str
                    )
                    query_params.extend(accessible_groups_bindparams)
                if ':allocation_ids' in statement:
                    statement = statement.replace(
                        ':allocation_ids', allocation_query_str
                    )
                    query_params.extend(allocation_bindparams)

                if sort_by == "gcn_status":
                    statement += f"""ORDER BY
                        CASE
                            WHEN bool_and(sourcesconfirmedingcns.obj_id IS NULL) = true THEN 4
                            WHEN bool_or(sourcesconfirmedingcns.confirmed) = true THEN 3
                            WHEN bool_and(sourcesconfirmedingcns.confirmed IS NULL) = true THEN 2
                            WHEN bool_or(sourcesconfirmedingcns.confirmed) = false THEN 1
                            ELSE 0
                        END {sort_order.upper()}"""
                elif sort_by == "favorites":
                    statement += f"""ORDER BY bool_and(listings.obj_id IS NULL) {sort_order.upper()}"""
                elif sort_by in NULL_FIELDS:
                    statement += f"""ORDER BY {SORT_BY[sort_by]} {sort_order.upper()} NULLS LAST"""
                else:
                    statement += f"""ORDER BY {SORT_BY[sort_by]} {sort_order.upper()}"""

                statement = (
                    text(statement)
                    .bindparams(*query_params)
                    .columns(id=sa.String, most_recent_saved_at=sa.DateTime)
                )
                connection = session.connection()
                results = connection.execute(statement)
                all_obj_ids = [r[0] for r in results]

                if verbose:
                    log_verbose(
                        f'1. COMBINING BOTH QUERY RESULTS TOOK {endTime - startTime} seconds, returned {len(all_obj_ids)} results.'
                    )
            else:
                # SORTING JOINS
                if sort_by == "favorites":
                    joins.append(
                        f"""
                        LEFT JOIN listings ON listings.obj_id = objs.id AND listings.list_name = 'favorites' AND listings.user_id = {user_id}
                        """
                    )

                # ADD QUERY STATEMENTS
                statement = f"""SELECT objs.id AS id, MAX(sources.saved_at) AS most_recent_saved_at
                    FROM objs INNER JOIN sources ON objs.id = sources.obj_id
                    {' '.join(joins)}
                    WHERE {' AND '.join(statements)}
                    GROUP BY objs.id
                """

                if ":accessible_group_ids" in statement:
                    statement = statement.replace(
                        ":accessible_group_ids", accessible_groups_query_str
                    )
                    query_params.extend(accessible_groups_bindparams)
                if ':allocation_ids' in statement:
                    statement = statement.replace(
                        ':allocation_ids', allocation_query_str
                    )
                    query_params.extend(allocation_bindparams)

                if sort_by == "favorites":
                    statement += f"""ORDER BY bool_and(listings.obj_id IS NULL) {sort_order.upper()}"""
                elif sort_by in NULL_FIELDS:
                    statement += f"""ORDER BY {SORT_BY[sort_by]} {sort_order.upper()} NULLS LAST"""
                else:
                    statement += f"""ORDER BY {SORT_BY[sort_by]} {sort_order.upper()}"""

                statement = (
                    text(statement)
                    .bindparams(*query_params)
                    .columns(id=sa.String, most_recent_saved_at=sa.DateTime)
                )
                if verbose:
                    log_verbose(f'Params:\n{query_params}')
                    log_verbose(f'Query:\n{statement}')

                startTime = time.time()

                connection = session.connection()
                results = connection.execute(statement)
                all_obj_ids = [r[0] for r in results]
                if len(all_obj_ids) != len(set(all_obj_ids)):
                    raise ValueError(
                        f'Duplicate obj_ids in query results, query is incorrect: {all_obj_ids}'
                    )

                endTime = time.time()
                if verbose:
                    log_verbose(
                        f'1. MAIN Query took {endTime - startTime} seconds, returned {len(all_obj_ids)} results.'
                    )

            if len(all_obj_ids) == 0:
                return data

            objs, total_matches = [], len(all_obj_ids)
            if start > total_matches:
                return data
            if end > total_matches:
                end = total_matches

            startTime = time.time()

            obj_ids = all_obj_ids[start:end]
            objs = session.query(Obj).filter(Obj.id.in_(obj_ids)).distinct().all()
            # keep the original order
            objs = sorted(objs, key=lambda obj: obj_ids.index(obj.id))
            if include_hosts:
                # we add some keys already to avoid more loop(s) to add them later
                objs = [
                    {
                        **obj.to_dict(),
                        'groups': [],
                        'host': None,
                        'host_offset': None,
                    }
                    for obj in objs
                ]  # convert to dict
            else:
                objs = [
                    {
                        **obj.to_dict(),
                        'groups': [],
                    }
                    for obj in objs
                ]  # convert to dict

            endTime = time.time()
            if verbose:
                log_verbose(f'2. Objs Query took {endTime - startTime} seconds.')

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
                log_verbose(f'3. Sources Query took {endTime - startTime} seconds.')

            if not remove_nested:
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
                    obj = next(
                        (obj for obj in objs if obj['id'] == source['obj_id']), None
                    )
                    obj['groups'].append(
                        {
                            **groups[source['group_id']],
                            "active": source['active'],
                            "requested": source['requested'],
                            "saved_at": source['saved_at'],
                            "saved_by": users.get(source['saved_by_id'], None),
                        }
                    )

                endTime = time.time()
                if verbose:
                    log_verbose(
                        f'4. Sources Refomatting took {endTime - startTime} seconds.'
                    )

            else:
                # remove the groups key from the objs
                for obj in objs:
                    obj.pop('groups', None)
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
                log_verbose(
                    f'5. Various obj computations took {endTime - startTime} seconds.'
                )

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

                for obj in objs:
                    obj['thumbnails'] = [
                        t for t in thumbnails if t['obj_id'] == obj['id']
                    ]

                endTime = time.time()
                if verbose:
                    log_verbose(
                        f'6. Thumbnails Query took {endTime - startTime} seconds.'
                    )

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
                    log_verbose(
                        f'7. Photstats Query took {endTime - startTime} seconds.'
                    )

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
                    log_verbose(
                        f'8. Classifications Query took {endTime - startTime} seconds.'
                    )

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
                    log_verbose(
                        f'9. Annotations Query took {endTime - startTime} seconds.'
                    )

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
                    log_verbose(
                        f'10. Hosts Query (+offset) took {endTime - startTime} seconds.'
                    )

            if include_spectrum_exists:
                startTime = time.time()
                if has_spectrum:
                    # if we already filtered for sources with spectra, we can just set the flag to True
                    for obj in objs:
                        obj['spectrum_exists'] = True
                else:
                    query_str, bindparams = array2sql(
                        obj_ids, type=sa.String, prefix='obj_ids'
                    )
                    stmt = f"""
                    SELECT DISTINCT obj_id
                    FROM spectra
                    WHERE obj_id IN {query_str}
                    """
                    spectrum_exists = session.execute(
                        text(stmt).bindparams(*bindparams)
                    )
                    spectrum_exists = [r[0] for r in spectrum_exists]
                    for obj in objs:
                        obj['spectrum_exists'] = obj['id'] in spectrum_exists

                endTime = time.time()
                if verbose:
                    log_verbose(
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
                    query_str, bindparams = array2sql(
                        obj_ids, type=sa.String, prefix='obj_ids'
                    )
                    stmt = f"""
                    SELECT DISTINCT obj_id
                    FROM comments
                    WHERE obj_id IN {query_str}
                    """
                    comment_exists = session.execute(text(stmt).bindparams(*bindparams))
                    comment_exists = [r[0] for r in comment_exists]
                    for obj in objs:
                        obj['comment_exists'] = obj['id'] in comment_exists

                endTime = time.time()
                if verbose:
                    log_verbose(
                        f'12. Comment Exists Query took {endTime - startTime} seconds.'
                    )

            if include_photometry_exists:
                startTime = time.time()

                query_str, bindparams = array2sql(
                    obj_ids, type=sa.String, prefix='obj_ids'
                )
                stmt = f"""
                SELECT DISTINCT obj_id
                FROM photometry
                WHERE obj_id IN {query_str}
                """
                photometry_exists = session.execute(text(stmt).bindparams(*bindparams))
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
                    stmt = f"""
                        SELECT DISTINCT obj_id
                        FROM photometric_series
                        WHERE obj_id IN {query_str}
                    """
                    photometric_series_exists = session.execute(
                        text(stmt).bindparams(bindparam(*bindparams))
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
                    log_verbose(
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
                    log_verbose(
                        f'14. Period Exists Query took {endTime - startTime} seconds.'
                    )

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
                    log_verbose(
                        f'15. Comments Query took {endTime - startTime} seconds.'
                    )

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
                    log_verbose(
                        f'16. Labellers Query took {endTime - startTime} seconds.'
                    )

            if include_color_mag:
                startTime = time.time()
                for obj in objs:
                    obj['color_magnitude'] = get_color_mag(obj['annotations'])

                endTime = time.time()
                if verbose:
                    log_verbose(
                        f'17. Color Mag Query took {endTime - startTime} seconds.'
                    )

            data = {
                'totalMatches': total_matches,
                'sources': objs,
                'pageNumber': page_number,
                'numPerPage': num_per_page,
            }

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
            log_verbose(f'TOTAL took {endMethodTime - startMethodTime} seconds.')

        return data
    except Exception as e:
        log_verbose(str(e))
        session.rollback()
        raise e
