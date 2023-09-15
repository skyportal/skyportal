import time
import numpy as np
from tqdm import tqdm

import sqlalchemy as sa
from conesearch_alchemy.math import sind, cosd
from sqlalchemy.sql import and_, text
import arrow

from baselayer.app.env import load_env
from baselayer.app.models import init_db
from baselayer.log import make_log
from skyportal.models import (
    DBSession,
    User,
    Obj,
    Source,
    Thumbnail,
    PhotStat,
    Annotation,
    Classification,
    Group,
    Galaxy,
    Allocation,
)

_, cfg = load_env()
log = make_log('api/source_queries')

init_db(**cfg['database'])

SORT_BY = {
    'saved_at': 'most_recent_saved_at',  # default
    'id': 'objs.id',
    'ra': 'objs.ra',
    'dec': 'objs.dec',
    'redshift': 'objs.redshift',
}

SORT_ORDER = [
    'asc',
    'desc',
]

FILTERS = [
    "has_spectra",
    "has_classifications",
    "has_tnsname",
    "has_no_spectra",
    "has_no_classifications",
    "has_no_tnsname",
    "saved_before",
    "saved_after",
    "created_or_modified_after",
    "has_spectrum_before",
    "has_spectrum_after",
    "min_redshift",
    "max_redshift",
    "alias",
    "origin",
    "has_followup_request",
    'ra',
    'dec',
    'radius',
]

NULL_FIELDS = [
    "redshift",
]

DEGRA = np.pi / 180.0


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


