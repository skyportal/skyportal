import datetime
import functools
import io

from astropy.time import Time
from dateutil.parser import isoparse
from numpy import ma
from tornado.ioloop import IOLoop

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from baselayer.log import make_log

from ...utils.offset import (
    GaiaQuery,
    facility_parameters,
    get_finding_chart,
    source_image_parameters,
)
from ..base import BaseHandler

_, cfg = load_env()
log = make_log("api/unsourced_finder")


class UnsourcedFinderHandler(BaseHandler):
    @auth_or_token
    async def get(self):
        """
        ---
        summary: Get a finding chart for a position or Gaia ID
        description: Generate a PDF/PNG finding chart for a position or Gaia ID
        tags:
          - finding charts
        parameters:
        - in: query
          name: location_type
          nullable: false
          required: true
          schema:
            type: string
            enum: [gaia_dr3, gaia_dr2, pos]
          description: |
            What is the type of the search? From gaia or by position? If `pos`
            then `ra` and `dec` should be given. If otherwise, the catalog
            is queried for id `catalog_id` and the position information is
            pulled from there.
        - in: query
          name: catalog_id
          schema:
            type: string
        - in: query
          name: ra
          schema:
            type: float
            minimum: 0.0
            maximum: 360.0
            exclusiveMaximum: true
            description: |
               RA of the source of interest at the time of observation of
               interest (ie. the user is responsible for proper motion
               calulations).
        - in: query
          name: dec
          schema:
            type: float
            minimum: -90.0
            maximum: 90.0
            description: |
               DEC of the source of interest at the time of observation of
               interest (ie. the user is responsible for proper motion
               calulations).
        - in: query
          name: imsize
          schema:
            type: float
            minimum: 2
            maximum: 15
          description: Image size in arcmin (square). Defaults to 4.0
        - in: query
          name: facility
          nullable: true
          schema:
            type: string
            enum: [Keck, Shane, P200, P200-NGPS]
            description: |
               What type of starlist should be used? Defaults to Keck
        - in: query
          name: image_source
          nullable: true
          schema:
            type: string
            enum: [ps1, desi, dss, ztfref]
          description: |
            Source of the image used in the finding chart. Defaults to ps1
        - in: query
          name: use_ztfref
          required: false
          schema:
            type: boolean
          description: |
            Use ZTFref catalog for offset star positions, otherwise DR3.
            Defaults to True.
        - in: query
          name: obstime
          nullable: True
          schema:
            type: string
          description: |
            datetime of observation in isoformat (e.g. 2020-12-30T12:34:10).
            Defaults to now.
        - in: query
          name: type
          nullable: true
          schema:
            type: string
            enum: [png, pdf]
          description: |
            Output datafile type. Defaults to pdf.
        - in: query
          name: num_offset_stars
          schema:
            type: integer
            minimum: 0
            maximum: 4
          description: |
            Number of offset stars to determine and show [0,4] (default: 3)
        responses:
          200:
            description: A PDF/PNG finding chart file
            content:
              application/pdf:
                schema:
                  type: string
                  format: binary
              image/png:
                schema:
                  type: string
                  format: binary
          400:
            content:
              application/json:
                schema: Error
        """
        location_type = self.get_query_argument("location_type")
        if location_type not in ["gaia_dr3", "gaia_dr2", "pos"]:
            return self.error(f"Invalid argument for `location_type`: {location_type}")

        obstime = self.get_query_argument(
            "obstime", datetime.datetime.utcnow().isoformat()
        )
        if not isinstance(isoparse(obstime), datetime.datetime):
            return self.error("obstime is not valid isoformat")

        catalog_id = self.get_query_argument("catalog_id", "unknown")

        if location_type != "pos":
            # a Gaia source must be all integer characters
            if not catalog_id.isnumeric():
                return self.error("`catalog_id` must be a number")

            # database name should be something like gaiadr3
            db_name = "".join(location_type.split("_"))
            obstime_decimalyear = Time(isoparse(obstime)).decimalyear
            query_string = f"""
                SELECT source_id, ra, dec, pmra, pmdec, coord1(prop) AS ra_obs, coord2(prop) AS dec_obs FROM (
                    SELECT gaia.source_id, ra, dec, pmra, pmdec,
                    EPOCH_PROP_POS(ra, dec, parallax, pmra, pmdec, 0, ref_epoch, {obstime_decimalyear}) AS prop
                    FROM {db_name}.gaia_source AS gaia
                WHERE gaia.source_id={catalog_id}
                ) AS subquery
            """
            gaia_query = GaiaQuery()
            response = gaia_query.query(query_string)
            if len(response) != 1:
                return self.error(
                    f"Cannot get position information for `catalog_id` = {catalog_id}"
                )
            ra = response["ra_obs"].data[0]
            dec = response["dec_obs"].data[0]
            obj_id = f"{location_type.split('_')[-1]} {catalog_id}"
            pmra, pmdec = (
                ma.getdata(response["pmra"])[0],
                ma.getdata(response["pmdec"])[0],
            )
            extra_display_string = f"{pmra:0.4} E \u2033/yr {pmdec:0.4} N \u2033/yr"
        else:
            ra = self.get_query_argument("ra")
            try:
                ra = float(ra)
            except ValueError:
                # could not handle inputs
                return self.error("Invalid argument for `ra`")
            if not 0 <= ra < 360.0:
                return self.error("Invalid value for `ra`: must be 0 <= ra < 360.0")
            dec = self.get_query_argument("dec")
            try:
                dec = float(dec)
            except ValueError:
                # could not handle inputs
                return self.error("Invalid argument for `dec`")
            if not -90 <= dec <= 90.0:
                return self.error(
                    "Invalid value for `dec`: must be in the range [-90,90]"
                )
            obj_id = f"{ra:0.6g}{dec:+0.6g}"
            extra_display_string = ""

        output_type = self.get_query_argument("type", "pdf")
        if output_type not in ["png", "pdf"]:
            return self.error(f"Invalid argument for `type`: {output_type}")

        imsize = self.get_query_argument("imsize", "4.0")
        try:
            imsize = float(imsize)
        except ValueError:
            # could not handle inputs
            return self.error("Invalid argument for `imsize`")

        if imsize < 2.0 or imsize > 15.0:
            return self.error("The value for `imsize` is outside the allowed range")

        facility = self.get_query_argument("facility", "Keck")
        image_source = self.get_query_argument("image_source", "ps1")
        use_ztfref = self.get_query_argument("use_ztfref", True)
        if isinstance(use_ztfref, str):
            use_ztfref = use_ztfref in ["t", "True", "true", "yes", "y"]

        num_offset_stars = self.get_query_argument("num_offset_stars", "3")
        try:
            num_offset_stars = int(num_offset_stars)
        except ValueError:
            # could not handle inputs
            return self.error("Invalid argument for `num_offset_stars`")

        if not 0 <= num_offset_stars <= 4:
            return self.error(
                "The value for `num_offset_stars` is outside the allowed range [0, 4]"
            )

        if facility not in facility_parameters:
            return self.error("Invalid facility")

        if image_source not in source_image_parameters:
            return self.error("Invalid source image")

        radius_degrees = facility_parameters[facility]["radius_degrees"]
        mag_limit = facility_parameters[facility]["mag_limit"]
        min_sep_arcsec = facility_parameters[facility]["min_sep_arcsec"]
        mag_min = facility_parameters[facility]["mag_min"]

        finder = functools.partial(
            get_finding_chart,
            ra,
            dec,
            obj_id,
            image_source=image_source,
            output_format=output_type,
            imsize=imsize,
            how_many=num_offset_stars,
            radius_degrees=radius_degrees,
            mag_limit=mag_limit,
            mag_min=mag_min,
            min_sep_arcsec=min_sep_arcsec,
            starlist_type=facility,
            obstime=obstime,
            use_source_pos_in_starlist=True,
            allowed_queries=2,
            queries_issued=0,
            use_ztfref=use_ztfref,
            extra_display_string=extra_display_string,
        )

        self.push_notification(
            "Finding chart generation in progress. Download will start soon."
        )
        rez = await IOLoop.current().run_in_executor(None, finder)

        filename = rez["name"]
        data = io.BytesIO(rez["data"])

        await self.send_file(data, filename, output_type=output_type)
