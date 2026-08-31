from typing import Any, Literal

import dustmaps.sfd
import numpy as np
import sqlalchemy as sa
from astropy import coordinates as ap_coord
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env

from ...models import (
    Annotation,
    Classification,
    Comment,
    GcnEventObj,
    Obj,
    PhotometricSeries,
    Photometry,
    Spectrum,
)
from ...utils.acknowledgment import build_acknowledgment
from ...utils.calculations import great_circle_distance
from ...utils.offset import _calculate_best_position_for_offset_stars
from ..base import BaseHandler

_, cfg = load_env()


class ObjBody(BaseModel):
    """Shared optional `Obj` fields accepted by the Obj marshmallow schema
    (``Obj.__schema__()``) on source/candidate writes. Deep validation and
    coercion are still performed by that schema; this only constrains the
    top-level shape."""

    # Survey ids (e.g. LSST diaObject) arrive as JSON numbers, but Obj.id is a
    # string column; pydantic rejects int for `str` unless told to coerce.
    model_config = ConfigDict(extra="forbid", coerce_numbers_to_str=True)

    ra: float | None = Field(None, description="ICRS Right Ascension [deg].")
    dec: float | None = Field(None, description="ICRS Declination [deg].")
    ra_dis: float | None = Field(
        None, description="J2000 Right Ascension at discovery time [deg]."
    )
    dec_dis: float | None = Field(
        None, description="J2000 Declination at discovery time [deg]."
    )
    ra_err: float | None = Field(
        None, description="Error on J2000 Right Ascension at discovery time [deg]."
    )
    dec_err: float | None = Field(
        None, description="Error on J2000 Declination at discovery time [deg]."
    )
    offset: float | None = Field(
        None, description="Offset from nearest static object [arcsec]."
    )
    t0: float | None = Field(None, description="Reference time.")
    redshift: float | None = Field(None, description="Redshift.")
    redshift_error: float | None = Field(None, description="Redshift error.")
    redshift_origin: str | None = Field(None, description="Redshift source.")
    redshift_history: Any = Field(
        None, description="Record of who set which redshift values and when."
    )
    host_id: int | None = Field(
        None, description="The ID of the Galaxy to which this Obj is associated."
    )
    summary: str | None = Field(None, description="Summary of the obj.")
    summary_history: Any = Field(
        None,
        description="Record of the summaries generated and written about this obj",
    )
    altdata: Any = Field(
        None,
        description="Misc. alternative metadata stored in JSON format, e.g. "
        "`{'gaia': {'info': {'Teff': 5780}}}`",
    )
    dist_nearest_source: float | None = Field(
        None, description="Distance to the nearest Obj [arcsec]."
    )
    mag_nearest_source: float | None = Field(
        None, description="Magnitude of the nearest Obj [AB]."
    )
    e_mag_nearest_source: float | None = Field(
        None, description="Error on magnitude of the nearest Obj [mag]."
    )
    transient: bool | None = Field(
        None,
        description="Boolean indicating whether the object is an astrophysical transient.",
    )
    varstar: bool | None = Field(
        None,
        description="Boolean indicating whether the object is a variable star.",
    )
    is_roid: bool | None = Field(
        None,
        description="Boolean indicating whether the object is a moving object.",
    )
    mpc_name: str | None = Field(None, description="Minor planet center name.")
    gcn_crossmatch: list[str] | None = Field(
        None, description="List of GCN event dateobs for crossmatched events."
    )
    tns_name: str | None = Field(None, description="Transient Name Server name.")
    tns_info: Any = Field(None, description="TNS info in JSON format")
    score: float | None = Field(None, description="Machine learning score.")
    origin: str | None = Field(None, description="Origin of the object.")
    alias: list[str] | None = Field(
        None, description="Alternative names for this object."
    )
    internal_key: str | None = Field(
        None, description="Internal key used for secure websocket messaging."
    )
    detect_photometry_count: int | None = Field(
        None,
        description="How many times the object was detected above the S/N threshold.",
    )


