import numpy as np
from baselayer.app.access import auth_or_token
from ..base import BaseHandler

from ...models import (
    Obj,
    Annotation,
)


def normalize_key(str):
    # convert the string to lowercase and remove underscores
    return str.lower().replace('_', '')


def get_color_mag(annotations, **kwargs):
    # please refer to `ObjColorMagHandler.get` below

    # ignore None inputs from e.g., query arguments
    inputs = {k: v for k, v in kwargs.items() if v is not None}

    catalog = inputs.get('catalog', 'gaia')
    mag_key = inputs.get('apparentMagKey', 'Mag_G')
    parallax_key = inputs.get('parallaxKey', 'Plx')
    absorption_key = inputs.get('absorptionKey', 'A_G')
    abs_mag_key = inputs.get('absoluteMagKey', None)
    blue_mag_key = inputs.get('blueMagKey', 'Mag_Bp')
    red_mag_key = inputs.get('redMagKey', 'Mag_Rp')
    color_key = inputs.get('colorKey', None)

    output = []

    for an in annotations:
        abs_mag = None
        color = None
        absorption = None
        if normalize_key(catalog) in normalize_key(an.origin):
            # found the right catalog, but does it have the right keys?

            # get the absolute magnitude
            if abs_mag_key is not None:  # get the absolute magnitude directly
                for k in an.data.keys():
                    if normalize_key(abs_mag_key) == normalize_key(k):
                        abs_mag = an.data[k]  # found it!
            else:  # we need to look for the apparent magnitude and parallax
                mag = None
                plx = None
                for k in an.data.keys():
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
                for k in an.data.keys():
                    if normalize_key(color_key) == normalize_key(k):
                        color = float(an.data[k])  # found it!
            else:
                blue = None
                red = None
                for k in an.data.keys():
                    if normalize_key(blue_mag_key) == normalize_key(k):
                        blue = an.data[k]
                    if normalize_key(red_mag_key) == normalize_key(k):
                        red = an.data[k]
                    if blue is not None and red is not None:
                        # calculate the color between these two magnitudes
                        color = float(blue) - float(red)

            # only check this if given an absorption term
            if absorption_key is not None:
                for k in an.data.keys():
                    if normalize_key(absorption_key) == normalize_key(k):
                        absorption = an.data[k]

        if abs_mag is not None and color is not None:
            if absorption is not None and not np.isnan(absorption):
                abs_mag = abs_mag + absorption  # apply the absorption term

            output.append({'origin': an.origin, 'abs_mag': abs_mag, 'color': color})

    return output


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
          Partial match to the origin,
          associated with a catalog cross match,
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
                            type: float
                          abs_mag:
                            type: float

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

        catalog = self.get_query_argument('catalog', None)  # "GAIA"
        mag_key = self.get_query_argument('apparentMagKey', None)  # "Mag_G"
        parallax_key = self.get_query_argument('parallaxKey', None)  # "Plx"
        absorption_key = self.get_query_argument('absorptionKey', None)  # "A_G"
        abs_mag_key = self.get_query_argument('absoluteMagKey', None)  # None
        blue_mag_key = self.get_query_argument('blueMagKey', None)  # "Mag_Bp"
        red_mag_key = self.get_query_argument('redMagKey', None)  # "Mag_Rp"
        color_key = self.get_query_argument('colorKey', None)  # None

        output = get_color_mag(
            annotations,
            catalog=catalog,
            apparentMagKey=mag_key,
            parallaxKey=parallax_key,
            absorptionKey=absorption_key,
            absoluteMagKey=abs_mag_key,
            blueMagKey=blue_mag_key,
            redMagKey=red_mag_key,
            colorKey=color_key,
        )

        self.verify_and_commit()

        return self.success(data=output)
