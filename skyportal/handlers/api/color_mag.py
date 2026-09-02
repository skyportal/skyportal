from typing import Annotated

import numpy as np
from pydantic import Field
from skyportal_py_models.sources import ObjColorMagGetQuery

from baselayer.app.access import auth_or_token

from ...models import (
    Annotation,
    Obj,
)
from ..base import BaseHandler


def normalize_key(str):
    # convert the string to lowercase and remove underscores
    return str.lower().replace("_", "")


def get_color_mag(annotations, **kwargs):
    # please refer to `ObjColorMagHandler.get` below

    # ignore None inputs from e.g., query arguments
    inputs = {k: v for k, v in kwargs.items() if v is not None}

    catalog = inputs.get("catalog", "gaia")
    mag_key = inputs.get("apparentMagKey", "Mag_G")
    parallax_key = inputs.get("parallaxKey", "Plx")
    absorption_key = inputs.get("absorptionKey", "A_G")
    abs_mag_key = inputs.get("absoluteMagKey", None)
    blue_mag_key = inputs.get("blueMagKey", "Mag_Bp")
    red_mag_key = inputs.get("redMagKey", "Mag_Rp")
    color_key = inputs.get("colorKey", None)

    output = []

    for an in annotations:
        abs_mag = None
        color = None
        absorption = None
        if normalize_key(catalog) in normalize_key(an.origin):
            # found the right catalog, but does it have the right keys?

            # get the absolute magnitude
            if abs_mag_key is not None:  # get the absolute magnitude directly
                for k in an.data:
                    if normalize_key(abs_mag_key) == normalize_key(k):
                        abs_mag = an.data[k]  # found it!
            else:  # we need to look for the apparent magnitude and parallax
                mag = None
                plx = None
                for k in an.data:
                    if normalize_key(mag_key) == normalize_key(k):
                        mag = an.data[k]
                    if normalize_key(parallax_key) == normalize_key(k):
                        plx = an.data[k]
                    if mag is not None and plx is not None:
                        if plx > 0:
                            abs_mag = mag + 5 * np.log10(plx / 100)
                        else:
                            abs_mag = np.nan

            # get the color data
            if color_key is not None:  # get the color value directly
                for k in an.data:
                    if normalize_key(color_key) == normalize_key(k):
                        color = float(an.data[k])  # found it!
            else:
                blue = None
                red = None
                for k in an.data:
                    if normalize_key(blue_mag_key) == normalize_key(k):
                        blue = an.data[k]
                    if normalize_key(red_mag_key) == normalize_key(k):
                        red = an.data[k]
                    if blue is not None and red is not None:
                        # calculate the color between these two magnitudes
                        color = float(blue) - float(red)

            # only check this if given an absorption term
            if absorption_key is not None:
                for k in an.data:
                    if normalize_key(absorption_key) == normalize_key(k):
                        absorption = an.data[k]

        if abs_mag is not None and color is not None:
            if absorption is not None and not np.isnan(absorption):
                abs_mag = abs_mag + absorption  # apply the absorption term

            output.append({"origin": an.origin, "abs_mag": abs_mag, "color": color})

    return output


class ObjColorMagHandler(BaseHandler):
    @auth_or_token
    async def get(
        self,
        obj_id: Annotated[
            str, Field(description="ID of the object to retrieve photometry for")
        ],
        *,
        query: ObjColorMagGetQuery = None,
    ):
        """
        ---
        summary: Get color and absolute magnitude of a source
        description: |
            get the color and absolute magnitude of a source
            based on cross-matches to some catalog (default is GAIA).
        tags:
          - objs
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: array
                      items:
                        type: object
                        properties:
                          origin:
                            type: string
                          color:
                            type: number
                          abs_mag:
                            type: number
          400:
            content:
              application/json:
                schema: Error
        """
        query = self.parse_query(ObjColorMagGetQuery)

        async with self.AsyncSession() as session:
            obj = await session.scalar(
                Obj.select(self.associated_user_object).where(Obj.id == obj_id)
            )
            if obj is None:
                return self.error("Invalid object id.")

            ann_result = await session.scalars(
                Annotation.select(self.associated_user_object).where(
                    Annotation.obj_id == obj_id
                )
            )
            annotations = ann_result.unique().all()

            output = get_color_mag(
                annotations,
                catalog=query.catalog,
                apparentMagKey=query.apparentMagKey,
                parallaxKey=query.parallaxKey,
                absorptionKey=query.absorptionKey,
                absoluteMagKey=query.absoluteMagKey,
                blueMagKey=query.blueMagKey,
                redMagKey=query.redMagKey,
                colorKey=query.colorKey,
            )

            return self.success(data=output)
