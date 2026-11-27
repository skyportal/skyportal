from types import SimpleNamespace

import requests
from tornado.ioloop import IOLoop

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env

from ...broker_apis.boom import _request
from ...models import Broker, Obj
from ...utils.archival_rv import fetch_spectrum
from ..base import BaseHandler

_, cfg = load_env()
COLLECTION = "Archival_RV_Pilot_v1"


def find_pilot_source(broker, source_id, ra, dec):
    result = _request(
        broker,
        "POST",
        "queries/cone_search",
        json={
            "catalog_name": COLLECTION,
            "object_coordinates": {"source": [ra, dec]},
            "radius": 3.0,
            "unit": "Arcseconds",
            "limit": 10,
            "max_time_ms": 5000,
        },
    )
    candidates = (result or {}).get("source", [])
    named = [
        candidate
        for candidate in candidates
        if source_id == candidate["_id"] or source_id in candidate.get("aliases", [])
    ]
    if len(named) == 1:
        return named[0]
    return candidates[0] if len(candidates) == 1 else None


class ArchivalRvHandler(BaseHandler):
    @auth_or_token
    async def get(self, source_id):
        broker_id = cfg["boom.archival_rv_broker_id"]
        if broker_id is None:
            return self.error("Archival RV pilot is disabled", status=404)
        with self.Session() as session:
            source = session.scalars(
                Obj.select(self.current_user).where(Obj.id == source_id)
            ).first()
            broker = session.scalars(
                Broker.select(self.current_user).where(
                    Broker.id == broker_id, Broker.active.is_(True)
                )
            ).first()
            if (
                source is None
                or broker is None
                or broker.broker_classname != "BOOMBROKER"
            ):
                return self.error(
                    "Source or archival RV broker unavailable", status=404
                )
            ra, dec = source.ra, source.dec
            remote = SimpleNamespace(altdata=broker.altdata)
        loop = IOLoop.current()
        try:
            match = await loop.run_in_executor(
                None, find_pilot_source, remote, source_id, ra, dec
            )
        except (ValueError, requests.RequestException):
            return self.error("The BOOM archival RV catalog is unavailable", status=502)

        observation_id = self.get_query_argument("observation", None)
        if observation_id is None:
            if match is not None:
                match["observations"] = [
                    {
                        key: value
                        for key, value in observation.items()
                        if key != "spectrum"
                    }
                    | {"spectrum_available": bool(observation.get("spectrum"))}
                    for observation in match["observations"]
                ]
            return self.success(data={"source": match})

        observation = next(
            (
                row
                for row in (match or {}).get("observations", [])
                if row["id"] == observation_id
            ),
            None,
        )
        if not observation or not observation.get("spectrum"):
            return self.error(
                "No spectrum is available for this observation", status=404
            )
        try:
            spectrum = await loop.run_in_executor(
                None, fetch_spectrum, observation["spectrum"]
            )
        except ValueError as error:
            return self.error(str(error), status=502)
        return self.success(data=spectrum)
