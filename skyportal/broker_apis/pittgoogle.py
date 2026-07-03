import json

from baselayer.log import make_log

from .interface import BrokerAPI

log = make_log("broker/pittgoogle")

# Pitt-Google's public BigQuery archive of the ZTF alert stream (queries run under
# the user's own project/billing; the data lives in Pitt-Google's project).
DEFAULT_TABLE = "ardent-cycling-243415.ztf.alerts_v4_02"
_FID_TO_BAND = {1: "g", 2: "r", 3: "i"}


def _client(broker):
    """Build a BigQuery client from ``broker.altdata`` (a service-account key +
    project id). Lazy imports so google-cloud-bigquery is only needed by
    deployments that use Pitt-Google."""
    from google.cloud import bigquery
    from google.oauth2 import service_account

    altdata = broker.altdata or {}
    key = altdata.get("service_account_key")
    project = altdata.get("project_id")
    if not key or not project:
        raise ValueError(
            "Broker altdata must include 'service_account_key' and 'project_id'."
        )
    if isinstance(key, str):
        key = json.loads(key)
    creds = service_account.Credentials.from_service_account_info(key)
    return bigquery.Client(project=project, credentials=creds)


def _table(broker):
    return (broker.altdata or {}).get("table", DEFAULT_TABLE)


def _run(broker, sql, params):
    from google.cloud import bigquery

    client = _client(broker)
    job = client.query(sql, job_config=bigquery.QueryJobConfig(query_parameters=params))
    return [dict(row) for row in job.result()]


def _normalize_rows(object_id, rows):
    """Reshape BigQuery alert rows (one candidate per row: jd/fid/magpsf/sigmapsf/
    ra/decl) into the standard {objectId, candidate, prv_candidates} shape."""
    prv = [
        {
            "jd": r.get("jd"),
            "magpsf": r.get("magpsf"),
            "sigmapsf": r.get("sigmapsf"),
            "band": _FID_TO_BAND.get(r.get("fid")),
            "ra": r.get("ra"),
            "dec": r.get("decl"),
        }
        for r in rows
        if r.get("magpsf") is not None
    ]
    prv.sort(key=lambda d: d["jd"] or 0)
    latest = prv[-1] if prv else {}
    return {
        "objectId": object_id,
        "candidate": {
            "ra": latest.get("ra"),
            "dec": latest.get("dec"),
            "magpsf": latest.get("magpsf"),
            "jd": latest.get("jd"),
            "band": latest.get("band"),
        },
        "prv_candidates": prv,
    }


def _pt(c):
    return {
        "jd": c.get("jd"),
        "magpsf": c.get("magpsf"),
        "sigmapsf": c.get("sigmapsf"),
        "band": _FID_TO_BAND.get(c.get("fid")),
        "ra": c.get("ra"),
        "dec": c.get("dec"),
    }


def _normalize_pubsub_alert(alert):
    """Reshape a streamed ZTF avro alert (a ``pittgoogle.Alert``) into the standard
    shape + extract its cutouts (gzipped FITS). Returns (data, candid, cutouts)."""
    d = getattr(alert, "dict", None) or {}
    object_id = d.get("objectId")
    if object_id is None:
        return None, None, None
    cand = d.get("candidate") or {}
    prv = [_pt(cand)] + [
        _pt(c) for c in (d.get("prv_candidates") or []) if c.get("magpsf") is not None
    ]
    data = {
        "objectId": object_id,
        "candidate": {
            "ra": cand.get("ra"),
            "dec": cand.get("dec"),
            "magpsf": cand.get("magpsf"),
            "jd": cand.get("jd"),
            "band": _FID_TO_BAND.get(cand.get("fid")),
        },
        "prv_candidates": prv,
    }
    cutouts = {}
    for field in ("cutoutScience", "cutoutTemplate", "cutoutDifference"):
        c = d.get(field)
        blob = c.get("stampData") if isinstance(c, dict) else c
        if blob:
            cutouts[field] = blob
    return data, cand.get("candid"), (cutouts or None)


