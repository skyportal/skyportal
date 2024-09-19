import dustmaps.sfd
import numpy as np
import sqlalchemy as sa
from astropy import coordinates as ap_coord
from sqlalchemy import func

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from ..base import BaseHandler
from ...models import (
    Annotation,
    Classification,
    Comment,
    Obj,
    PhotometricSeries,
    Photometry,
    Spectrum,
    SourcesConfirmedInGCN,
)
from ...utils.offset import _calculate_best_position_for_offset_stars
from ...utils.calculations import great_circle_distance

_, cfg = load_env()


class ObjHandler(BaseHandler):
    @auth_or_token  # ACLs will be checked below based on configs
    def delete(self, obj_id):
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
        with self.Session() as session:
            obj = session.scalars(
                Obj.select(session.user_or_token, mode='delete').where(Obj.id == obj_id)
            ).first()
            if obj is None:
                return self.error(f"Cannot find object with ID {obj_id}.")

            stmt = sa.select(Annotation).where(Annotation.obj_id == obj.id)
            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            total_annotations = session.execute(count_stmt).scalar()
            if total_annotations > 0:
                return self.error(
                    f"Please remove all associated annotations from object with ID {obj_id} before removing."
                )

            stmt = sa.select(Spectrum).where(Spectrum.obj_id == obj.id)
            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            total_spectrum = session.execute(count_stmt).scalar()
            if total_spectrum > 0:
                return self.error(
                    f"Please remove all associated spectra from object with ID {obj_id} before removing."
                )

            stmt = sa.select(Photometry).where(Photometry.obj_id == obj.id)
            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            total_photometry = session.execute(count_stmt).scalar()
            if total_photometry > 0:
                return self.error(
                    f"Please remove all associated photometry from object with ID {obj_id} before removing."
                )

            stmt = sa.select(PhotometricSeries).where(
                PhotometricSeries.obj_id == obj.id
            )
            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            total_photometric_series = session.execute(count_stmt).scalar()
            if total_photometric_series > 0:
                return self.error(
                    f"Please remove all associated photometric series from object with ID {obj_id} before removing."
                )

            stmt = sa.select(Comment).where(Comment.obj_id == obj.id)
            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            total_comments = session.execute(count_stmt).scalar()
            if total_comments > 0:
                return self.error(
                    f"Please remove all associated comments on object with ID {obj_id} before removing."
                )

            stmt = sa.select(Classification).where(Classification.obj_id == obj.id)
            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            total_classifications = session.execute(count_stmt).scalar()
            if total_classifications > 0:
                return self.error(
                    f"Please remove all associated classifications on object with ID {obj_id} before removing."
                )

            stmt = sa.select(SourcesConfirmedInGCN).where(
                SourcesConfirmedInGCN.obj_id == obj.id
            )
            count_stmt = sa.select(func.count()).select_from(stmt.distinct())
            total_sources_in_gcn = session.execute(count_stmt).scalar()
            if total_sources_in_gcn > 0:
                return self.error(
                    f"Please remove all associated sources in gcns associated with the object with ID {obj_id} before removing."
                )

            session.delete(obj)
            session.commit()
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
                return [operator(id) for id in param.split(',')]
            except ValueError:
                return self.error(
                    f'Invalid {param} parameter, must be a comma-separated list of {dtype}s'
                )
        elif isinstance(param, list) or isinstance(param, tuple):
            try:
                return [operator(id) for id in param]
            except ValueError:
                return self.error(
                    f'Invalid {param} parameter, must be a comma-separated list of {dtype}s'
                )
        elif isinstance(param, int):
            return [param]
        else:
            return self.error(
                f'Invalid {param} parameter, must be a comma-separated list of {dtype}s'
            )

    @auth_or_token
    def get(self, obj_id):
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
        instrument_ids = self.get_query_argument('instrument_ids', None)
        stream_ids = self.get_query_argument('stream_ids', None)
        stream_only = self.get_query_argument('stream_only', False)

        snr_threshold = self.get_query_argument('snr_threshold', 3.0)
        method = self.get_query_argument('method', 'snr2')

        # VALIDATE INSTRUMENT IDS IF PROVIDED
        if instrument_ids is not None:
            instrument_ids = self.validate_list_parameter(instrument_ids, dtype="int")

        # VALIDATE STREAM IDS IF PROVIDED
        if stream_ids is not None:
            stream_ids = self.validate_list_parameter(stream_ids, dtype="int")

        # VALIDATE SNR THRESHOLD
        try:
            snr_threshold = float(snr_threshold)
            if snr_threshold <= 0:
                raise ValueError
        except ValueError:
            return self.error(
                'Invalid snr_threshold parameter, must be a positive float'
            )

        # VALIDATE METHOD
        if method not in ['snr2', 'invvar']:
            return self.error(
                'Invalid method parameter, must be one of "snr2" or "invvar"'
            )

        with self.Session() as session:
            try:
                obj = session.scalar(
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
                        '%fp%'
                    ),  # always exclude forced photometry
                ]
                if instrument_ids is not None:
                    query_constraints.append(
                        Photometry.instrument_id.in_(instrument_ids)
                    )
                if stream_ids is not None:
                    query_constraints.append(Photometry.stream_id.in_(stream_ids))

                photometry = (
                    session.scalars(
                        sa.select(Photometry).where(sa.and_(*query_constraints))
                    )
                ).all()

                # POST-QUERY FILTERING
                additional_constraints = [
                    lambda p: p.flux / p.fluxerr
                    > snr_threshold,  # signal-to-noise ratio threshold
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
                    }
                )
            except Exception as e:
                return self.error(
                    f"An error occurred while calculating the object's position: {e}"
                )
