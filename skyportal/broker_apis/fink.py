from baselayer.log import make_log

from .interface import BrokerAPI

log = make_log("broker/fink")

# Fink ZTF alerts use fid (1/2/3); LSST alerts carry a string band already.
_FID_TO_BAND = {1: "g", 2: "r", 3: "i"}


class FINKBROKER(BrokerAPI):
    """The Fink alert broker (ingestion-only via the ``fink-client`` Kafka streams).

    Fink exposes no interactive REST query API here — it is a streaming ingestion
    source. Configure a ``Broker`` with ``altdata`` holding a ``fink`` block
    (servers/username/password/group_id/topics), ``filter_ids`` (the skyportal
    Filters these science-topic alerts pass), and ``survey`` ("ZTF"/"LSST").
    Fink 'topics' are science tags (e.g. ``fink_kn_candidates_ztf``).
    """

    surveys = ["ZTF", "LSST"]

    form_json_schema_config = {
        "type": "object",
        "required": ["fink"],
        "properties": {
            "fink": {
                "type": "object",
                "title": "Fink Kafka",
                "properties": {
                    "servers": {"type": "string", "title": "Bootstrap servers"},
                    "username": {"type": "string"},
                    "password": {"type": "string"},
                    "group_id": {"type": "string"},
                    "topics": {"type": "array", "items": {"type": "string"}},
                },
            },
            "survey": {
                "type": "string",
                "title": "Survey",
                "enum": ["ZTF", "LSST"],
                "default": "ZTF",
            },
        },
    }

    ui_json_schema = {"fink": {"password": {"ui:widget": "password"}}}

    @staticmethod
    def validate_config(altdata):
        if not (altdata or {}).get("fink", {}).get("servers"):
            raise ValueError("Broker altdata must include fink.servers.")

    @staticmethod
    def _normalize(survey, alert):
        """Reshape a Fink alert (survey-specific) into the standard alert shape
        (``objectId`` + ``candidate`` + a single-detection ``prv_candidates``).
        Returns ``(data, passing_alert_id)`` or ``(None, None)``."""
        if survey == "LSST":
            src = alert.get("diaSource") or {}
            obj = alert.get("diaObject") or {}
            oid = obj.get("diaObjectId")
            if oid is None:
                return None, None
            mjd = src.get("midpointMjdTai")
            prv = [
                {
                    "jd": (mjd + 2400000.5) if mjd is not None else None,
                    "band": src.get("band"),
                    "psfFlux": src.get("psfFlux"),  # nJy; shared save scales to Jy
                    "psfFluxErr": src.get("psfFluxErr"),
                    "ra": src.get("ra"),
                    "dec": src.get("dec"),
                }
            ]
            data = {
                "objectId": str(oid),
                "candidate": {
                    "ra": obj.get("ra") or src.get("ra"),
                    "dec": obj.get("dec") or src.get("dec"),
                },
                "prv_candidates": prv,
            }
            return data, src.get("diaSourceId")

        cand = alert.get("candidate") or {}
        oid = alert.get("objectId")
        if oid is None:
            return None, None
        prv = [
            {
                "jd": cand.get("jd"),
                "band": _FID_TO_BAND.get(cand.get("fid")),
                "magpsf": cand.get("magpsf"),
                "sigmapsf": cand.get("sigmapsf"),
                "ra": cand.get("ra"),
                "dec": cand.get("dec"),
            }
        ]
        data = {
            "objectId": oid,
            "candidate": {
                "ra": cand.get("ra"),
                "dec": cand.get("dec"),
                "magpsf": cand.get("magpsf"),
            },
            "prv_candidates": prv,
        }
        return data, cand.get("candid")

    @staticmethod
    async def run_ingestion(broker, stop=None, max_messages=None, **kwargs):
        """Consume Fink's science-topic Kafka streams via ``fink-client`` and
        register each alert as a Candidate under ``filter_ids``."""
        import asyncio

        import sqlalchemy as sa
        from fink_client.consumer import AlertConsumer

        from baselayer.app.models import async_plain_session_factory

        from ..models import User
        from ._save import save_object_as_candidate

        altdata = broker.altdata or {}
        fink = altdata.get("fink") or {}
        survey = altdata.get("survey", "ZTF")
        filter_ids = altdata.get("filter_ids") or []
        maxtimeout = float(fink.get("maxtimeout", 5))

        config = {
            "bootstrap.servers": fink.get("servers"),
            "group.id": fink.get("group_id", f"skyportal-broker-{broker.id}"),
        }
        if fink.get("username"):
            config["username"] = fink["username"]
        if fink.get("password"):
            config["password"] = fink["password"]
        topics = fink.get("topics") or []

        consumer = AlertConsumer(topics, config)
        log(f"Fink ingestion (broker {broker.id}): subscribed to {topics}")

        count = 0
        try:
            while not (stop is not None and stop.is_set()):
                topic, alert, key = await asyncio.to_thread(consumer.poll, maxtimeout)
                if alert is None:
                    continue
                data, candid = FINKBROKER._normalize(survey, alert)
                if data is None:
                    continue
                try:
                    async with async_plain_session_factory() as session:
                        user = await session.scalar(sa.select(User).where(User.id == 1))
                        await save_object_as_candidate(
                            data,
                            survey,
                            session,
                            user,
                            filter_ids,
                            passing_alert_id=candid,
                        )
                except Exception as e:
                    log(f"Error ingesting Fink alert {data.get('objectId')}: {e}")
                count += 1
                if max_messages is not None and count >= max_messages:
                    break
        finally:
            consumer.close()
        log(f"Fink ingestion (broker {broker.id}): consumed {count} alerts")
        return count
