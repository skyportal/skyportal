import traceback

import requests
import sqlalchemy as sa
from astropy.visualization import (
    AsinhStretch,
    AsymmetricPercentileInterval,
    LinearStretch,
    LogStretch,
    MinMaxInterval,
    SqrtStretch,
    ZScaleInterval,
)

from baselayer.app.access import auth_or_token, permissions
from baselayer.log import make_log

from ....models import Obj, Thumbnail
from ...base import BaseHandler
from .utils import (
    add_thumbnails,
    boom_available,
    boom_token,
    boom_url,
    decode_cutout,
    orient_cutout,
    render_cutout_png,
    thumbnail_types,
)

log = make_log("api/boom/cutout")

NORMALIZATION_METHODS = {
    "asymmetric_percentile": lambda: AsymmetricPercentileInterval(
        lower_percentile=1, upper_percentile=100
    ),
    "min_max": MinMaxInterval,
    "zscale": lambda: ZScaleInterval(n_samples=600, contrast=0.045, krej=2.5),
}

STRETCHING_METHODS = {
    "linear": LinearStretch,
    "log": LogStretch,
    "asinh": AsinhStretch,
    "sqrt": SqrtStretch,
}

KNOWN_CMAPS = {"bone", "gray", "cividis", "viridis", "magma"}


