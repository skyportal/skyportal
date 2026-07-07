import arrow
import sqlalchemy as sa
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

log = make_log("api/source")

DEFAULT_SOURCES_PER_PAGE = 100
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
DEFAULT_AGGREGATE_POINTS = 20000


class PhotStatHandler(BaseHandler):
    @auth_or_token
    async def get(self, obj_id: str = None):
        """
        ---
        summary: Get photometry stats for a source
        description: retrieve the PhotStat associated with the obj_id.
        tags:
          - photometry
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
            description: object ID to get statistics on
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
    async def post(self, obj_id: str = None):
        """
        ---
        summary: Create new phot stats for a source
        description: create a new PhotStat to be associated with the obj_id.
        tags:
          - photometry
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
            description: object ID to get statistics on
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
    async def put(self, obj_id: str = None):
        """
        ---
        summary: Update phot stats for a source
        description: create or update the PhotStat associated with the obj_id.
        tags:
          - photometry
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
            description: object ID to get statistics on
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
    async def delete(self, obj_id: str = None):
        """
        ---
        summary: Delete phot stats of a source
        description: delete the PhotStat associated with the obj_id.
        tags:
          - photometry
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
            description: object ID to get statistics on
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
    async def get(self):
        """
        ---
        summary: Get counts of sources w/ and w/o PhotStats
        description: find the number of sources with and without a PhotStat object
        tags:
          - photometry
        parameters:
          - in: query
            name: createdAtStartTime
            required: false
            schema:
              type: string
            description: |
              arrow parseable string, only objects
              that have been created after this time
              will be checked for missing/existing PhotStats.
          - in: query
            name: createdAtEndTime
            required: false
            schema:
              type: string
            description: |
              arrow parseable string, only objects
              that have been created before this time
              will be checked for missing/existing PhotStats.
          - in: query
            name: quickUpdateStartTime
            required: false
            schema:
              type: string
            description: |
              arrow parseable string, any object's PhotStat
              that has been updated (either full update or
              an update at insert time) after this time
              will be recalculated.
          - in: query
            name: quickUpdateEndTime
            required: false
            schema:
              type: string
            description: |
              arrow parseable string, any object's PhotStat
              that has been updated (either full update or
              an update at insert time) before this time
              will be recalculated.
          - in: query
            name: fullUpdateStartTime
            required: false
            schema:
              type: string
            description: |
              arrow parseable string, any object's PhotStat
              that has been fully updated after this time
              will be counted.
          - in: query
            name: fullUpdateEndTime
            required: false
            schema:
              type: string
            description: |
              arrow parseable string, any object's PhotStat
              that has been fully updated before this time
              will be counted.
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
        created_at_start_time = self.get_query_argument("createdAtStartTime", None)
        created_at_end_time = self.get_query_argument("createdAtEndTime", None)
        quick_update_start_time = self.get_query_argument("quickUpdateStartTime", None)
        quick_update_end_time = self.get_query_argument("quickUpdateEndTime", None)
        full_update_start_time = self.get_query_argument("fullUpdateStartTime", None)
        full_update_end_time = self.get_query_argument("fullUpdateEndTime", None)

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
    async def post(self):
        """
        ---
        summary: Calculate phot stats for a batch of sources
        description: calculate photometric stats for a batch of sources without a PhotStat
        tags:
          - photometry
        parameters:
          - in: query
            name: numPerPage
            nullable: true
            schema:
              type: integer
            description: |
              Number of sources to check for updates. Defaults to 100. Max 500.
          - in: query
            name: pageNumber
            nullable: true
            schema:
              type: integer
            description: Page number for iterating through all sources. Defaults to 1
          - in: query
            name: createdAtStartTime
            required: false
            schema:
              type: string
            description: |
              arrow parseable string, only objects
              that have been created after this time
              will be checked for missing PhotStats.
          - in: query
            name: createdAtEndTime
            required: false
            schema:
              type: string
            description: |
              arrow parseable string, only objects
              that have been created before this time
              will be checked for missing PhotStats.
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

        page_number = self.get_query_argument("pageNumber", 1, type=int)
        num_per_page = self.get_query_argument(
            "numPerPage", DEFAULT_SOURCES_PER_PAGE, type=int
        )
        if page_number is None or num_per_page is None:
            return self.error(
                "Cannot parse inputs pageNumber or numPerPage as integers."
            )
        num_per_page = min(num_per_page, MAX_SOURCES_PER_PAGE)

        created_at_start_time = self.get_query_argument("createdAtStartTime", None)
        created_at_end_time = self.get_query_argument("createdAtEndTime", None)

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
    async def patch(self):
        """
        ---
        summary: Recalculate phot stats for a batch of sources
        description: manually recalculate the photometric stats for a batch of sources
        tags:
          - photometry
        parameters:
          - in: query
            name: numPerPage
            nullable: true
            schema:
              type: integer
            description: |
              Number of sources to check for updates. Defaults to 100. Max 500.
          - in: query
            name: pageNumber
            nullable: true
            schema:
              type: integer
            description: Page number for iterating through all sources. Defaults to 1
          - in: query
            name: createdAtStartTime
            required: false
            schema:
              type: string
            description: |
              arrow parseable string, only objects
              that have been created after this time
              will be checked for missing/existing PhotStats.
          - in: query
            name: createdAtEndTime
            required: false
            schema:
              type: string
            description: |
              arrow parseable string, only objects
              that have been created before this time
              will be checked for missing/existing PhotStats.
          - in: query
            name: quickUpdateStartTime
            required: false
            schema:
              type: string
            description: |
              arrow parseable string, any object's PhotStat
              that has been updated (either full update or
              an update at insert time) after this time
              will be recalculated.
          - in: query
            name: quickUpdateEndTime
            required: false
            schema:
              type: string
            description: |
              arrow parseable string, any object's PhotStat
              that has been updated (either full update or
              an update at insert time) before this time
              will be recalculated.
          - in: query
            name: fullUpdateStartTime
            required: false
            schema:
              type: string
            description: |
              arrow parseable string, any object's PhotStat
              that has been fully updated after this time
              will be recalculated.
          - in: query
            name: fullUpdateEndTime
            required: false
            schema:
              type: string
            description: |
              arrow parseable string, any object's PhotStat
              that has been fully updated before this time
              will be recalculated.
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

        page_number = self.get_query_argument("pageNumber", 1, type=int)
        num_per_page = self.get_query_argument(
            "numPerPage", DEFAULT_SOURCES_PER_PAGE, type=int
        )
        if page_number is None or num_per_page is None:
            return self.error(
                "Cannot parse inputs pageNumber or numPerPage as integers."
            )
        num_per_page = min(num_per_page, MAX_SOURCES_PER_PAGE)

        created_at_start_time = self.get_query_argument("createdAtStartTime", None)
        created_at_end_time = self.get_query_argument("createdAtEndTime", None)
        quick_update_start_time = self.get_query_argument("quickUpdateStartTime", None)
        quick_update_end_time = self.get_query_argument("quickUpdateEndTime", None)
        full_update_start_time = self.get_query_argument("fullUpdateStartTime", None)
        full_update_end_time = self.get_query_argument("fullUpdateEndTime", None)

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
    async def get(self):
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
        parameters:
          - in: query
            name: xField
            schema:
              type: string
            description: PhotStat field for the x axis (see the returned `fields`).
          - in: query
            name: yField
            schema:
              type: string
            description: PhotStat field for the y axis.
          - in: query
            name: zField
            schema:
              type: string
            description: Optional PhotStat field for a third (z) axis.
          - in: query
            name: classifications
            schema:
              type: string
            description: |
              Comma-separated classification names to down-select sources
              (matches any). Omit to include all accessible sources.
          - in: query
            name: classificationProbThreshold
            schema:
              type: number
            description: Only count classifications at or above this probability.
          - in: query
            name: maxMatches
            schema:
              type: integer
            description: |
              Maximum number of points to return (default 20000, capped at
              100000). If more match, the response is truncated.
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
        fields_meta = [
            {"value": value, "label": label}
            for value, label in PHOT_STAT_PLOT_FIELDS.items()
        ]

        x_field = self.get_query_argument("xField", None)
        y_field = self.get_query_argument("yField", None)
        z_field = self.get_query_argument("zField", None)

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

        classifications = self.get_query_argument("classifications", None)
        prob_threshold = self.get_query_argument("classificationProbThreshold", None)
        if prob_threshold is not None:
            try:
                prob_threshold = float(prob_threshold)
            except ValueError:
                return self.error("classificationProbThreshold must be a number")

        try:
            max_matches = int(
                self.get_query_argument("maxMatches", DEFAULT_AGGREGATE_POINTS)
            )
        except ValueError:
            return self.error("maxMatches must be an integer")
        max_matches = max(1, min(max_matches, MAX_AGGREGATE_POINTS))

        async with self.AsyncSession() as session:
            # Restrict to sources the user can access, and to classifications
            # they can see (non-ML), then color by the highest-probability one.
            accessible_source_obj_ids = sa.select(
                Source.select(self.current_user).subquery().c.obj_id
            )
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
                x_col.label("x"),
                y_col.label("y"),
                primary_cls.c.classification.label("classification"),
            ]
            if z_field:
                columns.append(getattr(PhotStat, z_field).label("z"))

            query = (
                sa.select(*columns)
                .select_from(PhotStat)
                .join(Obj, Obj.id == PhotStat.obj_id)
                .outerjoin(primary_cls, primary_cls.c.obj_id == PhotStat.obj_id)
                .where(PhotStat.obj_id.in_(accessible_source_obj_ids))
                .where(x_col.isnot(None))
                .where(y_col.isnot(None))
            )
            if z_field:
                query = query.where(getattr(PhotStat, z_field).isnot(None))

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
                    query = query.where(PhotStat.obj_id.in_(match))

            # Fetch one extra row to detect truncation.
            rows = (await session.execute(query.limit(max_matches + 1))).all()
            truncated = len(rows) > max_matches
            rows = rows[:max_matches]

            points = []
            for row in rows:
                point = {
                    "id": row.id,
                    "ra": row.ra,
                    "dec": row.dec,
                    "classification": row.classification,
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