def get(
    filters={},
    group_ids=[],
    page=1,
    nbPerPage=100,
    sortBy='saved_at',
    sortOrder="desc",
    user_id=None,
    verbose=False,
):
    # it takes one query argument, which is the query type
    # and the group_ids to query
    startMethodTime = time.time()

    if user_id is None:
        raise ValueError('No user_id provided.')

    if len(filters) == 0:
        raise ValueError('No filters provided.')

    if len(filters) > 0 and not set(filters).issubset(set(FILTERS)):
        raise ValueError(f'Invalid filters: {filters}')

    if sortBy not in SORT_BY:
        raise ValueError(f'Invalid sortBy: {sortBy}')

    if sortOrder.lower() not in SORT_ORDER:
        raise ValueError(f'Invalid sortOrder: {sortOrder}')

    with DBSession() as session:

        user = session.scalar(sa.select(User).where(User.id == user_id))
        if user is None:
            raise ValueError(f'Invalid user_id: {user_id}')

        user_group_ids = [g.id for g in user.accessible_groups]

        if len(group_ids) == 0:
            group_ids = user_group_ids
        elif not set(group_ids).issubset(set(user_group_ids)):
            raise ValueError('Selected group(s) not all accessible to user.')

        # fetch the allocations in advance, will be used later
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

        data = {}
        query_params = (
            {  # we use query parameters to avoid SQL injection, can be improved
                'group_ids': array2sql(group_ids),
            }
        )

        statement = (
            """SELECT objs.id AS id, MAX(sources.saved_at) AS most_recent_saved_at"""
        )

        statement += """
            FROM objs INNER JOIN sources ON objs.id = sources.obj_id
            WHERE sources.active = true AND sources.group_id IN :group_ids
        """

        if filters.get('has_classifications', False) not in [False, [], None]:
            if isinstance(filters['has_classifications'], list):
                filters['has_classifications'] = [
                    str(c) for c in filters['has_classifications']
                ]
                # dont forget to surround the classification names with quotes
                statement += """
                AND EXISTS (SELECT obj_id from classifications where classifications.obj_id=objs.id and classifications.ml=false and classifications.classification in :classifications and classifications.id in (select classification_id from group_classifications where group_id in :group_ids))
                """
                query_params['classifications'] = array2sql(
                    filters['has_classifications']
                )
            else:
                statement += """
                AND EXISTS (SELECT obj_id from classifications where classifications.obj_id=objs.id and classifications.ml=false and classifications.id in (select classification_id from group_classifications where group_id in :group_ids))
                """
        elif filters.get('has_no_classifications', False) not in [False, [], None]:
            if isinstance(filters['has_no_classifications'], list):
                filters['has_no_classifications'] = [
                    str(c) for c in filters['has_no_classifications']
                ]
                # dont forget to surround the classification names with quotes
                statement += """
                AND NOT EXISTS (SELECT obj_id from classifications where classifications.obj_id=objs.id and classifications.ml=false and classifications.classification in :classifications and classifications.id in (select classification_id from group_classifications where group_id in :group_ids))
                """
                query_params['classifications'] = array2sql(
                    filters['has_no_classifications']
                )
            else:
                statement += """
                AND NOT EXISTS (SELECT obj_id from classifications where classifications.obj_id=objs.id and classifications.ml=false and classifications.id in (select classification_id from group_classifications where group_id in :group_ids))
                """
        if filters.get('has_spectra', False):
            statement += """
            AND EXISTS (SELECT obj_id from spectra where spectra.obj_id=objs.id and spectra.id in (select spectr_id from group_spectra where group_id in :group_ids))
            """
        elif filters.get('has_no_spectra', False):
            statement += """
            AND NOT EXISTS (SELECT obj_id from spectra where spectra.obj_id=objs.id and spectra.id in (select spectr_id from group_spectra where group_id in :group_ids))
            """

        if filters.get('has_spectrum_before', None) is not None:
            try:
                query_params['has_spectrum_before'] = arrow.get(
                    filters["has_spectrum_before"]
                ).datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
                statement += """
                AND EXISTS (SELECT obj_id from spectra where spectra.obj_id=objs.id and spectra.observed_at <= :has_spectrum_before and spectra.id in (select spectr_id from group_spectra where group_id in :group_ids))
                """
            except Exception as e:
                raise ValueError(
                    f'Invalid has_spectrum_before: {filters["has_spectrum_before"]} ({e})'
                )

        if filters.get('has_spectrum_after', None) is not None:
            try:
                query_params['has_spectrum_after'] = arrow.get(
                    filters["has_spectrum_after"]
                ).datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
                statement += """
                AND EXISTS (SELECT obj_id from spectra where spectra.obj_id=objs.id and spectra.observed_at >= :has_spectrum_after and spectra.id in (select spectr_id from group_spectra where group_id in :group_ids))
                """
            except Exception as e:
                raise ValueError(
                    f'Invalid has_spectrum_after: {filters["has_spectrum_after"]} ({e})'
                )

        if {'ra', 'dec', 'radius'}.issubset(set(filters)):
            try:
                ra, dec, radius = (
                    float(filters['ra']),
                    float(filters['dec']),
                    float(filters['radius']),
                )
                statement += f"""
                AND {within(Obj.ra, Obj.dec, ra, dec, radius).compile(compile_kwargs={"literal_binds": True})}
                """
                pass
            except Exception as e:
                raise ValueError(
                    f'Invalid ra, dec, radius: {filters["ra"]}, {filters["dec"]}, {filters["radius"]} ({e})'
                )

        if filters.get('has_tnsname', False):
            statement += """
            AND objs.tns_name IS NOT NULL
            """
        elif filters.get('has_no_tnsname', False):
            statement += """
            AND objs.tns_name IS NULL
            """

        if "min_redshift" in filters:
            try:
                query_params['min_redshift'] = float(filters["min_redshift"])
                statement += """
                AND objs.redshift >= :min_redshift
                """
            except Exception as e:
                raise ValueError(
                    f'Invalid min_redshift: {filters["min_redshift"]} ({e})'
                )

        if "max_redshift" in filters:
            try:
                query_params['max_redshift'] = float(filters["max_redshift"])
                statement += """
                AND objs.redshift <= :max_redshift
                """
            except Exception as e:
                raise ValueError(
                    f'Invalid max_redshift: {filters["max_redshift"]} ({e})'
                )

        if filters.get("saved_before", None) is not None:
            try:
                query_params['saved_before'] = arrow.get(
                    filters["saved_before"]
                ).datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
                statement += """
                AND sources.saved_at < :saved_before
                """
            except Exception as e:
                raise ValueError(
                    f'Invalid saved_before: {filters["saved_before"]} ({e})'
                )

        if filters.get("saved_after", None) is not None:
            try:
                query_params['saved_after'] = arrow.get(
                    filters["saved_after"]
                ).datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
                statement += """
                AND sources.saved_at > :saved_after
                """
            except Exception as e:
                raise ValueError(f'Invalid saved_after: {filters["saved_after"]} ({e})')

        if filters.get("created_or_modified_after", None) is not None:
            try:
                query_params['created_or_modified_after'] = arrow.get(
                    filters["created_or_modified_after"]
                ).datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
                statement += """
                AND (objs.created_at > :created_or_modified_after OR objs.modified > :created_or_modified_after)
                """
            except Exception as e:
                raise ValueError(
                    f'Invalid created_or_modified_after: {filters["created_or_modified_after"]} ({e})'
                )

        if filters.get("alias", None) is not None:
            if filters["alias"] in ["", None]:
                raise ValueError(f'Invalid alias: {filters["alias"]}')
            query_params['alias'] = filters["alias"]
            # use a LIKE query to allow for partial matches
            statement += """
            AND objs.altdata LIKE '%:alias%'
            """

        if filters.get("origin", None) is not None:
            if filters["origin"] in ["", None]:
                raise ValueError(f'Invalid origin: {filters["origin"]}')
            query_params['origin'] = filters["origin"]
            # use a LIKE query to allow for partial matches
            statement += """
            AND objs.origin LIKE '%:origin%'
            """

        if filters.get("has_followup_request", False):
            pass  # TODO
            #         SELECT followuprequests.requester_id, followuprequests.last_modified_by_id, followuprequests.obj_id, followuprequests.payload, followuprequests.status, followuprequests.allocation_id, followuprequests.id, followuprequests.created_at, followuprequests.modified
            # FROM followuprequests JOIN allocations ON allocations.id = followuprequests.allocation_id JOIN (SELECT allocations.id AS id
            # FROM allocations JOIN (SELECT allocations_1.id AS id
            # FROM allocations AS allocations_1 JOIN groups ON groups.id = allocations_1.group_id JOIN group_users AS group_users_1 ON groups.id = group_users_1.group_id JOIN users ON users.id = group_users_1.user_id
            # WHERE users.id = :id_1) AS anon_2 ON anon_2.id = allocations.id JOIN (SELECT allocations_2.id AS id
            # FROM allocations AS allocations_2) AS anon_3 ON anon_3.id = allocations.id) AS anon_1 ON anon_1.id = allocations.id

            # this example above is a badly generated query, but the logic is here
            # we already grabbed the allocation's ids in advance, so we can use them here
            query_params['allocation_ids'] = array2sql(allocation_ids)
            statement += """
            AND EXISTS (SELECT obj_id from followuprequests where followuprequests.obj_id=objs.id and followuprequests.allocation_id in :allocation_ids)
            """

        statement += """
        GROUP BY objs.id
        """

        if sortBy in NULL_FIELDS:
            statement += f"""
            ORDER BY {SORT_BY[sortBy]} {sortOrder.upper()} NULLS LAST
            """
        else:
            statement += f"""
            ORDER BY {SORT_BY[sortBy]} {sortOrder.upper()}
            """

        # statement += f"""
        # LIMIT {nbPerPage} OFFSET {(page-1)*nbPerPage}
        # """

        statement = (
            text(statement)
            .bindparams(**query_params)
            .columns(id=sa.String, most_recent_saved_at=sa.DateTime)
        )
        if verbose:
            log(f'Query:\n{statement}')

        startTime = time.time()

        connection = DBSession().connection()
        results = connection.execute(statement)
        all_obj_ids = [r[0] for r in results]

        endTime = time.time()
        if verbose:
            log(
                f'1. MAIN Query took {endTime - startTime} seconds, returned {len(all_obj_ids)} results.'
            )

        start, end = (page - 1) * nbPerPage, page * nbPerPage
        totalMatches = len(all_obj_ids)
        if totalMatches > 0 and start <= totalMatches:
            if end > totalMatches:
                end = totalMatches

            startTime = time.time()

            obj_ids = all_obj_ids[start:end]
            objs = session.query(Obj).filter(Obj.id.in_(obj_ids)).distinct().all()
            objs = sorted(
                objs, key=lambda obj: obj_ids.index(obj.id)
            )  # sort by original order
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

            # THUMBNAILS
            startTime = time.time()

            thumbnails = (
                session.scalars(
                    Thumbnail.select(user).where(Thumbnail.obj_id.in_(obj_ids))
                )
                .unique()
                .all()
            )
            thumbnails = [t.to_dict() for t in thumbnails]
            for obj in objs:
                obj['thumbnails'] = sorted(
                    (t for t in thumbnails if t['obj_id'] == obj['id']),
                    key=lambda t: t['created_at'],
                )

            endTime = time.time()
            if verbose:
                log(f'3. Thumbnails Query took {endTime - startTime} seconds.')

            # PHOTSTATS
            startTime = time.time()

            photstats = (
                session.scalars(
                    PhotStat.select(user).where(PhotStat.obj_id.in_(obj_ids))
                )
                .unique()
                .all()
            )
            photstats = [p.to_dict() for p in photstats]
            for obj in objs:
                obj['photstats'] = sorted(
                    (p for p in photstats if p['obj_id'] == obj['id']),
                    key=lambda p: p['created_at'],
                )

            endTime = time.time()
            if verbose:
                log(f'4. Photstats Query took {endTime - startTime} seconds.')

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
            classifications = [c.to_dict() for c in classifications]
            for obj in objs:
                obj['classifications'] = sorted(
                    (c for c in classifications if c['obj_id'] == obj['id']),
                    key=lambda c: c['created_at'],
                )

            endTime = time.time()
            if verbose:
                log(f'5. Classifications Query took {endTime - startTime} seconds.')

            # ANNOTATIONS
            startTime = time.time()

            annotations = (
                session.scalars(
                    Annotation.select(user).where(Annotation.obj_id.in_(obj_ids))
                )
                .unique()
                .all()
            )
            annotations = [a.to_dict() for a in annotations]
            for obj in objs:
                obj['annotations'] = sorted(
                    (a for a in annotations if a['obj_id'] == obj['id']),
                    key=lambda a: a['created_at'],
                )

            endTime = time.time()
            if verbose:
                log(f'6. Annotations Query took {endTime - startTime} seconds.')

            # SOURCES
            startTime = time.time()

            sources = (
                session.scalars(Source.select(user).where(Source.obj_id.in_(obj_ids)))
                .unique()
                .all()
            )
            sources = [s.to_dict() for s in sources]
            sources = sorted(
                (s for s in sources if s['obj_id'] == obj['id']),
                key=lambda s: s['created_at'],
            )

            endTime = time.time()
            if verbose:
                log(f'7. Sources Query took {endTime - startTime} seconds.')

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
                log(f'8. Sources Refomatting took {endTime - startTime} seconds.')

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
                hosts_coords = np.array([[host['ra'], host['dec']] for host in hosts])

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
                log(f'9. Hosts Query (+offset) took {endTime - startTime} seconds.')

            data = {'totalMatches': totalMatches, 'objs': objs}

        else:
            data = {'totalMatches': totalMatches, 'objs': []}

        endMethodTime = time.time()
        if verbose:
            log(f'TOTAL took {endMethodTime - startMethodTime} seconds.')

            return data


