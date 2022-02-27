import sqlalchemy as sa
from baselayer.app.access import permissions

from ..base import BaseHandler
from ...models import (
    DBSession,
    User,
    CronJobRun,
    Obj,
    Source,
    Candidate,
    Token,
    Group,
    Spectrum,
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
        data["Number of candidates"] = DBSession().scalar(
            sa.select(sa.func.count()).select_from(Candidate)
        )
        data["Number of sources"] = DBSession().scalar(
            sa.select(sa.func.count()).select_from(Source)
        )
        data["Number of objs"] = DBSession().scalar(
            sa.select(sa.func.count()).select_from(Obj)
        )
        data["Number of photometry (approx)"] = list(
            DBSession().execute(
                "SELECT reltuples::bigint FROM pg_catalog.pg_class WHERE relname = 'photometry'"
            )
        )[0][0]
        data["Number of spectra"] = DBSession().scalar(
            sa.select(sa.func.count()).select_from(Spectrum)
        )
        data["Number of groups"] = DBSession().scalar(
            sa.select(sa.func.count()).select_from(Group)
        )
        data["Number of users"] = DBSession().scalar(
            sa.select(sa.func.count()).select_from(User)
        )
        data["Number of tokens"] = DBSession().scalar(
            sa.select(sa.func.count()).select_from(Token)
        )
        cand = (
            DBSession()
            .execute(sa.select(Candidate).order_by(Candidate.created_at))
            .first()
        )
        if cand is not None:
            (cand,) = cand
        data["Oldest candidate creation datetime"] = (
            cand.created_at if cand is not None else None
        )
        cand = (
            DBSession()
            .execute(sa.select(Candidate).order_by(Candidate.created_at.desc()))
            .first()
        )
        if cand is not None:
            (cand,) = cand
        data["Newest candidate creation datetime"] = (
            cand.created_at if cand is not None else None
        )
        cand = (
            DBSession()
            .execute(
                sa.select(Candidate)
                .where(Candidate.obj_id.notin_(sa.select(Source.obj_id).subquery()))
                .order_by(Candidate.created_at)
            )
            .first()
        )
        if cand is not None:
            (cand,) = cand

        data["Oldest unsaved candidate creation datetime"] = (
            cand.created_at if cand is not None else None
        )
        data["Latest cron job run times & statuses"] = []
        cron_job_scripts = (
            DBSession().execute(sa.select(CronJobRun.script).distinct()).all()
        )
        for (script,) in cron_job_scripts:
            cron_job_run = (
                DBSession()
                .execute(
                    sa.select(CronJobRun)
                    .where(CronJobRun.script == script)
                    .order_by(CronJobRun.created_at.desc())
                )
                .first()
            )
            if cron_job_run is not None:
                (cron_job_run,) = cron_job_run
            data["Latest cron job run times & statuses"].append(
                {
                    "summary": f"{script} ran at {cron_job_run.created_at} with exit status {cron_job_run.exit_status}",
                    "output": cron_job_run.output,
                }
            )
        return self.success(data=data)