class PITTGOOGLEBROKER(BrokerAPI):
    """The Pitt-Google broker (Google Cloud, ZTF alerts).

    Interactive access via BigQuery over Pitt-Google's public alert archive.
    Requires a Google Cloud **service-account key** (JSON) + your **project_id**
    (queries bill your project; BigQuery has a free tier). Configure a ``Broker``
    with ``altdata = {"service_account_key": <JSON>, "project_id": "...",
    "table": "..."}``. Cutouts (Cloud Storage) and Pub/Sub ingestion are not yet
    implemented.
    """

    surveys = ["ZTF"]

    form_json_schema_config = {
        "type": "object",
        "required": ["service_account_key", "project_id"],
        "properties": {
            "project_id": {
                "type": "string",
                "title": "Your GCP project id (queries bill this project)",
            },
            "service_account_key": {
                "type": "string",
                "title": "Service-account key (paste the JSON)",
            },
            "table": {
                "type": "string",
                "title": "BigQuery alerts table",
                "default": DEFAULT_TABLE,
            },
            "subscription": {
                "type": "string",
                "title": "Pub/Sub subscription (for ingestion)",
            },
            "survey": {"type": "string", "enum": ["ZTF"], "default": "ZTF"},
        },
    }

    ui_json_schema = {"service_account_key": {"ui:widget": "textarea"}}

    @staticmethod
    def validate_config(altdata):
        altdata = altdata or {}
        for key in ("service_account_key", "project_id"):
            if not altdata.get(key):
                raise ValueError(f"Broker altdata must include '{key}'.")

    @staticmethod
    def query_alerts(broker, session, **kwargs):
        object_id = kwargs.get("objectId") or kwargs.get("object_id")
        if object_id:
            return [PITTGOOGLEBROKER.get_alert(broker, object_id, session, **kwargs)]
        ra, dec = kwargs.get("ra"), kwargs.get("dec")
        if ra is not None and dec is not None:
            return PITTGOOGLEBROKER.cone_search(
                broker, ra, dec, kwargs.get("radius", 5), session, **kwargs
            )
        raise ValueError("Provide objectId, or ra+dec.")

    @staticmethod
    def get_alert(broker, alert_id, session, **kwargs):
        from google.cloud import bigquery

        sql = f"""
            SELECT candidate.jd AS jd, candidate.fid AS fid,
                   candidate.magpsf AS magpsf, candidate.sigmapsf AS sigmapsf,
                   candidate.ra AS ra, candidate.dec AS decl
            FROM `{_table(broker)}`
            WHERE objectId = @objectId
            ORDER BY candidate.jd
        """
        params = [bigquery.ScalarQueryParameter("objectId", "STRING", alert_id)]
        return _normalize_rows(alert_id, _run(broker, sql, params))

    @staticmethod
    def cone_search(broker, ra, dec, radius, session, **kwargs):
        from google.cloud import bigquery

        # Haversine angular separation (arcsec), with a declination bounding box
        # to bound the scan. Note: a cone over the full table can be costly.
        sql = f"""
            SELECT objectId, candidate.jd AS jd, candidate.fid AS fid,
                   candidate.magpsf AS magpsf, candidate.sigmapsf AS sigmapsf,
                   candidate.ra AS ra, candidate.dec AS decl
            FROM `{_table(broker)}`
            WHERE candidate.dec BETWEEN @dec - @deg AND @dec + @deg
              AND (2 * ASIN(SQRT(
                    POWER(SIN(RADIANS(candidate.dec - @dec) / 2), 2)
                    + COS(RADIANS(@dec)) * COS(RADIANS(candidate.dec))
                    * POWER(SIN(RADIANS(candidate.ra - @ra) / 2), 2)
                  ))) * 206264.806 <= @radius
            ORDER BY candidate.jd
            LIMIT @limit
        """
        params = [
            bigquery.ScalarQueryParameter("ra", "FLOAT64", float(ra)),
            bigquery.ScalarQueryParameter("dec", "FLOAT64", float(dec)),
            bigquery.ScalarQueryParameter("radius", "FLOAT64", float(radius)),
            bigquery.ScalarQueryParameter("deg", "FLOAT64", float(radius) / 3600.0),
            bigquery.ScalarQueryParameter(
                "limit", "INT64", int(kwargs.get("limit", 200))
            ),
        ]
        by_obj: dict = {}
        for r in _run(broker, sql, params):
            by_obj.setdefault(r["objectId"], []).append(r)
        return [_normalize_rows(oid, rs) for oid, rs in by_obj.items()]

    @staticmethod
    async def run_ingestion(broker, stop=None, max_messages=None, **kwargs):
        """Consume Pitt-Google's Pub/Sub stream (via ``pittgoogle-client``) and
        register each alert as a Candidate under ``filter_ids``, with cutouts
        (the streamed avro carries them, unlike the BigQuery archive). Requires
        ``altdata['subscription']`` — a Pub/Sub subscription in your project
        (with pubsub.subscriber) attached to Pitt-Google's topic."""
        import asyncio
        import json
        import os
        import tempfile

        import pittgoogle
        import sqlalchemy as sa

        from baselayer.app.models import async_plain_session_factory

        from ..models import User
        from ._save import save_object_as_candidate

        altdata = broker.altdata or {}
        key = altdata.get("service_account_key")
        project = altdata.get("project_id")
        subscription_name = altdata.get("subscription")
        filter_ids = altdata.get("filter_ids") or []
        survey = altdata.get("survey", "ZTF")
        if not (key and project and subscription_name):
            raise ValueError(
                "Ingestion needs service_account_key, project_id, and subscription."
            )

        # pittgoogle Auth reads GOOGLE_APPLICATION_CREDENTIALS (a keyfile path);
        # materialize the encrypted key to a temp file for the duration.
        if isinstance(key, dict):
            key = json.dumps(key)
        keyfile = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        keyfile.write(key)
        keyfile.close()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = keyfile.name
        os.environ["GOOGLE_CLOUD_PROJECT"] = project

        subscription = pittgoogle.pubsub.Subscription(
            subscription_name, projectid=project
        )
        log(f"Pitt-Google ingestion (broker {broker.id}): pulling {subscription_name}")

        count = 0
        try:
            while not (stop is not None and stop.is_set()):
                alerts = await asyncio.to_thread(
                    pittgoogle.pubsub.pull_batch, subscription, max_messages=100
                )
                alerts = alerts if isinstance(alerts, list) else []
                if not alerts:
                    continue
                for alert in alerts:
                    data, candid, cutouts = _normalize_pubsub_alert(alert)
                    if data is None:
                        continue
                    try:
                        async with async_plain_session_factory() as session:
                            user = await session.scalar(
                                sa.select(User).where(User.id == 1)
                            )
                            await save_object_as_candidate(
                                data,
                                survey,
                                session,
                                user,
                                filter_ids,
                                passing_alert_id=candid,
                                cutouts=cutouts,
                            )
                    except Exception as e:
                        log(f"Error ingesting Pitt-Google alert: {e}")
                    count += 1
                    if max_messages is not None and count >= max_messages:
                        break
                if max_messages is not None and count >= max_messages:
                    break
        finally:
            os.unlink(keyfile.name)
        log(f"Pitt-Google ingestion (broker {broker.id}): consumed {count} alerts")
        return count