def benchmark(filters, user_id, group_ids, page, nbPerPage):
    combinations = []
    for sortBy in SORT_BY:
        for sortOrder in ['asc', 'desc']:
            combinations.append((sortBy, sortOrder))

    results = []

    # then, run each combination 10 times and take the average
    for sortBy, sortOrder in combinations:
        totalTime = 0
        for i in tqdm(
            range(10), desc=f'{str(filters)}, sortBy={sortBy}, sortOrder={sortOrder}'
        ):
            startTime = time.time()
            get(
                filters=filters,
                group_ids=group_ids,
                page=page,
                nbPerPage=nbPerPage,
                sortBy=sortBy,
                sortOrder=sortOrder,
                user_id=user_id,
                verbose=False,
            )
            endTime = time.time()
            totalTime += endTime - startTime
        avgTime = totalTime / 10
        results.append((sortBy, sortOrder, avgTime))

    print()
    # summarize the results in a table
    print(f'{"sortBy":<10}{"sortOrder":<10}{"avgTime":<10}')
    for sortBy, sortOrder, avgTime in results:
        print(f'{sortBy:<10}{sortOrder:<10}{avgTime:<10}')


if __name__ == '__main__':
    user_id = 13
    group_ids = []
    page = 1
    nbPerPage = 100
    filters = {
        'has_spectra': True,
        # 'has_no_classifications': True,
        # 'has_no_classifications': ["Type II"],
        # 'has_no_tnsname': True
        # 'saved_after': '2021-01-01',
        # 'saved_before': '2023-09-01',
        # 'created_or_modified_after': '2023-01-01',
        # 'min_redshift': '0.1',
        # 'max_redshift': '2.0',
        # 'has_followup_request': True,
        'radius': 10,
        'ra': 50.0,
        'dec': 50.0,
    }
    sortBy = 'redshift'
    sortOrder = 'desc'

    # run just one query first to make sure it works
    data = get(
        filters=filters,
        group_ids=group_ids,
        page=page,
        nbPerPage=nbPerPage,
        sortBy=sortBy,
        sortOrder=sortOrder,
        user_id=user_id,
        verbose=True,
    )
    log(
        f'Query returned {data["totalMatches"]} matches. Limited to {len(data["objs"])} results.'
    )

    # benchmark(filters, user_id, group_ids, page, nbPerPage)

# TODOs:
# - take taxonomy into account when filtering on classifications but with names (not just booleans)
