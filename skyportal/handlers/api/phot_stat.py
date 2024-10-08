import arrow
import sqlalchemy as sa
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from ..base import BaseHandler
from ...models import (
    Obj,
    Photometry,
    PhotStat,
)
from baselayer.app.access import permissions, auth_or_token
from baselayer.log import make_log

log = make_log('api/source')

DEFAULT_SOURCES_PER_PAGE = 100
MAX_SOURCES_PER_PAGE = 500


class PhotStatHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id=None):
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
                schema: PhotStat
          400:
              content:
                application/json:
                  schema: Error

        """

        with self.Session() as session:
            obj = session.scalars(
                Obj.select(self.current_user).where(Obj.id == obj_id)
            ).first()
            if obj is None:
                return self.error(f'Cannot find source with id "{obj_id}". ')

            stmt = sa.select(PhotStat).where(PhotStat.obj_id == obj_id)
            phot_stat = session.scalars(stmt).first()

            if phot_stat is None:
                return self.error(
                    f'Could not find a PhotStat for object with id "{obj_id}". '
                )

            # this is a non-permissioned query:
            # it will get the time of the latest photometry
            # regardless of the user's permissions to view it.
            stmt = (
                sa.select(Photometry)
                .where(Photometry.obj_id == obj_id)
                .order_by(Photometry.created_at.desc())
            )
            last_photometry = session.scalars(stmt).first()
            if last_photometry:
                phot_stat.last_phot_add_time = last_photometry.created_at
            else:
                phot_stat.last_phot_add_time = None

        return self.success(data=phot_stat)

    @permissions(['system admin'])
    def post(self, obj_id=None):
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
        with self.Session() as session:
            obj = session.scalars(
                Obj.select(self.current_user).where(Obj.id == obj_id)
            ).first()
            if obj is None:
                return self.error(f'Cannot find source with id "{obj_id}". ')

            stmt = sa.select(PhotStat).where(PhotStat.obj_id == obj_id)
            phot_stat = session.scalars(stmt).first()
            if phot_stat is not None:
                return self.error(
                    f'PhotStat for object with id "{obj_id}" already exists. '
                )

            stmt = sa.select(Photometry).where(Photometry.obj_id == obj_id)
            photometry = session.scalars(stmt).all()

            phot_stat = PhotStat(obj_id=obj_id)
            phot_stat.full_update(photometry)
            session.add(phot_stat)
            session.commit()

        return self.success()

    @permissions(['system admin'])
    def put(self, obj_id=None):
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

        with self.Session() as session:
            obj = session.scalars(
                Obj.select(self.current_user).where(Obj.id == obj_id)
            ).first()
            if obj is None:
                return self.error(f'Cannot find source with id "{obj_id}". ')

            stmt = sa.select(PhotStat).where(PhotStat.obj_id == obj_id)
            phot_stat = session.scalars(stmt).first()
            if phot_stat is None:
                phot_stat = PhotStat(obj_id=obj_id)

            stmt = sa.select(Photometry).where(Photometry.obj_id == obj_id)
            photometry = session.scalars(stmt).all()
            phot_stat.full_update(photometry)
            session.add(phot_stat)
            session.commit()

        return self.success()

    @permissions(['system admin'])
    def delete(self, obj_id=None):
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
        with self.Session() as session:
            obj = session.scalars(
                Obj.select(self.current_user).where(Obj.id == obj_id)
            ).first()
            if obj is None:
                return self.error(f'Cannot find source with id "{obj_id}". ')

            stmt = sa.select(PhotStat).where(PhotStat.obj_id == obj_id)
            phot_stats = session.scalars(stmt).all()
            if phot_stats is None:
                return self.error(
                    f'Could not find a PhotStat for object with id "{obj_id}". '
                )
            for p in phot_stats:
                session.delete(p)

            session.commit()

        return self.success()


class PhotStatUpdateHandler(BaseHandler):
    @permissions(['System admin'])
    def get(self):
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
        created_at_start_time = self.get_query_argument('createdAtStartTime', None)
        created_at_end_time = self.get_query_argument('createdAtEndTime', None)
        quick_update_start_time = self.get_query_argument('quickUpdateStartTime', None)
        quick_update_end_time = self.get_query_argument('quickUpdateEndTime', None)
        full_update_start_time = self.get_query_argument('fullUpdateStartTime', None)
        full_update_end_time = self.get_query_argument('fullUpdateEndTime', None)

        with self.Session() as session:
            try:
                # start with Objs that have created_at within range
                stmt = sa.select(Obj).options(joinedload(Obj.photstats))
                if created_at_start_time:
                    created_at_start_time = str(
                        arrow.get(created_at_start_time.strip()).datetime
                    )
                    stmt = stmt.where(Obj.created_at >= created_at_start_time)
                if created_at_end_time:
                    created_at_end_time = str(
                        arrow.get(created_at_end_time.strip()).datetime
                    )
                    stmt = stmt.where(Obj.created_at <= created_at_end_time)
            except arrow.parser.ParserError:
                return self.error(
                    f'Cannot parse inputs createdAtStartTime ({created_at_start_time}) '
                    f'or createdAtEndTime ({created_at_end_time}) as arrow parseable strings.'
                )

            # select only objects that don't have a PhotStats object
            stmt_without = stmt.where(~Obj.photstats.any())
            count_stmt = sa.select(func.count()).select_from(stmt_without)
            total_missing = session.execute(count_stmt).scalar()

            # get the number of Objs with PhotStats
            # (that have created_at within range,
            # and that have update times within range)
            stmt_with = stmt.where(Obj.photstats.any())
            try:
                if quick_update_start_time:
                    quick_update_start_time = str(
                        arrow.get(quick_update_start_time.strip()).datetime
                    )
                    stmt_with = stmt_with.where(
                        Obj.photstats.any(
                            PhotStat.last_update >= quick_update_start_time
                        )
                    )
                if quick_update_end_time:
                    quick_update_end_time = str(
                        arrow.get(quick_update_end_time.strip()).datetime
                    )
                    stmt_with = stmt_with.where(
                        Obj.photstats.any(PhotStat.last_update <= quick_update_end_time)
                    )
                if full_update_start_time:
                    full_update_start_time = str(
                        arrow.get(full_update_start_time.strip()).datetime
                    )
                    stmt_with = stmt_with.where(
                        Obj.photstats.any(
                            PhotStat.last_full_update >= full_update_start_time
                        )
                    )
                if full_update_end_time:
                    full_update_end_time = str(
                        arrow.get(full_update_end_time.strip()).datetime
                    )
                    stmt_with = stmt_with.where(
                        Obj.photstats.any(
                            PhotStat.last_full_update <= full_update_end_time
                        )
                    )
            except arrow.parser.ParserError:
                return self.error(
                    f'Cannot parse inputs quickUpdateStartTime ({quick_update_start_time}) '
                    f'or quickUpdateEndTime ({quick_update_end_time}) '
                    f'or fullUpdateStartTime ({full_update_start_time}) '
                    f'or fullUpdateEndTime ({full_update_end_time}) '
                    'as arrow parseable strings.'
                )
            count_stmt = sa.select(func.count()).select_from(stmt_with.distinct())
            total_phot_stats = session.execute(count_stmt).scalar()

        results = {
            'totalWithoutPhotStats': total_missing,
            'totalWithPhotStats': total_phot_stats,
        }
        return self.success(data=results)

    @permissions(['System admin'])
    def post(self):
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

        try:
            page_number = int(self.get_query_argument('pageNumber', 1))
            num_per_page = min(
                int(self.get_query_argument("numPerPage", DEFAULT_SOURCES_PER_PAGE)),
                MAX_SOURCES_PER_PAGE,
            )
        except ValueError:
            return self.error(
                f'Cannot parse inputs pageNumber ({page_number}) '
                f'or numPerPage ({num_per_page}) as an integers.'
            )

        created_at_start_time = self.get_query_argument('createdAtStartTime', None)
        created_at_end_time = self.get_query_argument('createdAtEndTime', None)

        with self.Session() as session:
            stmt = sa.select(Obj).options(joinedload(Obj.photstats))
            try:
                if created_at_start_time:
                    created_at_start_time = str(
                        arrow.get(created_at_start_time.strip()).datetime
                    )
                    stmt = stmt.where(Obj.created_at >= created_at_start_time)
                if created_at_end_time:
                    created_at_end_time = str(
                        arrow.get(created_at_end_time.strip()).datetime
                    )
                    stmt = stmt.where(Obj.created_at <= created_at_end_time)
            except arrow.parser.ParserError:
                return self.error(
                    f'Cannot parse inputs createdAtStartTime ({created_at_start_time}) '
                    f'or createdAtEndTime ({created_at_end_time}) as arrow parseable strings.'
                )

            # select only objects that don't have a PhotStats object
            stmt = stmt.where(~Obj.photstats.any())

            count_stmt = sa.select(func.count()).select_from(stmt)
            total_matches = session.execute(count_stmt).scalar()
            stmt = stmt.offset((page_number - 1) * num_per_page)
            stmt = stmt.limit(num_per_page)
            objects = session.execute(stmt).scalars().unique().all()

            try:
                for i, obj in enumerate(objects):
                    stmt = sa.select(Photometry).where(Photometry.obj_id == obj.id)
                    photometry = session.scalars(stmt).all()
                    phot_stat = PhotStat(obj_id=obj.id)
                    phot_stat.full_update(photometry)
                    session.add(phot_stat)
            except Exception as e:
                return self.error(
                    f'Error calculating photometry stats: {e} for object {obj.id}'
                )

            session.commit()

        results = {
            'totalMatches': total_matches,
            'numPerPage': num_per_page,
            'pageNumber': page_number,
        }
        return self.success(data=results)

    @permissions(['System admin'])
    def patch(self):
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

        try:
            page_number = int(self.get_query_argument('pageNumber', 1))
            num_per_page = min(
                int(self.get_query_argument("numPerPage", DEFAULT_SOURCES_PER_PAGE)),
                MAX_SOURCES_PER_PAGE,
            )
        except ValueError:
            return self.error(
                f'Cannot parse inputs pageNumber ({page_number}) '
                f'or numPerPage ({num_per_page}) as an integers.'
            )

        created_at_start_time = self.get_query_argument('createdAtStartTime', None)
        created_at_end_time = self.get_query_argument('createdAtEndTime', None)
        quick_update_start_time = self.get_query_argument('quickUpdateStartTime', None)
        quick_update_end_time = self.get_query_argument('quickUpdateEndTime', None)
        full_update_start_time = self.get_query_argument('fullUpdateStartTime', None)
        full_update_end_time = self.get_query_argument('fullUpdateEndTime', None)

        with self.Session() as session:
            stmt = sa.select(Obj).options(joinedload(Obj.photstats))
            try:
                if created_at_start_time:
                    created_at_start_time = str(
                        arrow.get(created_at_start_time.strip()).datetime
                    )
                    stmt = stmt.where(Obj.created_at >= created_at_start_time)
                if created_at_end_time:
                    created_at_end_time = str(
                        arrow.get(created_at_end_time.strip()).datetime
                    )
                    stmt = stmt.where(Obj.created_at <= created_at_end_time)
            except arrow.parser.ParserError:
                return self.error(
                    f'Cannot parse inputs createdAtStartTime ({created_at_start_time}) '
                    f'or createdAtEndTime ({created_at_end_time}) as arrow parseable strings.'
                )

            # only look at Objs with a PhotStat
            stmt = stmt.where(Obj.photstats.any())
            try:
                if quick_update_start_time:
                    quick_update_start_time = str(
                        arrow.get(quick_update_start_time.strip()).datetime
                    )
                    stmt = stmt.where(
                        Obj.photstats.any(
                            PhotStat.last_update >= quick_update_start_time
                        )
                    )
                if quick_update_end_time:
                    quick_update_end_time = str(
                        arrow.get(quick_update_end_time.strip()).datetime
                    )
                    stmt = stmt.where(
                        Obj.photstats.any(PhotStat.last_update <= quick_update_end_time)
                    )
                if full_update_start_time:
                    full_update_start_time = str(
                        arrow.get(full_update_start_time.strip()).datetime
                    )
                    stmt = stmt.where(
                        Obj.photstats.any(
                            PhotStat.last_full_update >= full_update_start_time
                        )
                    )
                if full_update_end_time:
                    full_update_end_time = str(
                        arrow.get(full_update_end_time.strip()).datetime
                    )
                    stmt = stmt.where(
                        Obj.photstats.any(
                            PhotStat.last_full_update <= full_update_end_time
                        )
                    )
            except arrow.parser.ParserError:
                return self.error(
                    f'Cannot parse inputs quickUpdateStartTime ({quick_update_start_time}) '
                    f'or quickUpdateEndTime ({quick_update_end_time}) '
                    f'or fullUpdateStartTime ({full_update_start_time}) '
                    f'or fullUpdateEndTime ({full_update_end_time}) '
                    'as arrow parseable strings.'
                )

            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            total_matches = session.execute(count_stmt).scalar()
            stmt = stmt.offset((page_number - 1) * num_per_page)
            stmt = stmt.limit(num_per_page)
            objects = session.scalars(stmt).unique().all()

            try:
                for i, obj in enumerate(objects):
                    stmt = sa.select(Photometry).where(Photometry.obj_id == obj.id)
                    photometry = session.scalars(stmt).all()
                    obj.photstats[0].full_update(photometry)
                    # make sure only one photstats per object
                    for j in range(1, len(obj.photstats)):
                        session.delete(obj.photstats[j])
            except Exception as e:
                return self.error(
                    f'Error calculating photometry stats: {e} for object {obj.id}'
                )

            session.commit()

        results = {
            'totalMatches': total_matches,
            'numPerPage': num_per_page,
            'pageNumber': page_number,
        }
        return self.success(data=results)
