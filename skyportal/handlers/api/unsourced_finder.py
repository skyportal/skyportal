import functools
import io
from typing import Literal

from astropy.time import Time
from dateutil.parser import isoparse
from numpy import ma
from pydantic import BaseModel, ConfigDict, Field
from tornado.ioloop import IOLoop

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from baselayer.log import make_log

from ...utils.naive_datetime import utcnow_naive
from ...utils.offset import (
    GaiaQuery,
    facility_parameters,
    get_finding_chart,
    source_image_parameters,
)
from ..base import BaseHandler

_, cfg = load_env()
log = make_log("api/unsourced_finder")


class UnsourcedFinderGetQuery(BaseModel):
    """Query parameters for generating a finding chart for a position or Gaia ID."""

    model_config = ConfigDict(extra="forbid")

    location_type: Literal["gaia_dr3", "gaia_dr2", "pos"] = Field(
        description=(
            "What is the type of the search? From gaia or by position? If `pos` "
            "then `ra` and `dec` should be given. If otherwise, the catalog is "
            "queried for id `catalog_id` and the position information is pulled "
            "from there."
        ),
    )
    catalog_id: str = Field(
        default="unknown",
        description="ID of the object in the Gaia catalog (if `location_type` is not `pos`).",
    )
    ra: float | None = Field(
        default=None,
        description=(
            "RA of the source of interest at the time of observation of "
            "interest (ie. the user is responsible for proper motion "
            "calulations). Required if `location_type` is `pos`."
        ),
    )
    dec: float | None = Field(
        default=None,
        description=(
            "DEC of the source of interest at the time of observation of "
            "interest (ie. the user is responsible for proper motion "
            "calulations). Required if `location_type` is `pos`."
        ),
    )
    imsize: float = Field(
        default=4.0,
        description="Image size in arcmin (square). Defaults to 4.0",
    )
    facility: Literal[*facility_parameters] = Field(
        default="Keck",
        description="What type of starlist should be used? Defaults to Keck",
    )
    image_source: Literal[*source_image_parameters] = Field(
        default="ps1",
        description="Source of the image used in the finding chart. Defaults to ps1",
    )
    use_ztfref: bool = Field(
        default=True,
        description=(
            "Use ZTFref catalog for offset star positions, otherwise DR3. "
            "Defaults to True."
        ),
    )
    obstime: str | None = Field(
        default=None,
        description=(
            "datetime of observation in isoformat (e.g. 2020-12-30T12:34:10). "
            "Defaults to now."
        ),
    )
    type: Literal["png", "pdf"] = Field(
        default="pdf",
        description="Output datafile type. Defaults to pdf.",
    )
    num_offset_stars: int = Field(
        default=3,
        description="Number of offset stars to determine and show [0,4] (default: 3)",
    )


class UnsourcedFinderHandler(BaseHandler):
    @auth_or_token
    async def get(self, *, query: UnsourcedFinderGetQuery = None):
        """
        ---
        summary: Get a finding chart for a position or Gaia ID
        description: Generate a PDF/PNG finding chart for a position or Gaia ID
        tags:
          - finding charts
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
        query = self.parse_query(UnsourcedFinderGetQuery)

        location_type = query.location_type

        obstime = (
            query.obstime if query.obstime is not None else utcnow_naive().isoformat()
        )
        try:
            isoparse(obstime)
        except (ValueError, TypeError):
            return self.error("obstime is not valid isoformat")

        catalog_id = query.catalog_id

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
            ra = query.ra
            if ra is None:
                return self.error("Missing argument `ra`")
            if not 0 <= ra < 360.0:
                return self.error("Invalid value for `ra`: must be 0 <= ra < 360.0")
            dec = query.dec
            if dec is None:
                return self.error("Missing argument `dec`")
            if not -90 <= dec <= 90.0:
                return self.error(
                    "Invalid value for `dec`: must be in the range [-90,90]"
                )
            obj_id = f"{ra:0.6g}{dec:+0.6g}"
            extra_display_string = ""

        output_type = query.type

        imsize = query.imsize
        if imsize < 2.0 or imsize > 15.0:
            return self.error("The value for `imsize` is outside the allowed range")

        facility = query.facility
        image_source = query.image_source
        use_ztfref = query.use_ztfref

        num_offset_stars = query.num_offset_stars
        if not 0 <= num_offset_stars <= 4:
            return self.error(
                "The value for `num_offset_stars` is outside the allowed range [0, 4]"
            )

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
        if not rez.get("success", True):
            return self.error(rez.get("reason", "Could not generate finding chart"))

        filename = rez["name"]
        data = io.BytesIO(rez["data"])

        await self.send_file(data, filename, output_type=output_type)
