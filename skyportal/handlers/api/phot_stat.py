from typing import Annotated

import arrow
import sqlalchemy as sa
from pydantic import Field
from skyportal_py_models.sources import (
    PhotStatAggregateGetQuery,
    PhotStatUpdateGetQuery,
    PhotStatUpdatePatchQuery,
    PhotStatUpdatePostQuery,
)
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from baselayer.app.access import auth_or_token, permissions
from baselayer.log import make_log

from ...models import (
    Classification,
    Obj,
    Photometry,
    PhotStat,
    Source,
)
from ..base import BaseHandler

ObjId = Annotated[str, Field(description="object ID to get statistics on")]

log = make_log("api/source")

MAX_SOURCES_PER_PAGE = 500

# Scalar PhotStat columns that can be plotted against one another, with the
# labels shown in the bulk-statistics UI. Restricting to this allowlist keeps
# the aggregate endpoint from exposing arbitrary column access.
PHOT_STAT_PLOT_FIELDS = {
    "num_obs_global": "Number of observations",
    "num_det_global": "Number of detections",
    "first_detected_mjd": "First detection [MJD]",
    "first_detected_mag": "First detection magnitude",
    "last_detected_mjd": "Last detection [MJD]",
    "last_detected_mag": "Last detection magnitude",
    "peak_mjd_global": "Peak time [MJD]",
    "peak_mag_global": "Peak magnitude",
    "mean_mag_global": "Mean magnitude",
    "faintest_mag_global": "Faintest magnitude",
    "deepest_limit_global": "Deepest limit",
    "rise_rate": "Rise rate [mag/day]",
    "decay_rate": "Decay rate [mag/day]",
    "mag_rms_global": "Magnitude RMS",
    "time_to_non_detection": "Time to non-detection [day]",
}

# Absolute ceiling on returned points, regardless of the requested maxMatches.
MAX_AGGREGATE_POINTS = 100000


class PhotStatHandler(BaseHandler):
    @auth_or_token
    async def get(self, obj_id: ObjId = None):
        """
        ---
        summary: Get photometry stats for a source
        description: retrieve the PhotStat associated with the obj_id.
        tags:
          - photometry
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
                          $ref: '#/components/schemas/PhotStat'
          400:
              content:
                application/json:
                  schema: Error

        """
        async with self.AsyncSession() as session:
            obj = await session.scalar(
                Obj.select(self.current_user).where(Obj.id == obj_id)
            )
            if obj is None:
                return self.error(f'Cannot find source with id "{obj_id}". ')

            phot_stat = await session.scalar(
                sa.select(PhotStat).where(PhotStat.obj_id == obj_id)
            )

            if phot_stat is None:
                return self.error(
                    f'Could not find a PhotStat for object with id "{obj_id}". '
                )

            # this is a non-permissioned query:
            # it will get the time of the latest photometry
            # regardless of the user's permissions to view it.
            last_photometry = await session.scalar(
                sa.select(Photometry)
                .where(Photometry.obj_id == obj_id)
                .order_by(Photometry.created_at.desc())
            )
            if last_photometry:
                phot_stat.last_phot_add_time = last_photometry.created_at
            else:
                phot_stat.last_phot_add_time = None

        return self.success(data=phot_stat)

    @permissions(["system admin"])
    async def post(self, obj_id: ObjId = None):
        """
        ---
        summary: Create new phot stats for a source
        description: create a new PhotStat to be associated with the obj_id.
        tags:
          - photometry
        responses:
          200:
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/Success'
          400:
              content:
                application/json:
                  schema: Error

        """
        async with self.AsyncSession() as session:
            obj = await session.scalar(
                Obj.select(self.current_user).where(Obj.id == obj_id)
            )
            if obj is None:
                return self.error(f'Cannot find source with id "{obj_id}". ')

            phot_stat = await session.scalar(
                sa.select(PhotStat).where(PhotStat.obj_id == obj_id)
            )
            if phot_stat is not None:
                return self.error(
                    f'PhotStat for object with id "{obj_id}" already exists. '
                )

            photometry_result = await session.scalars(
                sa.select(Photometry).where(Photometry.obj_id == obj_id)
            )
            photometry = photometry_result.all()

            phot_stat = PhotStat(obj_id=obj_id)
            phot_stat.full_update(photometry)
            session.add(phot_stat)
            await session.commit()

        return self.success()

    @permissions(["system admin"])
    async def put(self, obj_id: ObjId = None):
        """
        ---
        summary: Update phot stats for a source
        description: create or update the PhotStat associated with the obj_id.
        tags:
          - photometry
        responses:
          200:
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/Success'
          400:
              content:
                application/json:
                  schema: Error

        """

        async with self.AsyncSession() as session:
            obj = await session.scalar(
                Obj.select(self.current_user).where(Obj.id == obj_id)
            )
            if obj is None:
                return self.error(f'Cannot find source with id "{obj_id}". ')

            phot_stat = await session.scalar(
                sa.select(PhotStat).where(PhotStat.obj_id == obj_id)
            )
            if phot_stat is None:
                phot_stat = PhotStat(obj_id=obj_id)

            photometry_result = await session.scalars(
                sa.select(Photometry).where(Photometry.obj_id == obj_id)
            )
            photometry = photometry_result.all()
            phot_stat.full_update(photometry)
            session.add(phot_stat)
            await session.commit()

        return self.success()

    @permissions(["system admin"])
    async def delete(self, obj_id: ObjId = None):
        """
        ---
        summary: Delete phot stats of a source
        description: delete the PhotStat associated with the obj_id.
        tags:
          - photometry
        responses:
          200:
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/Success'
          400:
              content:
                application/json:
                  schema: Error
        """
        async with self.AsyncSession() as session:
            obj = await session.scalar(
                Obj.select(self.current_user).where(Obj.id == obj_id)
            )
            if obj is None:
                return self.error(f'Cannot find source with id "{obj_id}". ')

            phot_stats_result = await session.scalars(
                sa.select(PhotStat).where(PhotStat.obj_id == obj_id)
            )
            phot_stats = phot_stats_result.all()
            if not phot_stats:
                return self.error(
                    f'Could not find a PhotStat for object with id "{obj_id}". '
                )
            for p in phot_stats:
                await session.delete(p)

            await session.commit()

        return self.success()


