import arrow
import sqlalchemy as sa

from baselayer.app.access import permissions

from ...models import (
    Annotation,
    Candidate,
    Classification,
    Comment,
    CronJobRun,
    Filter,
    FollowupRequest,
    GcnEvent,
    Group,
    Instrument,
    Obj,
    Source,
    SourceView,
    Spectrum,
    Telescope,
    Thumbnail,
    Token,
    User,
)
from ..base import BaseHandler

# Only models with an indexed created_at: bucketing photometry would sequential-scan it.
HISTORY_MODELS = {
    "candidates": Candidate,
    "sources": Source,
    "objs": Obj,
    "spectra": Spectrum,
    "classifications": Classification,
    "comments": Comment,
    "annotations": Annotation,
    "followup_requests": FollowupRequest,
    "gcn_events": GcnEvent,
    "source_views": SourceView,
    "users": User,
}

HISTORY_INTERVALS = ("hour", "day", "week", "month")

MAX_HISTORY_BINS = 2000


class StatsHandler(BaseHandler):
    @permissions(["System admin"])
    async def get(self):
        """
        ---
        summary: Get DB statistics
        description: Retrieve basic DB statistics
        tags:
          - system info
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
                            Number of candidates:
                              type: integer
                              description: Number of rows in candidates table
                            Number of objs:
                              type: integer
                              description: Number of rows in objs table
                            Number of sources:
                              type: integer
                              description: Number of rows in sources table
                            Number of photometry:
                              type: integer
                              description: Number of rows in photometry table
                            Number of spectra:
                              type: integer
                              description: Number of rows in spectra table
                            Number of groups:
                              type: integer
                              description: Number of rows in groups table
                            Number of users:
                              type: integer
                              description: Number of rows in users table
                            Number of tokens:
                              type: integer
                              description: Number of rows in tokens table
                            Oldest candidate creation datetime:
                              type: string
                              description: |
                                Datetime string corresponding to created_at column of
                                the oldest row in the candidates table.
                            Newest candidate creation datetime:
                              type: string
                              description: |
                                Datetime string corresponding to created_at column of
                                the newest row in the candidates table.
        """

        data = {}

        async with self.AsyncSession() as session:
            photometry_count_row = (
                await session.execute(
                    sa.text(
                        "SELECT reltuples::bigint FROM pg_catalog.pg_class WHERE relname = 'photometry'"
                    )
                )
            ).first()
            data["Number of photometry (approx)"] = photometry_count_row[0]

            data["Number of candidates"] = await session.scalar(
                sa.select(sa.func.count()).select_from(Candidate)
            )
            data["Number of sources"] = await session.scalar(
                sa.select(sa.func.count()).select_from(Source)
            )
            data["Number of source views"] = await session.scalar(
                sa.select(sa.func.count()).select_from(SourceView)
            )
            data["Number of objs"] = await session.scalar(
                sa.select(sa.func.count()).select_from(Obj)
            )
            data["Number of spectra"] = await session.scalar(
                sa.select(sa.func.count()).select_from(Spectrum)
            )
            data["Number of groups"] = await session.scalar(
                sa.select(sa.func.count()).select_from(Group)
            )
            data["Number of users"] = await session.scalar(
                sa.select(sa.func.count()).select_from(User)
            )
            data["Number of tokens"] = await session.scalar(
                sa.select(sa.func.count()).select_from(Token)
            )
            data["Number of filters"] = await session.scalar(
                sa.select(sa.func.count()).select_from(Filter)
            )
            data["Number of telescopes"] = await session.scalar(
                sa.select(sa.func.count()).select_from(Telescope)
            )
            data["Number of instruments"] = await session.scalar(
                sa.select(sa.func.count()).select_from(Instrument)
            )
            data["Number of comments"] = await session.scalar(
                sa.select(sa.func.count()).select_from(Comment)
            )
            data["Number of annotations"] = await session.scalar(
                sa.select(sa.func.count()).select_from(Annotation)
            )
            data["Number of thumbnails"] = await session.scalar(
                sa.select(sa.func.count()).select_from(Thumbnail)
            )
            data["Number of GCN events"] = await session.scalar(
                sa.select(sa.func.count()).select_from(GcnEvent)
            )
            data["Latest cron job run times & statuses"] = []
            cron_job_scripts = (
                await session.scalars(sa.select(CronJobRun.script).distinct())
            ).all()
            for script in cron_job_scripts:
                cron_job_run = (
                    await session.scalars(
                        sa.select(CronJobRun)
                        .where(CronJobRun.script == script)
                        .order_by(CronJobRun.created_at.desc())
                    )
                ).first()
                if cron_job_run is None:
                    continue
                data["Latest cron job run times & statuses"].append(
                    {
                        "summary": f"{script} ran at {cron_job_run.created_at} with exit status {cron_job_run.exit_status}",
                        "output": cron_job_run.output,
                    }
                )
            return self.success(data=data)


