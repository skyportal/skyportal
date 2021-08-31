import io
import math
import datetime
import functools

import numpy.ma as ma
from dateutil.parser import isoparse
from astropy.time import Time
import tornado
from tornado.ioloop import IOLoop

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from baselayer.log import make_log

from ..base import BaseHandler

from ...utils.offset import (
    GaiaQuery,
    facility_parameters,
    source_image_parameters,
    get_finding_chart,
)

_, cfg = load_env()
log = make_log('api/unsourced_finder')


class UnSourcedFinderHandler(BaseHandler):
    @auth_or_token
    async def get(self):
        """
        ---
        description: Generate a PDF/PNG finding chart for a position or Gaia ID
        parameters:
        - in: query
          name: location_type
          nullable: false
          required: true
          schema:
            type: string
            enum: [gaia_edr3, gaia_dr2, pos]
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
        - in: query
          name: dec
          schema:
            type: float
            minimum: -90.0
            maximum: 90.0
        - in: query
          name: imsize
          schema:
            type: float
            minimum: 2
            maximum: 15
          description: Image size in arcmin (square)
        - in: query
          name: facility
          nullable: true
          schema:
            type: string
            enum: [Keck, Shane, P200]
        - in: query
          name: image_source
          nullable: true
          schema:
            type: string
            enum: [desi, dss, ztfref]
          description: Source of the image used in the finding chart
        - in: query
          name: use_ztfref
          required: false
          schema:
            type: boolean
          description: |
            Use ZTFref catalog for offset star positions, otherwise DR2
        - in: query
          name: obstime
          nullable: True
          schema:
            type: string
          description: |
            datetime of observation in isoformat (e.g. 2020-12-30T12:34:10)
        - in: query
          name: type
          nullable: true
          schema:
            type: string
            enum: [png, pdf]
          description: |
            output type
        - in: query
          name: num_offset_stars
          schema:
            type: integer
            minimum: 0
            maximum: 4
          description: |
            output desired number of offset stars [0,4] (default: 3)
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
        location_type = self.get_query_argument('location_type')
        if location_type not in ["gaia_edr3", "gaia_dr2", "pos"]:
            return self.error(f'Invalid argument for `location_type`: {location_type}')

        obstime = self.get_query_argument(
            'obstime', datetime.datetime.utcnow().isoformat()
        )
        if not isinstance(isoparse(obstime), datetime.datetime):
            return self.error('obstime is not valid isoformat')

        catalog_id = self.get_query_argument('catalog_id', 'unknown')
        if location_type != "pos":
            # database name should be something like gaiaedr3
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
            g = GaiaQuery()
            r = g.query(query_string)
            if len(r) != 1:
                return self.error(
                    f'Cannot get position information for `catalog_id` = {catalog_id}'
                )
            ra = r["ra_obs"].data[0]
            dec = r["dec_obs"].data[0]
            obj_id = f'{location_type.split("_")[-1]} {catalog_id}'
            pmra, pmdec = ma.getdata(r["pmra"])[0], ma.getdata(r["pmdec"])[0]
            extra_display_string = f'{pmra:0.4} E \u2033/yr {pmdec:0.4} N \u2033/yr'
        else:
            ra = self.get_query_argument('ra')
            try:
                ra = float(ra)
            except ValueError:
                # could not handle inputs
                return self.error('Invalid argument for `ra`')
            dec = self.get_query_argument('dec')
            try:
                dec = float(dec)
            except ValueError:
                # could not handle inputs
                return self.error('Invalid argument for `dec`')
            obj_id = f'{ra:0.5}{dec:+d}'
            extra_display_string = ""

        output_type = self.get_query_argument('type', 'pdf')
        if output_type not in ["png", "pdf"]:
            return self.error(f'Invalid argument for `type`: {output_type}')

        imsize = self.get_query_argument('imsize', '4.0')
        try:
            imsize = float(imsize)
        except ValueError:
            # could not handle inputs
            return self.error('Invalid argument for `imsize`')

        if imsize < 2.0 or imsize > 15.0:
            return self.error('The value for `imsize` is outside the allowed range')

        facility = self.get_query_argument('facility', 'Keck')
        image_source = self.get_query_argument('image_source', 'ztfref')
        use_ztfref = self.get_query_argument('use_ztfref', True)
        if isinstance(use_ztfref, str):
            use_ztfref = use_ztfref in ['t', 'True', 'true', 'yes', 'y']

        num_offset_stars = self.get_query_argument('num_offset_stars', '3')
        try:
            num_offset_stars = int(num_offset_stars)
        except ValueError:
            # could not handle inputs
            return self.error('Invalid argument for `num_offset_stars`')

        if facility not in facility_parameters:
            return self.error('Invalid facility')

        if image_source not in source_image_parameters:
            return self.error('Invalid source image')

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
            'Finding chart generation in progress. Download will start soon.'
        )
        rez = await IOLoop.current().run_in_executor(None, finder)

        filename = rez["name"]
        image = io.BytesIO(rez["data"])

        # Adapted from
        # https://bhch.github.io/posts/2017/12/serving-large-files-with-tornado-safely-without-blocking/
        mb = 1024 * 1024 * 1
        chunk_size = 1 * mb
        max_file_size = 15 * mb
        if not (image.getbuffer().nbytes < max_file_size):
            return self.error(
                f"Refusing to send files larger than {max_file_size / mb:.2f} MB"
            )

        # do not send result via `.success`, since that creates a JSON
        self.set_status(200)
        if output_type == "pdf":
            self.set_header("Content-Type", "application/pdf; charset='utf-8'")
            self.set_header("Content-Disposition", f"attachment; filename={filename}")
        else:
            self.set_header("Content-type", f"image/{output_type}")

        self.set_header(
            'Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0'
        )

        self.verify_and_commit()

        for i in range(math.ceil(max_file_size / chunk_size)):
            chunk = image.read(chunk_size)
            if not chunk:
                break
            try:
                self.write(chunk)  # write the chunk to response
                await self.flush()  # send the chunk to client
            except tornado.iostream.StreamClosedError:
                # this means the client has closed the connection
                # so break the loop
                break
            finally:
                # deleting the chunk is very important because
                # if many clients are downloading files at the
                # same time, the chunks in memory will keep
                # increasing and will eat up the RAM
                del chunk

                # pause the coroutine so other handlers can run
                await tornado.gen.sleep(1e-9)  # 1 ns
