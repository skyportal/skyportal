import dustmaps.sfd
import numpy as np
import sqlalchemy as sa
from astropy import coordinates as ap_coord
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env

from ...models import (
    Annotation,
    Classification,
    Comment,
    Obj,
    PhotometricSeries,
    Photometry,
    SourcesConfirmedInGCN,
    Spectrum,
)
from ...utils.calculations import great_circle_distance
from ...utils.offset import _calculate_best_position_for_offset_stars
from ..base import BaseHandler

_, cfg = load_env()


class ObjHandler(BaseHandler):
    @auth_or_token  # ACLs will be checked below based on configs
    async def delete(self, obj_id):
        """
        ---
        summary: Delete an Obj
        description: Delete an Obj
        tags:
          - objs
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        async with self.AsyncSession() as session:
            obj = await session.scalar(
                Obj.select(session.user_or_token, mode="delete").where(Obj.id == obj_id)
            )
            if obj is None:
                return self.error(f"Cannot find object with ID {obj_id}.")

            # Counts of dependent rows that must be cleared before deletion.
            for related_cls, label in (
                (Annotation, "annotations"),
                (Spectrum, "spectra"),
                (Photometry, "photometry"),
                (PhotometricSeries, "photometric series"),
                (Comment, "comments"),
                (Classification, "classifications"),
                (SourcesConfirmedInGCN, "sources in gcns"),
            ):
                count = await session.scalar(
                    sa.select(func.count()).select_from(
                        sa.select(related_cls)
                        .where(related_cls.obj_id == obj.id)
                        .distinct()
                    )
                )
                if count > 0:
                    return self.error(
                        f"Please remove all associated {label} from object with ID {obj_id} before removing."
                    )

            await session.delete(obj)
            await session.commit()
            return self.success()


class ObjPositionHandler(BaseHandler):
    def validate_list_parameter(self, param, default=None, dtype="int"):
        """Validate a list parameter.

        Parameters
        ----------
        param : str, list, int
            The parameter to validate.
        default : list, optional
            The default value to return if the parameter is None.
        dtype : str, optional
            The data type of the parameter. Must be one of "int", "float", "str", or "bool".

        Returns
        -------
        list
            The validated parameter.
        """

        operator = int
        if dtype == "float":
            operator = float
        elif dtype == "str":
            operator = str
        elif dtype == "bool":
            operator = bool
        else:
            raise ValueError(f"Invalid dtype: {dtype}")

        if param is None:
            return default
        if isinstance(param, str):
            try:
                return [operator(id) for id in param.split(",")]
            except ValueError:
                return self.error(
                    f"Invalid {param} parameter, must be a comma-separated list of {dtype}s"
                )
        elif isinstance(param, list | tuple):
            try:
                return [operator(id) for id in param]
            except ValueError:
                return self.error(
                    f"Invalid {param} parameter, must be a comma-separated list of {dtype}s"
                )
        elif isinstance(param, int):
            return [param]
        else:
            return self.error(
                f"Invalid {param} parameter, must be a comma-separated list of {dtype}s"
            )

    @auth_or_token
    async def get(self, obj_id):
        """
        ---
        summary: Retrieve photometry-based position of an Obj
        description: Calculate the position of an Obj using its photometry
        tags:
          - objs
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    ra:
                      type: number
                      description: Right ascension of the object
                    dec:
                      type: number
                      description: Declination of the object
          400:
            content:
              application/json:
                schema: Error
        """
        instrument_ids = self.get_query_argument("instrument_ids", None)
        stream_ids = self.get_query_argument("stream_ids", None)
        stream_only = self.get_query_argument("stream_only", False)

        snr_threshold = self.get_query_argument("snr_threshold", 3.0, type=float)
        method = self.get_query_argument("method", "snr2")

        # VALIDATE INSTRUMENT IDS IF PROVIDED
        if instrument_ids is not None:
            instrument_ids = self.validate_list_parameter(instrument_ids, dtype="int")

        # VALIDATE STREAM IDS IF PROVIDED
        if stream_ids is not None:
            stream_ids = self.validate_list_parameter(stream_ids, dtype="int")

        # VALIDATE SNR THRESHOLD
        if snr_threshold is None or snr_threshold <= 0:
            return self.error(
                "Invalid snr_threshold parameter, must be a positive float"
            )

        # VALIDATE METHOD
        if method not in ["snr2", "invvar"]:
            return self.error(
                'Invalid method parameter, must be one of "snr2" or "invvar"'
            )

        async with self.AsyncSession() as session:
            try:
                obj = await session.scalar(
                    Obj.select(session.user_or_token).where(Obj.id == obj_id)
                )
                if obj is None:
                    return self.error(f"Could not load object with ID {obj_id}")
            except Exception:
                return self.error(f"Could not load object with ID {obj_id}")

            try:
                # DATABASE QUERY AND FILTERING
                query_constraints = [
                    Photometry.obj_id == obj_id,
                    ~Photometry.origin.ilike(
                        "%fp%"
                    ),  # always exclude forced photometry
                ]
                if instrument_ids is not None:
                    query_constraints.append(
                        Photometry.instrument_id.in_(instrument_ids)
                    )
                if stream_ids is not None:
                    query_constraints.append(Photometry.stream_id.in_(stream_ids))

                phot_stmt = sa.select(Photometry).where(sa.and_(*query_constraints))
                # `len(p.streams)` is checked below if `stream_only` is set;
                # eager-load to avoid a MissingGreenlet inside the filter.
                if stream_only and not stream_ids:
                    phot_stmt = phot_stmt.options(selectinload(Photometry.streams))
                photometry_result = await session.scalars(phot_stmt)
                photometry = photometry_result.all()

                # POST-QUERY FILTERING
                additional_constraints = [
                    lambda p: (
                        p.flux / p.fluxerr > snr_threshold
                    ),  # signal-to-noise ratio threshold
                ]
                if (
                    stream_only and not stream_ids
                ):  # if stream_ids are provided, we don't need to check for streams at all
                    additional_constraints.append(lambda p: p and len(p.streams) > 0)

                photometry = [
                    p
                    for p in photometry
                    if not np.isnan(p.flux)
                    and not np.isnan(p.fluxerr)
                    and p.fluxerr != 0
                    and p.ra is not None
                    and not np.isnan(p.ra)
                    and p.dec is not None
                    and not np.isnan(p.dec)
                    and all(constraint(p) for constraint in additional_constraints)
                ]

                ra, dec = _calculate_best_position_for_offset_stars(
                    photometry,
                    fallback=(obj.ra, obj.dec),
                    how=method,
                )
                skycoord = ap_coord.SkyCoord(obj.ra, obj.dec, unit="deg")
                return self.success(
                    data={
                        "ra": ra,
                        "dec": dec,
                        "gal_lon": skycoord.galactic.l.deg,
                        "gal_lat": skycoord.galactic.b.deg,
                        "ebv": float(dustmaps.sfd.SFDQuery()(skycoord)),
                        "separation": float(
                            great_circle_distance(ra, dec, obj.ra, obj.dec) * 3600
                        ),
                        "discovery_ra": obj.ra,
                        "discovery_dec": obj.dec,
                    }
                )
            except Exception as e:
                return self.error(
                    f"An error occurred while calculating the object's position: {e}"
                )
