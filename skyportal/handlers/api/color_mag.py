import numpy as np
from baselayer.app.access import auth_or_token
from ..base import BaseHandler

from ...models import (
    Obj,
    Annotation,
)


def convertKey(str):
    # convert the string to lowercase and remove underscores
    return str.lower().replace('_', '')


class ObjColorMagHandler(BaseHandler):
    """
    ---
    description: |
        get the color and absolute magnitude of a source
        based on cross-matches to some catalog (default is GAIA).
    parameters:
    - in: path
        name: obj_id
        required: true
        schema:
          type: string
        description: ID of the object to retrieve photometry for
      - in: query
        name: catalog
        required: false
        schema:
          type: string
        description: |
          The name of the data key, associated with a catalog cross match,
          from which the color-mag data should be retrieved.
          Default is GAIA. Ignores case and underscores.
      - in: query
        name: apparentMagKey
        required: false
        schema:
          type: string
        description: |
          The key inside the cross-match which is associated
          with the magnitude of the color-magnitude data.
          Will look for parallax data in addition to this magnitude
          in order to calculate the absolute magnitude of the object.
          Default is "Mag_G". Ignores case and underscores.
      - in: query
        name: parallaxKey
        required: false
        schema:
          type: string
        description: |
          The key inside the cross-match which is associated
          with the parallax of the source.
          Will look for magnitude data in addition to this parallax
          in order to calculate the absolute magnitude of the object.
          Default is "Plx". Ignores case and underscores.
      - in: query
        name: absorptionKey
        required: false
        schema:
          type: string
        description: |
          The key inside the cross-match which is associated
          with the source absorption term.
          Will add this term to the absolute magnitude calculated
          from apparent magnitude and parallax.
          Default is "A_G". Ignores case and underscores.
      - in: query
        name: absoluteMagKey
        required: false
        schema:
          type: string
        description: |
          The key inside the cross-match which is associated
          with the absolute magnitude of the color-magnitude data.
          If given, will override the "apparentMagKey", "parallaxKey"
          and "absorptionKey", and takes the magnitude directly from
          this key in the cross match dictionary.
          Default is None. Ignores case and underscores.
      - in: query
        name: blueMagKey
        required: false
        schema:
          type: string
        description: |
          The key inside the cross-match which is associated
          with the source magnitude in the shorter wavelength.
          Will add this term to the red magnitude to get the color.
          Default is "Mag_Bp". Ignores case and underscores.
      - in: query
        name: redMagKey
        required: false
        schema:
          type: string
        description: |
          The key inside the cross-match which is associated
          with the source magnitude in the longer wavelength.
          Will add this term to the blue magnitude to get the color.
          Default is "Mag_Rp". Ignores case and underscores.
      - in: query
        name: colorKey
        required: false
        schema:
          type: string
        description: |
          The key inside the cross-match which is associated
          with the color term of the color-magnitude data.
          If given, will override the "blueMagKey", and "redMagKey",
          taking the color directly from the associated dictionary value.
          Default is None. Ignores case and underscores.

    responses:
      200:
        content:
          application/json:
            schema: ArrayOfObjects

      400:
        content:
        application/json:
          schema: Error

    """

    @auth_or_token
    def get(self, obj_id):
        obj = Obj.query.get(obj_id)
        if obj is None:
            return self.error('Invalid object id.')

        annotations = (
            Annotation.query_records_accessible_by(self.current_user)
            .filter(Annotation.obj_id == obj_id)
            .all()
        )
        self.verify_permissions()

        catalog = self.get_query_argument('catalog', 'gaia')
        mag_key = self.get_query_argument('apparentMagKey', 'Mag_G')
        parallax_key = self.get_query_argument('parallaxKey', 'Plx')
        absorption_key = self.get_query_argument('absorptionKey', 'A_G')
        abs_mag_key = self.get_query_argument('absoluteMagKey', None)
        blue_mag_key = self.get_query_argument('blueMagKey', 'Mag_Bp')
        red_mag_key = self.get_query_argument('redMagKey', 'Mag_Rp')
        color_key = self.get_query_argument('color', None)

        output = []

        for an in annotations:
            print(an)
            abs_mag = None
            color = None
            absorption = None
            origin = an.origin

            for (
                key,
                xmatch,
            ) in (
                an.data.items()
            ):  # go over all items in the data (e.g., different catalog matches)
                if convertKey(key) == convertKey(
                    catalog
                ):  # found the right catalog, but does it have the right keys?

                    # get the absolute magnitude
                    if abs_mag_key is not None:  # get the absolute magnitude directly
                        for k in xmatch.keys():
                            if convertKey(abs_mag_key) == convertKey(k):
                                abs_mag = xmatch[k]  # found it!
                                break  # no need to scan the rest of the cross match
                    else:  # we need to look for the apparent magnitude and parallax
                        mag = None
                        plx = None
                        for k in xmatch.keys():
                            if convertKey(mag_key) == convertKey(k):
                                mag = xmatch[k]
                            if convertKey(parallax_key) == convertKey(k):
                                plx = xmatch[k]
                            if mag is not None and plx is not None:
                                abs_mag = mag - 2.5 * np.log10(plx / 100)
                                break  # no need to scan the rest of the cross match

                    # get the color data
                    if color_key is not None:  # get the color value directly
                        for k in xmatch.keys():
                            if convertKey(color_key) == convertKey(k.lower):
                                color = float(xmatch[k])  # found it!
                                break  # no need to scan the rest of the cross match
                    else:
                        blue = None
                        red = None
                        for k in xmatch.keys():
                            if convertKey(blue_mag_key) == convertKey(k):
                                blue = xmatch[k]
                            if convertKey(red_mag_key) == convertKey(k):
                                red = xmatch[k]
                            if blue is not None and red is not None:
                                color = float(blue) - float(
                                    red
                                )  # calculate the color between these two magnitudes
                                break  # no need to scan the rest of the cross match

                    if (
                        absorption_key is not None
                    ):  # only check this if given an absorption term
                        for k in xmatch.keys():
                            if convertKey(absorption_key) == convertKey(k):
                                absorption = xmatch[k]
                                break  # no need to scan the rest of the cross match

                if (
                    abs_mag is not None
                    and not np.isnan(abs_mag)
                    and color is not None
                    and not np.isnan(color)
                ):

                    if absorption is not None and not np.isnan(absorption):
                        abs_mag = abs_mag + absorption  # apply the absorption term

                    output.append(
                        {'origin': origin, 'abs_mag': abs_mag, 'color': color}
                    )
                    break  # found all the data we need for this annotation/origin

        self.verify_permissions()

        return self.success(data=output)
