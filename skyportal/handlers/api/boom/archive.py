import asyncio
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import requests

from baselayer.app.access import auth_or_token
from baselayer.log import make_log

from ...base import BaseHandler
from .alert import BOOM_RADIUS_UNIT_MAP
from .utils import boom_available, boom_token, boom_url

log = make_log("api/boom_archive")

# Collections that belong to surveys/alerts, not reference catalogs.
SURVEY_PREFIXES = ("ZTF_", "LSST_", "PTF_", "PGIR_", "WNTR_")

CATALOGS_TTL = timedelta(hours=1)

_reference_catalogs = None
_catalogs_fetched_at = None


def _fetch_reference_catalogs():
    """Hit Boom's /catalogs endpoint, strip alert collections, and cache."""
    global _reference_catalogs, _catalogs_fetched_at
    if boom_url is None or boom_token is None:
        return _reference_catalogs
    try:
        response = requests.get(
            f"{boom_url}/catalogs",
            headers={"Authorization": f"Bearer {boom_token}"},
            timeout=10,
        )
        if response.status_code != 200:
            log(
                f"Failed to fetch catalog list from Boom: "
                f"{response.status_code} {response.text}"
            )
            return _reference_catalogs  # return stale list if available
        all_catalogs = response.json().get("data", [])
        _reference_catalogs = [
            str(c["name"])
            for c in all_catalogs
            if not any(str(c["name"]).startswith(p) for p in SURVEY_PREFIXES)
        ]
        _catalogs_fetched_at = datetime.utcnow()
        log(f"Cached {len(_reference_catalogs)} Boom reference catalogs.")
        return _reference_catalogs
    except Exception as e:
        log(f"Failed to fetch catalog list from Boom: {e}")
        return _reference_catalogs


def get_reference_catalogs():
    """Return cached reference catalog list, refreshing if TTL has expired."""
    if (
        _reference_catalogs is None
        or _catalogs_fetched_at is None
        or datetime.utcnow() - _catalogs_fetched_at > CATALOGS_TTL
    ):
        return _fetch_reference_catalogs()
    return _reference_catalogs


# Warm the cache at module load time (best-effort; may be None if Boom is down).
_fetch_reference_catalogs()


def _cone_search_catalog(catalog, ra, dec, radius, unit, token, url):
    """Run a single cone-search against one Boom catalog. Returns (catalog, results)."""
    try:
        response = requests.post(
            f"{url}/queries/cone_search",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "catalog_name": catalog,
                "object_coordinates": {"query": [ra, dec]},
                "radius": radius,
                "unit": unit,
                "max_time_ms": 5000,
            },
            timeout=10,
        )
        if response.status_code != 200:
            return catalog, []
        results = response.json().get("data", {}).get("query", [])
        for source in results:
            source["_id"] = str(source.get("_id", ""))
            coords = (
                source.get("coordinates", {})
                .get("radec_geojson", {})
                .get("coordinates", [])
            )
            if len(coords) == 2:
                source["ra"] = coords[0] + 180
                source["dec"] = coords[1]
        return catalog, results
    except Exception as e:
        log(f"Cone search against {catalog} failed: {e}")
        return catalog, []


class BoomCatalogNamesHandler(BaseHandler):
    @auth_or_token
    @boom_available
    async def get(self):
        """
        ---
        summary: List non-survey catalog names available in Boom
        description: |
          Returns the cached list of reference catalog names from Boom
          (i.e. all catalogs whose names do not start with a known survey
          prefix such as ZTF_, LSST_, PTF_, PGIR_, or WNTR_).
          The list is refreshed automatically every hour.
        tags:
          - archive
          - boom
        responses:
          200:
            description: list of catalog names
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          type: array
                          items:
                            type: string
          400:
            content:
              application/json:
                schema: Error
        """
        catalogs = get_reference_catalogs()
        if catalogs is None:
            return self.error("Could not retrieve catalog list from Boom.")
        return self.success(data=catalogs)


class BoomCrossMatchHandler(BaseHandler):
    @auth_or_token
    @boom_available
    async def get(self):
        """
        ---
        summary: Cross-match a position against all reference catalogs in Boom
        description: |
          Retrieves the cached list of non-survey catalogs from Boom (refreshed
          every hour), then runs a positional cone-search against every reference
          catalog in parallel.
        tags:
          - archive
          - boom
        parameters:
          - in: query
            name: ra
            required: true
            schema:
              type: number
            description: RA in degrees (0 ≤ RA < 360)
          - in: query
            name: dec
            required: true
            schema:
              type: number
            description: Declination in degrees (-90 ≤ Dec ≤ 90)
          - in: query
            name: radius
            required: true
            schema:
              type: number
            description: Search radius, capped at 1 deg. Units set by radius_units.
          - in: query
            name: radius_units
            required: true
            schema:
              type: string
              enum: [deg, arcmin, arcsec]
        responses:
          200:
            description: cross-matched sources keyed by catalog name
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          type: object
          400:
            content:
              application/json:
                schema: Error
        """
        ra = self.get_query_argument("ra", None)
        dec = self.get_query_argument("dec", None)
        radius = self.get_query_argument("radius", None)
        radius_units = self.get_query_argument("radius_units", None)

        if not all((ra, dec, radius, radius_units)):
            missing = [
                name
                for name, val in zip(
                    ["ra", "dec", "radius", "radius_units"],
                    [ra, dec, radius, radius_units],
                )
                if val is None
            ]
            return self.error(f"Missing required parameters: {missing}.")

        if radius_units not in BOOM_RADIUS_UNIT_MAP:
            return self.error(
                "Invalid radius_units. Must be one of 'deg', 'arcmin', or 'arcsec'."
            )

        try:
            ra = float(ra)
            dec = float(dec)
            radius = float(radius)
        except ValueError:
            return self.error("Invalid (non-float) value provided.")

        if not (0 <= ra < 360):
            return self.error("Invalid RA value: must be 0 <= RA [deg] < 360.")
        if not (-90 <= dec <= 90):
            return self.error("Invalid Dec value: must be -90 <= Dec [deg] <= 90.")
        if (
            (radius_units == "deg" and radius > 1)
            or (radius_units == "arcmin" and radius > 60)
            or (radius_units == "arcsec" and radius > 3600)
        ):
            return self.error("Radius must be <= 1.0 deg.")

        try:
            catalogs = get_reference_catalogs()
            if not catalogs:
                return self.error(
                    "No reference catalogs available in Boom to cross-match against."
                )

            unit = BOOM_RADIUS_UNIT_MAP[radius_units]
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as pool:
                futures = [
                    loop.run_in_executor(
                        pool,
                        _cone_search_catalog,
                        catalog,
                        ra,
                        dec,
                        radius,
                        unit,
                        boom_token,
                        boom_url,
                    )
                    for catalog in catalogs
                ]
                pairs = await asyncio.gather(*futures)

            data = {catalog: results for catalog, results in pairs if results}
            return self.success(data=data)

        except Exception:
            _err = traceback.format_exc()
            return self.error(f"failure: {_err}")
