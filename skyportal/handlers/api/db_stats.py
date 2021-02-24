from baselayer.app.access import permissions
from ..base import BaseHandler
from ...models import (
    DBSession,
    Obj,
    Source,
    Candidate,
    User,
    Token,
    Group,
    Spectrum,
    CronJobRun,
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
        data["Number of candidates"] = Candidate.query.count()
        data["Number of sources"] = Source.query.count()
        data["Number of objs"] = Obj.query.count()
        data["Number of photometry (approx)"] = list(
            DBSession().execute(
                "SELECT reltuples::bigint FROM pg_catalog.pg_class WHERE relname = 'photometry'"
            )
        )[0][0]
        data["Number of spectra"] = Spectrum.query.count()
        data["Number of groups"] = Group.query.count()
        data["Number of users"] = User.query.count()
        data["Number of tokens"] = Token.query.count()
        cand = Candidate.query.order_by(Candidate.created_at).first()
        data["Oldest candidate creation datetime"] = (
            cand.created_at if cand is not None else None
        )
        cand = Candidate.query.order_by(Candidate.created_at.desc()).first()
        data["Newest candidate creation datetime"] = (
            cand.created_at if cand is not None else None
        )
        data["Latest cron job run times & statuses"] = []
        cron_job_scripts = DBSession().query(CronJobRun.script).distinct().all()
        for script in cron_job_scripts:
            cron_job_run = (
                CronJobRun.query.filter(CronJobRun.script == script[0])
                .order_by(CronJobRun.created_at.desc())
                .first()
            )
            data["Latest cron job run times & statuses"].append(
                {
                    "summary": f"{script[0]} ran at {cron_job_run.created_at} with exit status {cron_job_run.exit_status}",
                    "output": cron_job_run.output,
                }
            )
        return self.success(data=data)
