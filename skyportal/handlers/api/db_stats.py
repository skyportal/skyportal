import datetime
from astropy.time import Time
from penquins import Kowalski

from baselayer.app.access import permissions
from baselayer.app.env import load_env
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


_, cfg = load_env()

if cfg.get('app.kowalski.enabled', False):
    kowalski = Kowalski(
        token=cfg["app.kowalski.token"],
        protocol=cfg["app.kowalski.protocol"],
        host=cfg["app.kowalski.host"],
        port=int(cfg["app.kowalski.port"]),
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
        cand = (
            DBSession()
            .query(Candidate)
            .filter(Candidate.obj_id.notin_(DBSession.query(Source.obj_id)))
            .order_by(Candidate.created_at)
            .first()
        )
        data["Oldest unsaved candidate creation datetime"] = (
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

        query_tns_count = {
            "query_type": "count_documents",
            "query": {
                "catalog": "TNS",
                "filter": {},
            },
        }
        response = kowalski.query(query=query_tns_count)
        data["Number of objects in TNS collection"] = response.get("data")

        query_tns_latest_object = {
            "query_type": "find",
            "query": {
                "catalog": "TNS",
                "filter": {},
                "projection": {"_id": 0, "discovery_date_(ut)": 1},
            },
            "kwargs": {"sort": [("discovery_date", -1)], "limit": 1},
        }
        response = kowalski.query(query=query_tns_latest_object)
        response_data = response.get("data", [])
        latest_tns_object_discovery_date = (
            response_data[0]["discovery_date_(ut)"] if len(response_data) > 0 else None
        )
        data[
            "Latest object from TNS collection discovery date (UTC)"
        ] = latest_tns_object_discovery_date

        for survey in ("PGIR", "ZTF"):
            utc_now = datetime.datetime.utcnow()
            jd_start = Time(
                datetime.datetime(utc_now.year, utc_now.month, utc_now.day)
            ).jd
            query_alerts_count = {
                "query_type": "count_documents",
                "query": {
                    "catalog": f"{survey}_alerts",
                    "filter": {
                        "candidate.jd": {
                            "$gt": jd_start - 1,
                            "$lt": jd_start,
                        }
                    },
                },
            }
            response = kowalski.query(query=query_alerts_count)
            data[f"Number of {survey} alerts ingested yesterday (UTC)"] = response.get(
                "data"
            )

            query_alerts_count = {
                "query_type": "count_documents",
                "query": {
                    "catalog": f"{survey}_alerts",
                    "filter": {
                        "candidate.jd": {
                            "$gt": jd_start,
                        }
                    },
                },
            }
            response = kowalski.query(query=query_alerts_count)
            data[
                f"Number of {survey} alerts ingested since 0h UTC today"
            ] = response.get("data")

        return self.success(data=data)