class ObjHandler(BaseHandler):
    @auth_or_token  # ACLs will be checked below based on configs
    async def delete(self, obj_id: str):
        """
        ---
        summary: Delete an Obj
        description: Delete an Obj
        tags:
          - objs
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
                (GcnEventObj, "sources in gcns"),
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


class ObjPositionGetQuery(BaseModel):
    """Query parameters for computing an Obj's photometry-based position."""

    model_config = ConfigDict(extra="forbid")

    instrument_ids: list[int] | None = Field(
        default=None,
        description="Only use photometry from these instrument IDs.",
    )
    stream_ids: list[int] | None = Field(
        default=None,
        description="Only use photometry from these stream IDs.",
    )
    stream_only: bool = Field(
        default=False,
        description="If true, only use photometry that belongs to at least one stream. Ignored when `stream_ids` is given.",
    )
    snr_threshold: float = Field(
        default=3.0,
        description="Only use photometry with a signal-to-noise ratio above this threshold. Defaults to 3.0.",
    )
    method: Literal["snr2", "invvar"] = Field(
        default="snr2",
        description="Weighting method used to combine the photometry positions. Defaults to snr2.",
    )


class ObjPositionHandler(BaseHandler):
    @auth_or_token
    async def get(self, obj_id: str, *, query: ObjPositionGetQuery = None):
        """
        ---
        summary: Retrieve photometry-based position of an Obj
        description: Calculate the position of an Obj using its photometry
        tags:
          - objs
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
        query = self.parse_query(ObjPositionGetQuery)

        if query.snr_threshold <= 0:
            return self.error(
                "Invalid snr_threshold parameter, must be a positive float"
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
                query_constraints = [
                    Photometry.obj_id == obj_id,
                    ~Photometry.origin.ilike(
                        "%fp%"
                    ),  # always exclude forced photometry
                ]
                if query.instrument_ids is not None:
                    query_constraints.append(
                        Photometry.instrument_id.in_(query.instrument_ids)
                    )
                if query.stream_ids is not None:
                    query_constraints.append(Photometry.stream_id.in_(query.stream_ids))

                # `stream_ids` already restricts to streams on its own.
                check_streams = query.stream_only and not query.stream_ids

                phot_stmt = sa.select(Photometry).where(sa.and_(*query_constraints))
                # `len(p.streams)` is checked below if `stream_only` is set;
                # eager-load to avoid a MissingGreenlet inside the filter.
                if check_streams:
                    phot_stmt = phot_stmt.options(selectinload(Photometry.streams))
                photometry_result = await session.scalars(phot_stmt)

                photometry = [
                    p
                    for p in photometry_result.all()
                    if not np.isnan(p.flux)
                    and not np.isnan(p.fluxerr)
                    and p.fluxerr != 0
                    and p.ra is not None
                    and not np.isnan(p.ra)
                    and p.dec is not None
                    and not np.isnan(p.dec)
                    and p.flux / p.fluxerr > query.snr_threshold
                    and (not check_streams or len(p.streams) > 0)
                ]

                ra, dec = _calculate_best_position_for_offset_stars(
                    photometry,
                    fallback=(obj.ra, obj.dec),
                    how=query.method,
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


class ObjAcknowledgmentGetQuery(BaseModel):
    """Which detected components to include in the assembled text."""

    model_config = ConfigDict(extra="forbid")

    exclude_filter_ids: list[int] | None = Field(
        default=None,
        description="Filters not to cite. Omit to cite every one detected.",
    )
    exclude_instrument_ids: list[int] | None = Field(
        default=None,
        description="Instruments not to cite. Omit to cite every one detected.",
    )
    exclude_allocation_ids: list[int] | None = Field(
        default=None,
        description="Allocations not to cite. Omit to cite every one detected.",
    )


class ObjAcknowledgmentHandler(BaseHandler):
    @auth_or_token
    async def get(self, obj_id: str, *, query: ObjAcknowledgmentGetQuery = None):
        """
        ---
        summary: Retrieve the acknowledgment block for an Obj
        description: |
          Build the citation text for a source from what it actually used: the
          instance, the filters and brokers that selected it, the facilities
          that supplied its photometry and spectra, and the programs it was
          observed under. Returns the assembled paragraph and the components it
          was built from, so a caller can drop anything unused.
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
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          type: object
                          properties:
                            text:
                              type: string
                              description: The assembled acknowledgment paragraph
                            components:
                              type: object
                              description: The parts the text was built from
          400:
            content:
              application/json:
                schema: Error
        """
        query = self.parse_query(ObjAcknowledgmentGetQuery)

        async with self.AsyncSession() as session:
            obj = await session.scalar(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            )
            if obj is None:
                return self.error(f"Could not load object with ID {obj_id}")

            return self.success(
                data=await build_acknowledgment(
                    session,
                    session.user_or_token,
                    obj_id,
                    exclude_filter_ids=query.exclude_filter_ids,
                    exclude_instrument_ids=query.exclude_instrument_ids,
                    exclude_allocation_ids=query.exclude_allocation_ids,
                )
            )