class PhotStatUpdateHandler(BaseHandler):
    @permissions(["System admin"])
    async def get(self, *, query: PhotStatUpdateGetQuery = None):
        """
        ---
        summary: Get counts of sources w/ and w/o PhotStats
        description: find the number of sources with and without a PhotStat object
        tags:
          - photometry
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
                              totalMatches:
                                type: integer
                              pageNumber:
                                type: integer
                              numPerPage:
                                type: integer
            400:
              content:
                application/json:
                  schema: Error
        """
        query = self.parse_query(PhotStatUpdateGetQuery)

        created_at_start_time = query.createdAtStartTime
        created_at_end_time = query.createdAtEndTime
        quick_update_start_time = query.quickUpdateStartTime
        quick_update_end_time = query.quickUpdateEndTime
        full_update_start_time = query.fullUpdateStartTime
        full_update_end_time = query.fullUpdateEndTime

        async with self.AsyncSession() as session:
            try:
                # start with Objs that have created_at within range
                stmt = sa.select(Obj).options(selectinload(Obj.photstats))
                if created_at_start_time:
                    created_at_start_time = arrow.get(
                        created_at_start_time.strip()
                    ).naive
                    stmt = stmt.where(Obj.created_at >= created_at_start_time)
                if created_at_end_time:
                    created_at_end_time = arrow.get(created_at_end_time.strip()).naive
                    stmt = stmt.where(Obj.created_at <= created_at_end_time)
            except arrow.parser.ParserError:
                return self.error(
                    f"Cannot parse inputs createdAtStartTime ({created_at_start_time}) "
                    f"or createdAtEndTime ({created_at_end_time}) as arrow parseable strings."
                )

            # select only objects that don't have a PhotStats object
            stmt_without = stmt.where(~Obj.photstats.any())
            count_stmt = sa.select(func.count()).select_from(stmt_without.subquery())
            total_missing = await session.scalar(count_stmt)

            # get the number of Objs with PhotStats
            # (that have created_at within range,
            # and that have update times within range)
            stmt_with = stmt.where(Obj.photstats.any())
            try:
                if quick_update_start_time:
                    quick_update_start_time = arrow.get(
                        quick_update_start_time.strip()
                    ).naive
                    stmt_with = stmt_with.where(
                        Obj.photstats.any(
                            PhotStat.last_update >= quick_update_start_time
                        )
                    )
                if quick_update_end_time:
                    quick_update_end_time = arrow.get(
                        quick_update_end_time.strip()
                    ).naive
                    stmt_with = stmt_with.where(
                        Obj.photstats.any(PhotStat.last_update <= quick_update_end_time)
                    )
                if full_update_start_time:
                    full_update_start_time = arrow.get(
                        full_update_start_time.strip()
                    ).naive
                    stmt_with = stmt_with.where(
                        Obj.photstats.any(
                            PhotStat.last_full_update >= full_update_start_time
                        )
                    )
                if full_update_end_time:
                    full_update_end_time = arrow.get(full_update_end_time.strip()).naive
                    stmt_with = stmt_with.where(
                        Obj.photstats.any(
                            PhotStat.last_full_update <= full_update_end_time
                        )
                    )
            except arrow.parser.ParserError:
                return self.error(
                    f"Cannot parse inputs quickUpdateStartTime ({quick_update_start_time}) "
                    f"or quickUpdateEndTime ({quick_update_end_time}) "
                    f"or fullUpdateStartTime ({full_update_start_time}) "
                    f"or fullUpdateEndTime ({full_update_end_time}) "
                    "as arrow parseable strings."
                )
            count_stmt = sa.select(func.count()).select_from(
                stmt_with.distinct().subquery()
            )
            total_phot_stats = await session.scalar(count_stmt)

        results = {
            "totalWithoutPhotStats": total_missing,
            "totalWithPhotStats": total_phot_stats,
        }
        return self.success(data=results)

    @permissions(["System admin"])
    async def post(self, *, query: PhotStatUpdatePostQuery = None):
        """
        ---
        summary: Calculate phot stats for a batch of sources
        description: calculate photometric stats for a batch of sources without a PhotStat
        tags:
          - photometry
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
                              totalMatches:
                                type: integer
                              pageNumber:
                                type: integer
                              numPerPage:
                                type: integer
            400:
              content:
                application/json:
                  schema: Error
        """

        query = self.parse_query(PhotStatUpdatePostQuery)

        page_number = query.pageNumber
        num_per_page = min(query.numPerPage, MAX_SOURCES_PER_PAGE)

        created_at_start_time = query.createdAtStartTime
        created_at_end_time = query.createdAtEndTime

        async with self.AsyncSession() as session:
            stmt = sa.select(Obj).options(selectinload(Obj.photstats))
            try:
                if created_at_start_time:
                    created_at_start_time = arrow.get(
                        created_at_start_time.strip()
                    ).naive
                    stmt = stmt.where(Obj.created_at >= created_at_start_time)
                if created_at_end_time:
                    created_at_end_time = arrow.get(created_at_end_time.strip()).naive
                    stmt = stmt.where(Obj.created_at <= created_at_end_time)
            except arrow.parser.ParserError:
                return self.error(
                    f"Cannot parse inputs createdAtStartTime ({created_at_start_time}) "
                    f"or createdAtEndTime ({created_at_end_time}) as arrow parseable strings."
                )

            # select only objects that don't have a PhotStats object
            stmt = stmt.where(~Obj.photstats.any())

            count_stmt = sa.select(func.count()).select_from(stmt.subquery())
            total_matches = await session.scalar(count_stmt)
            stmt = stmt.offset((page_number - 1) * num_per_page)
            stmt = stmt.limit(num_per_page)
            result = await session.scalars(stmt)
            objects = result.unique().all()

            current_obj_id = None
            try:
                for obj in objects:
                    current_obj_id = obj.id
                    photometry_result = await session.scalars(
                        sa.select(Photometry).where(Photometry.obj_id == obj.id)
                    )
                    photometry = photometry_result.all()
                    phot_stat = PhotStat(obj_id=obj.id)
                    phot_stat.full_update(photometry)
                    session.add(phot_stat)
            except Exception as e:
                return self.error(
                    f"Error calculating photometry stats: {e} for object {current_obj_id}"
                )

            await session.commit()

        results = {
            "totalMatches": total_matches,
            "numPerPage": num_per_page,
            "pageNumber": page_number,
        }
        return self.success(data=results)

    @permissions(["System admin"])
    async def patch(self, *, query: PhotStatUpdatePatchQuery = None):
        """
        ---
        summary: Recalculate phot stats for a batch of sources
        description: manually recalculate the photometric stats for a batch of sources
        tags:
          - photometry
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
                              totalMatches:
                                type: integer
                              pageNumber:
                                type: integer
                              numPerPage:
                                type: integer
            400:
              content:
                application/json:
                  schema: Error
        """

        query = self.parse_query(PhotStatUpdatePatchQuery)

        page_number = query.pageNumber
        num_per_page = min(query.numPerPage, MAX_SOURCES_PER_PAGE)

        created_at_start_time = query.createdAtStartTime
        created_at_end_time = query.createdAtEndTime
        quick_update_start_time = query.quickUpdateStartTime
        quick_update_end_time = query.quickUpdateEndTime
        full_update_start_time = query.fullUpdateStartTime
        full_update_end_time = query.fullUpdateEndTime

        async with self.AsyncSession() as session:
            stmt = sa.select(Obj).options(selectinload(Obj.photstats))
            try:
                if created_at_start_time:
                    created_at_start_time = arrow.get(
                        created_at_start_time.strip()
                    ).naive
                    stmt = stmt.where(Obj.created_at >= created_at_start_time)
                if created_at_end_time:
                    created_at_end_time = arrow.get(created_at_end_time.strip()).naive
                    stmt = stmt.where(Obj.created_at <= created_at_end_time)
            except arrow.parser.ParserError:
                return self.error(
                    f"Cannot parse inputs createdAtStartTime ({created_at_start_time}) "
                    f"or createdAtEndTime ({created_at_end_time}) as arrow parseable strings."
                )

            # only look at Objs with a PhotStat
            stmt = stmt.where(Obj.photstats.any())
            try:
                if quick_update_start_time:
                    quick_update_start_time = arrow.get(
                        quick_update_start_time.strip()
                    ).naive
                    stmt = stmt.where(
                        Obj.photstats.any(
                            PhotStat.last_update >= quick_update_start_time
                        )
                    )
                if quick_update_end_time:
                    quick_update_end_time = arrow.get(
                        quick_update_end_time.strip()
                    ).naive
                    stmt = stmt.where(
                        Obj.photstats.any(PhotStat.last_update <= quick_update_end_time)
                    )
                if full_update_start_time:
                    full_update_start_time = arrow.get(
                        full_update_start_time.strip()
                    ).naive
                    stmt = stmt.where(
                        Obj.photstats.any(
                            PhotStat.last_full_update >= full_update_start_time
                        )
                    )
                if full_update_end_time:
                    full_update_end_time = arrow.get(full_update_end_time.strip()).naive
                    stmt = stmt.where(
                        Obj.photstats.any(
                            PhotStat.last_full_update <= full_update_end_time
                        )
                    )
            except arrow.parser.ParserError:
                return self.error(
                    f"Cannot parse inputs quickUpdateStartTime ({quick_update_start_time}) "
                    f"or quickUpdateEndTime ({quick_update_end_time}) "
                    f"or fullUpdateStartTime ({full_update_start_time}) "
                    f"or fullUpdateEndTime ({full_update_end_time}) "
                    "as arrow parseable strings."
                )

            count_stmt = sa.select(func.count()).select_from(stmt.distinct().subquery())
            total_matches = await session.scalar(count_stmt)
            stmt = stmt.offset((page_number - 1) * num_per_page)
            stmt = stmt.limit(num_per_page)
            result = await session.scalars(stmt)
            objects = result.unique().all()

            current_obj_id = None
            try:
                for obj in objects:
                    current_obj_id = obj.id
                    photometry_result = await session.scalars(
                        sa.select(Photometry).where(Photometry.obj_id == obj.id)
                    )
                    photometry = photometry_result.all()
                    obj.photstats[0].full_update(photometry)
                    # make sure only one photstats per object
                    for j in range(1, len(obj.photstats)):
                        await session.delete(obj.photstats[j])
            except Exception as e:
                return self.error(
                    f"Error calculating photometry stats: {e} for object {current_obj_id}"
                )

            await session.commit()

        results = {
            "totalMatches": total_matches,
            "numPerPage": num_per_page,
            "pageNumber": page_number,
        }
        return self.success(data=results)