class BoomCutoutHandler(BaseHandler):
    @auth_or_token
    @boom_available
    async def get(self, survey: str):
        """
        ---
        summary: Serve Boom alert cutout(s) as JSON (FITS) or PNG
        description: |
          When file_format=png (default): renders a single cutout type as a PNG image.
          The `cutout` parameter is required in this mode.

          When file_format=fits: fetches all three cutouts from Boom
          and returns the raw payload as JSON (keys: cutoutScience,
          cutoutTemplate, cutoutDifference). No server-side processing is
          applied; the caller receives exactly what Boom returned.

        tags:
          - alerts
          - boom

        parameters:
          - in: path
            name: survey
            description: "Survey name (e.g. ZTF, LSST)"
            required: true
            schema:
              type: string
          - in: query
            name: candid
            description: "Alert candid. Mutually exclusive with objectId."
            required: false
            schema:
              type: integer
          - in: query
            name: objectId
            description: "Object ID. Mutually exclusive with candid."
            required: false
            schema:
              type: string
          - in: query
            name: which
            description: "Which alert to use when querying by objectId."
            required: false
            schema:
              type: string
              enum: [first, last, brightest, faintest]
          - in: query
            name: file_format
            description: |
              fits (default): return raw Boom JSON with all three cutouts.
              png: render a single cutout as a PNG image (requires `cutout`).
            required: false
            default: png
            schema:
              type: string
              enum: [fits, png]
          - in: query
            name: cutout
            description: "PNG mode only: which cutout to render."
            required: false
            schema:
              type: string
              enum: [science, template, difference]
          - in: query
            name: interval
            description: "PNG mode only: normalisation interval."
            required: false
            schema:
              type: string
              enum: [min_max, zscale]
          - in: query
            name: stretch
            description: "PNG mode only: stretch function."
            required: false
            schema:
              type: string
              enum: [linear, log, asinh, sqrt]
          - in: query
            name: cmap
            description: "PNG mode only: colour map."
            required: false
            schema:
              type: string
              enum: [bone, gray, cividis, viridis, magma]

        responses:
          '200':
            description: retrieved cutout(s)
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          type: object
              image/png:
                schema:
                  type: string
                  format: binary
          '400':
            description: retrieval failed
            content:
              application/json:
                schema: Error
        """
        try:
            candid = self.get_query_argument("candid", None)
            object_id = self.get_query_argument("objectId", None)
            which = self.get_query_argument("which", "last")
            file_format = self.get_argument("file_format", "png").lower()
            cutout = self.get_argument("cutout", None)
            interval = self.get_argument("interval", default=None)
            stretch = self.get_argument("stretch", default=None)
            cmap = self.get_argument("cmap", default=None)

            if candid is None and object_id is None:
                return self.error("Either `candid` or `objectId` must be provided.")
            if candid is not None and object_id is not None:
                return self.error(
                    "Only one of `candid` or `objectId` should be provided."
                )
            if candid is not None:
                try:
                    candid = int(candid)
                except ValueError:
                    return self.error("`candid` must be an integer.")

            if file_format not in ("fits", "png"):
                return self.error("`file_format` must be one of ['fits', 'png'].")

            known_which = ["first", "last", "brightest", "faintest"]
            if which not in known_which:
                return self.error(f"`which` must be one of {known_which}.")

            params = (
                {"candid": candid}
                if candid is not None
                else {"objectId": object_id, "which": which}
            )

            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {boom_token}",
            }

            response = requests.get(
                f"{boom_url}/surveys/{survey.upper()}/cutouts",
                headers=headers,
                params=params,
                timeout=10,
            )
            if response.status_code != 200:
                return self.error(
                    f"Failed to fetch cutout from Boom: {response.status_code} {response.text}"
                )

            resp_json = response.json()
            if "data" not in resp_json:
                return self.error(
                    "Unexpected response from Boom API (missing 'data' field)."
                )

            boom_data = resp_json["data"]

            if file_format == "fits":
                return self.success(data=boom_data)

            # ── PNG mode ─────────────────────────────────────────────────────
            if cutout is None:
                return self.error("`cutout` is required when file_format=png.")
            cutout = cutout.capitalize()
            if cutout not in ("Science", "Template", "Difference"):
                return self.error(
                    "`cutout` must be one of ['science', 'template', 'difference']."
                )

            cutout_key = f"cutout{cutout}"
            if cutout_key not in boom_data:
                return self.error(f"Cutout type '{cutout}' not found in Boom response.")

            data_array, header = decode_cutout(boom_data[cutout_key], survey)
            data_array = orient_cutout(data_array, survey, header)

            normalizer = NORMALIZATION_METHODS.get(
                (interval or "asymmetric_percentile").lower(),
                NORMALIZATION_METHODS["asymmetric_percentile"],
            )()

            default_stretch = "linear" if cutout == "Difference" else "log"
            stretcher = STRETCHING_METHODS.get(
                (stretch or default_stretch).lower(), LogStretch
            )()

            cmap = cmap.lower() if cmap and cmap.lower() in KNOWN_CMAPS else "bone"

            buff = render_cutout_png(data_array, stretcher, normalizer, cmap)
            self.set_header("Content-Type", "image/png")
            self.write(buff.getvalue())

        except Exception:
            _err = traceback.format_exc()
            return self.error(f"failure: {_err}")

    @permissions(["Upload data"])
    @boom_available
    async def post(self, survey: str):
        """
        ---
        summary: Save or replace cutout thumbnails for an existing source
        description: |
          Fetches cutout images from Boom for a given alert (identified by
          candid or objectId + which) and stores them as thumbnails for the
          corresponding source in SkyPortal. All existing thumbnails of types
          new/ref/sub for that source are replaced. Returns an error if the
          object does not already exist as a source.
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
        requestBody:
          content:
            application/json:
              schema:
                type: object
                required:
                  - objectId
                properties:
                  objectId:
                    type: string
                    description: Object ID of the existing source
                  candid:
                    type: integer
                    description: >
                      Alert candid to use for the cutout. Mutually exclusive
                      with `which`.
                  which:
                    type: string
                    enum: [first, last, brightest, faintest]
                    default: last
                    description: >
                      When querying by objectId, which alert to use.
                      Ignored when `candid` is provided.
                  band:
                    type: string
                    description: Optional band filter (e.g. g, r, i for LSST)
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
          400:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()
        object_id = data.get("objectId")
        candid = data.get("candid")
        which = data.get("which", "last")
        band = data.get("band")

        if not object_id:
            return self.error("`objectId` is required.")
        try:
            object_id = str(object_id)
        except ValueError:
            return self.error("`objectId` must be a string.")

        known_which = ["first", "last", "brightest", "faintest"]
        if which not in known_which:
            return self.error(f"`which` must be one of {known_which}.")

        if candid is not None:
            try:
                candid = int(candid)
            except (TypeError, ValueError):
                return self.error("`candid` must be an integer.")

        params = (
            {"candid": candid}
            if candid is not None
            else {"objectId": object_id, "which": which}
        )
        if band is not None:
            params["band"] = band

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {boom_token}",
        }

        async with self.AsyncSession() as session:
            obj = await session.scalar(sa.select(Obj).where(Obj.id == object_id))
            if obj is None:
                return self.error(
                    f"Object '{object_id}' not found. Save it as a source first."
                )

            response = requests.get(
                f"{boom_url}/surveys/{survey.upper()}/cutouts",
                headers=headers,
                params=params,
                timeout=10,
            )
            if response.status_code != 200:
                return self.error(
                    f"Failed to fetch cutouts from Boom: "
                    f"{response.status_code} {response.text}"
                )

            cutout_data = response.json().get("data", {})
            cutout_data["objectId"] = object_id

            existing = (
                await session.scalars(
                    sa.select(Thumbnail).where(
                        Thumbnail.obj_id == object_id,
                        Thumbnail.type.in_([t[1] for t in thumbnail_types]),
                    )
                )
            ).all()
            for thumb in existing:
                await session.delete(thumb)
            await session.flush()

            await add_thumbnails(cutout_data, survey.upper(), session)
            await session.commit()

        return self.success(data={"objectId": object_id, "survey": survey})