class StatsHistoryHandler(BaseHandler):
    @permissions(["System admin"])
    async def get(self):
        """
        ---
        summary: Get DB row counts per time interval
        description: |
          Number of rows added per time interval (bucketed on created_at) for a
          selection of tables, for plotting ingest rates on the DB Stats page.
          Buckets with no rows are returned with a count of zero.
        tags:
          - system info
        parameters:
          - in: query
            name: tables
            schema:
              type: string
            description: |
              Comma-separated list of tables to count. Defaults to `candidates`.
              Allowed values are returned in the `tables` field of the response.
          - in: query
            name: interval
            schema:
              type: string
              enum: [hour, day, week, month]
            description: Bucket width. Defaults to `day`.
          - in: query
            name: startDate
            schema:
              type: string
            description: |
              Arrow-parseable UTC datetime; only rows created at or after this
              time are counted. Defaults to 30 days ago.
          - in: query
            name: endDate
            schema:
              type: string
            description: |
              Arrow-parseable UTC datetime; only rows created before this time
              are counted. Defaults to now.
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
                            interval:
                              type: string
                            startDate:
                              type: string
                            endDate:
                              type: string
                            bins:
                              type: array
                              description: |
                                Start of each bucket, as a UTC datetime without
                                an offset (as are `startDate` and `endDate`).
                              items:
                                type: string
                            tables:
                              type: array
                              description: Every table this endpoint can count.
                              items:
                                type: string
                            counts:
                              type: object
                              description: |
                                Per requested table, one count per entry of `bins`.
                              additionalProperties:
                                type: array
                                items:
                                  type: integer
          400:
            content:
              application/json:
                schema: Error
        """
        interval = self.get_query_argument("interval", "day")
        if interval not in HISTORY_INTERVALS:
            return self.error(
                f"Invalid interval, must be one of {', '.join(HISTORY_INTERVALS)}"
            )

        tables = [
            name
            for table in self.get_query_argument("tables", "candidates").split(",")
            if (name := table.strip())
        ]
        if not tables:
            return self.error("At least one table must be requested")
        if unknown := [table for table in tables if table not in HISTORY_MODELS]:
            return self.error(
                f"Unknown table(s) {', '.join(unknown)}, must be one of "
                f"{', '.join(HISTORY_MODELS)}"
            )

        try:
            end = arrow.get(
                self.get_query_argument("endDate", None) or arrow.utcnow()
            ).to("utc")
            start = arrow.get(
                self.get_query_argument("startDate", None) or end.shift(days=-30)
            ).to("utc")
        except (arrow.parser.ParserError, ValueError) as e:
            return self.error(f"Invalid date: {e}")
        if start >= end:
            return self.error("startDate must be before endDate")

        # Bins align with date_trunc buckets, so the first can precede start.
        bins = []
        bin_start = start.floor(interval)
        while bin_start < end:
            bins.append(bin_start.naive)
            if len(bins) > MAX_HISTORY_BINS:
                return self.error(
                    f"Requested range spans more than {MAX_HISTORY_BINS} "
                    f"{interval} bins; narrow it or use a wider interval"
                )
            bin_start = bin_start.shift(**{f"{interval}s": 1})

        counts = {}
        async with self.AsyncSession() as session:
            for table in tables:
                created_at = HISTORY_MODELS[table].created_at
                bucket = sa.func.date_trunc(interval, created_at).label("bucket")
                rows = (
                    await session.execute(
                        sa.select(bucket, sa.func.count())
                        .where(created_at >= start.naive, created_at < end.naive)
                        .group_by(bucket)
                    )
                ).all()
                by_bucket = dict(rows)
                counts[table] = [by_bucket.get(b, 0) for b in bins]

        return self.success(
            data={
                "interval": interval,
                "startDate": start.naive.isoformat(),
                "endDate": end.naive.isoformat(),
                "bins": [b.isoformat() for b in bins],
                "tables": list(HISTORY_MODELS),
                "counts": counts,
            }
        )