class PhotStatAggregateHandler(BaseHandler):
    @auth_or_token
    async def get(self, *, query: PhotStatAggregateGetQuery = None):
        """
        ---
        summary: Bulk photometry statistics for plotting
        description: |
          Return a compact set of PhotStat scalar fields across many accessible
          sources, optionally down-selected by classification, for bulk
          visualization (e.g. plotting peak magnitude against rise rate for all
          sources classified as SN Ia). Each source is colored by its
          highest-probability classification. Call without xField/yField to get
          the list of plottable fields only.
        tags:
          - photometry
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
        query = self.parse_query(PhotStatAggregateGetQuery)

        fields_meta = [
            {"value": value, "label": label}
            for value, label in PHOT_STAT_PLOT_FIELDS.items()
        ]

        x_field = query.xField
        y_field = query.yField
        z_field = query.zField

        # Metadata-only request: let the UI populate its axis dropdowns.
        if not x_field or not y_field:
            return self.success(
                data={
                    "fields": fields_meta,
                    "points": [],
                    "count": 0,
                    "truncated": False,
                }
            )

        to_check = [("xField", x_field), ("yField", y_field)]
        if z_field:
            to_check.append(("zField", z_field))
        for name, value in to_check:
            if value not in PHOT_STAT_PLOT_FIELDS:
                return self.error(f"Invalid {name}: {value}")

        classifications = query.classifications
        prob_threshold = query.classificationProbThreshold

        # Alternative source selections (used instead of classification): a group
        # or an explicit object list.
        group_id = query.group_id
        obj_ids = query.obj_ids
        if obj_ids:
            obj_ids = [o.strip() for o in obj_ids.split(",") if o.strip()]

        max_matches = max(1, min(query.maxMatches, MAX_AGGREGATE_POINTS))

        async with self.AsyncSession() as session:
            # Restrict to sources the user can access, and to classifications
            # they can see (non-ML), then color by the highest-probability one.
            # A group or explicit object list narrows the accessible source set.
            src = Source.select(self.current_user)
            if group_id is not None:
                src = src.where(Source.group_id == group_id)
            if obj_ids:
                src = src.where(Source.obj_id.in_(obj_ids))
            accessible_source_obj_ids = sa.select(src.subquery().c.obj_id)
            accessible_cls = (
                Classification.select(self.current_user)
                .where(Classification.ml.is_(False))
                .subquery()
            )
            primary_cls = (
                sa.select(
                    accessible_cls.c.obj_id,
                    accessible_cls.c.classification.label("classification"),
                )
                .order_by(
                    accessible_cls.c.obj_id,
                    accessible_cls.c.probability.desc().nullslast(),
                )
                .distinct(accessible_cls.c.obj_id)
                .subquery()
            )

            x_col = getattr(PhotStat, x_field)
            y_col = getattr(PhotStat, y_field)
            columns = [
                Obj.id.label("id"),
                Obj.ra.label("ra"),
                Obj.dec.label("dec"),
                Obj.redshift.label("redshift"),
                Obj.tns_info.label("tns_info"),
                PhotStat.first_detected_mjd.label("first_detected_mjd"),
                PhotStat.peak_mjd_global.label("peak_mjd"),
                x_col.label("x"),
                y_col.label("y"),
                primary_cls.c.classification.label("classification"),
            ]
            if z_field:
                columns.append(getattr(PhotStat, z_field).label("z"))

            stmt = (
                sa.select(*columns)
                .select_from(PhotStat)
                .join(Obj, Obj.id == PhotStat.obj_id)
                .outerjoin(primary_cls, primary_cls.c.obj_id == PhotStat.obj_id)
                .where(PhotStat.obj_id.in_(accessible_source_obj_ids))
                .where(x_col.isnot(None))
                .where(y_col.isnot(None))
            )
            if z_field:
                stmt = stmt.where(getattr(PhotStat, z_field).isnot(None))

            if classifications:
                names = [c.strip() for c in classifications.split(",") if c.strip()]
                if names:
                    match = sa.select(accessible_cls.c.obj_id).where(
                        accessible_cls.c.classification.in_(names)
                    )
                    if prob_threshold is not None:
                        match = match.where(
                            accessible_cls.c.probability >= prob_threshold
                        )
                    stmt = stmt.where(PhotStat.obj_id.in_(match))

            # Fetch one extra row to detect truncation.
            rows = (await session.execute(stmt.limit(max_matches + 1))).all()
            truncated = len(rows) > max_matches
            rows = rows[:max_matches]

            points = []
            for row in rows:
                point = {
                    "id": row.id,
                    "ra": row.ra,
                    "dec": row.dec,
                    "redshift": row.redshift,
                    "classification": row.classification,
                    # t0 candidates for phase-stacking spectra (SpectraAggregation).
                    "first_detected_mjd": row.first_detected_mjd,
                    "peak_mjd": row.peak_mjd,
                    "tns_discovery_date": (
                        (row.tns_info or {}).get("discoverydate")
                        if isinstance(row.tns_info, dict)
                        else None
                    ),
                    "x": row.x,
                    "y": row.y,
                }
                if z_field:
                    point["z"] = row.z
                points.append(point)

            return self.success(
                data={
                    "fields": fields_meta,
                    "points": points,
                    "count": len(points),
                    "truncated": truncated,
                }
            )
