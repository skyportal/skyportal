import traceback

import requests

from baselayer.app.access import auth_or_token
from baselayer.log import make_log

from ...base import BaseHandler
from .utils import boom_available, boom_token, boom_url, convert_large_ints

log = make_log("api/boom/alert")

BOOM_RADIUS_UNIT_MAP = {
    "deg": "Degrees",
    "arcmin": "Arcminutes",
    "arcsec": "Arcseconds",
}

NO_CUTOUT_PROJECTION = {
    "cutoutScience": 0,
    "cutoutTemplate": 0,
    "cutoutDifference": 0,
}


class BoomAlertHandler(BaseHandler):
    @auth_or_token
    @boom_available
    async def get(self, survey: str):
        """
        ---
        summary: Retrieve alerts from Boom for a given survey
        description: |
          Retrieve alerts from Boom by objectId (single or comma-separated list),
          candid, or sky position (ra/dec/radius/radius_units). Positional queries
          and objectId filtering can be combined.
        tags:
          - alerts
          - boom
        parameters:
          - in: path
            name: survey
            required: true
            schema:
              type: string
            description: Survey name (e.g. ZTF, LSST)
          - in: query
            name: objectId
            required: false
            schema:
              type: string
            description: Single objectId or comma-separated list of objectIds
          - in: query
            name: candid
            required: false
            schema:
              type: integer
            description: Alert candid. Can be combined with objectId.
          - in: query
            name: ra
            required: false
            schema:
              type: number
            description: RA in degrees
          - in: query
            name: dec
            required: false
            schema:
              type: number
            description: Declination in degrees
          - in: query
            name: radius
            required: false
            schema:
              type: number
            description: Search radius (capped at 1 deg). Units set by radius_units.
          - in: query
            name: radius_units
            required: false
            schema:
              type: string
              enum: [deg, arcmin, arcsec]
            description: Units for radius
        responses:
          200:
            description: retrieved alert(s)
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
                            type: object
          400:
            content:
              application/json:
                schema: Error
        """
        object_id = self.get_query_argument("objectId", None)
        candid = self.get_query_argument("candid", None)
        ra = self.get_query_argument("ra", None)
        dec = self.get_query_argument("dec", None)
        radius = self.get_query_argument("radius", None)
        radius_units = self.get_query_argument("radius_units", None)

        position_tuple = (ra, dec, radius, radius_units)

        if not any((object_id, candid, ra, dec, radius, radius_units)):
            return self.error(
                "Missing required parameters: provide objectId, candid, or ra/dec/radius/radius_units."
            )

        headers = {"Authorization": f"Bearer {boom_token}"}
        catalog = f"{survey.upper()}_alerts"

        try:
            if candid is not None:
                try:
                    candid = int(candid)
                except ValueError:
                    return self.error("`candid` must be an integer.")

                filter_doc = {"candid": candid}
                if object_id:
                    filter_doc["objectId"] = object_id

                response = requests.post(
                    f"{boom_url}/queries/find",
                    headers=headers,
                    json={
                        "catalog_name": catalog,
                        "filter": filter_doc,
                        "projection": NO_CUTOUT_PROJECTION,
                        "max_time_ms": 10000,
                    },
                    timeout=15,
                )
                if response.status_code != 200:
                    return self.error(
                        f"Boom query failed: {response.status_code} {response.text}"
                    )
                data = response.json().get("data", [])
                return self.success(data=convert_large_ints(data))

            if not any(position_tuple):
                if object_id is None:
                    return self.error("Missing required parameters.")

                object_ids = [oid.strip() for oid in object_id.split(",")]
                filter_doc = (
                    {"objectId": object_ids[0]}
                    if len(object_ids) == 1
                    else {"objectId": {"$in": object_ids}}
                )

                response = requests.post(
                    f"{boom_url}/queries/find",
                    headers=headers,
                    json={
                        "catalog_name": catalog,
                        "filter": filter_doc,
                        "projection": NO_CUTOUT_PROJECTION,
                        "max_time_ms": 10000,
                    },
                    timeout=15,
                )
                if response.status_code != 200:
                    return self.error(
                        f"Boom query failed: {response.status_code} {response.text}"
                    )
                data = response.json().get("data", [])
                return self.success(data=convert_large_ints(data))

            if not all(position_tuple):
                missing = [
                    name
                    for name, val in zip(
                        ["ra", "dec", "radius", "radius_units"], position_tuple
                    )
                    if val is None
                ]
                return self.error(f"Missing positional parameters: {missing}.")

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

            if (
                (radius_units == "deg" and radius > 1)
                or (radius_units == "arcmin" and radius > 60)
                or (radius_units == "arcsec" and radius > 3600)
            ):
                return self.error("Radius must be <= 1.0 deg.")

            response = requests.post(
                f"{boom_url}/queries/cone_search",
                headers=headers,
                json={
                    "catalog_name": catalog,
                    "object_coordinates": {"query": [ra, dec]},
                    "radius": radius,
                    "unit": BOOM_RADIUS_UNIT_MAP[radius_units],
                    "max_time_ms": 10000,
                },
                timeout=15,
            )
            if response.status_code != 200:
                return self.error(
                    f"Boom cone search failed: {response.status_code} {response.text}"
                )

            alert_data = response.json().get("data", {}).get("query", [])

            if object_id is not None:
                filter_ids = {oid.strip() for oid in object_id.split(",")}
                alert_data = [a for a in alert_data if a.get("objectId") in filter_ids]

            return self.success(data=convert_large_ints(alert_data))

        except Exception:
            _err = traceback.format_exc()
            return self.error(f"failure: {_err}")
