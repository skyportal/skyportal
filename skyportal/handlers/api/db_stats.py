import sqlalchemy as sa

from baselayer.app.access import permissions

from ..base import BaseHandler
from ...models import (
    ThreadSession,
    User,
    Annotation,
    Comment,
    CronJobRun,
    Filter,
    Instrument,
    Obj,
    Source,
    Candidate,
    Token,
    GcnEvent,
    Group,
    Spectrum,
    SourceView,
    Telescope,
    Thumbnail,
)


class StatsHandler(BaseHandler):
    @permissions(["System admin"])
    def get(self):
        """
        ---
        description: Retrieve basic DB statistics
        tags:
          - system_info
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

        # This query is done in raw session as it directly executes
        # sql, which is unsupported by the self.Session() syntax
        with ThreadSession() as session:
            data["Number of photometry (approx)"] = list(
                session.execute(
                    sa.text(
                        "SELECT reltuples::bigint FROM pg_catalog.pg_class WHERE relname = 'photometry'"
                    )
                )
            )[0][0]

        with self.Session() as session:
            data["Number of candidates"] = session.scalar(
                sa.select(sa.func.count()).select_from(Candidate)
            )
            data["Number of sources"] = session.scalar(
                sa.select(sa.func.count()).select_from(Source)
            )
            data["Number of source views"] = session.scalar(
                sa.select(sa.func.count()).select_from(SourceView)
            )
            data["Number of objs"] = session.scalar(
                sa.select(sa.func.count()).select_from(Obj)
            )
            data["Number of spectra"] = session.scalar(
                sa.select(sa.func.count()).select_from(Spectrum)
            )
            data["Number of groups"] = session.scalar(
                sa.select(sa.func.count()).select_from(Group)
            )
            data["Number of users"] = session.scalar(
                sa.select(sa.func.count()).select_from(User)
            )
            data["Number of tokens"] = session.scalar(
                sa.select(sa.func.count()).select_from(Token)
            )
            data["Number of filters"] = session.scalar(
                sa.select(sa.func.count()).select_from(Filter)
            )
            data["Number of telescopes"] = session.scalar(
                sa.select(sa.func.count()).select_from(Telescope)
            )
            data["Number of instruments"] = session.scalar(
                sa.select(sa.func.count()).select_from(Instrument)
            )
            data["Number of comments"] = session.scalar(
                sa.select(sa.func.count()).select_from(Comment)
            )
            data["Number of annotations"] = session.scalar(
                sa.select(sa.func.count()).select_from(Annotation)
            )
            data["Number of thumbnails"] = session.scalar(
                sa.select(sa.func.count()).select_from(Thumbnail)
            )
            data["Number of GCN events"] = session.scalar(
                sa.select(sa.func.count()).select_from(GcnEvent)
            )
            data["Latest cron job run times & statuses"] = []
            cron_job_scripts = session.execute(
                sa.select(CronJobRun.script).distinct()
            ).all()
            for script in cron_job_scripts:
                cron_job_run = session.execute(
                    sa.select(CronJobRun)
                    .where(CronJobRun.script == script)
                    .order_by(CronJobRun.created_at.desc())
                ).first()
                if cron_job_run is not None:
                    (cron_job_run,) = cron_job_run
                data["Latest cron job run times & statuses"].append(
                    {
                        "summary": f"{script} ran at {cron_job_run.created_at} with exit status {cron_job_run.exit_status}",
                        "output": cron_job_run.output,
                    }
                )
            return self.success(data=data)
