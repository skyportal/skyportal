import sqlalchemy as sa

from baselayer.app.access import permissions

from ...models import (
    Annotation,
    Candidate,
    Comment,
    CronJobRun,
    Filter,
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
