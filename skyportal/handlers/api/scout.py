from functools import partial

from pydantic import BaseModel, ConfigDict, Field
from tornado.ioloop import IOLoop

from baselayer.app.access import auth_or_token

from ...models import (
    Annotation,
    Obj,
)
from ...utils.scout_ephemeris import (
    DEFAULT_HOURS,
    DEFAULT_STEP_MINUTES,
    GEOCENTRIC_OBSCODE,
    MAX_RECORDS,
    ScoutEphemerisError,
    clamp_window,
    fetch_ephemeris,
    tdes_from_annotation,
)
from ...utils.scout_ingest import ANNOTATION_ORIGIN
from ..base import BaseHandler


class ScoutEphemerisGetQuery(BaseModel):
    """Query parameters for a NEOCP candidate's ephemeris."""

    model_config = ConfigDict(extra="forbid")

    hours: float = Field(
        default=DEFAULT_HOURS,
        gt=0,
        description="Span to cover, starting now. Shortened if the requested "
        f"span and step would exceed JPL's {MAX_RECORDS}-row limit.",
    )
    stepMinutes: int = Field(
        default=DEFAULT_STEP_MINUTES,
        ge=1,
        description="Minutes between ephemeris rows.",
    )
    obsCode: str = Field(
        default=GEOCENTRIC_OBSCODE,
        description="MPC observatory code the positions are computed for. A "
        "near-Earth object's apparent place depends on it, so pass the real "
        "site rather than the geocentric default when pointing a telescope.",
    )


class ScoutEphemerisHandler(BaseHandler):
    @auth_or_token
    async def get(self, obj_id: str, *, query: ScoutEphemerisGetQuery = None):
        """
        ---
        summary: Get a NEOCP candidate's ephemeris
        description: |
          Positions over time for a JPL Scout NEOCP candidate, with the
          plane-of-sky uncertainty at each step.

          A Scout candidate is stored with one nominal position and a single
          uncertainty, which places it on the sky only when that uncertainty is
          small. Objects with a short arc carry a sigma of degrees and move
          while observed, so a position is only meaningful with a time attached.

          Fetched from JPL on each request rather than stored, since Scout
          re-fits as new astrometry arrives.
        tags:
          - sources
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
        query = self.parse_query(ScoutEphemerisGetQuery)

        async with self.AsyncSession() as session:
            obj = await session.scalar(
                Obj.select(self.associated_user_object).where(Obj.id == obj_id)
            )
            if obj is None:
                return self.error("Invalid object id.", status=404)

            annotation = await session.scalar(
                Annotation.select(self.associated_user_object).where(
                    Annotation.obj_id == obj_id,
                    Annotation.origin == ANNOTATION_ORIGIN,
                )
            )
            tdes = tdes_from_annotation(annotation.data if annotation else None)
            if not tdes:
                return self.error(
                    f"{obj_id} carries no {ANNOTATION_ORIGIN} annotation, so there "
                    "is no NEOCP designation to ask JPL about.",
                    status=404,
                )

        hours = clamp_window(query.hours, query.stepMinutes)
        # A Scout ephemeris is seconds of someone else's compute over blocking
        # HTTP; keep it off the event loop.
        call = partial(
            fetch_ephemeris,
            tdes,
            hours=hours,
            step_minutes=query.stepMinutes,
            obs_code=query.obsCode,
        )
        try:
            track = await IOLoop.current().run_in_executor(None, call)
        except ScoutEphemerisError as e:
            return self.error(str(e), status=502)

        return self.success(
            data={
                "obj_id": obj_id,
                "tdes": tdes,
                "obs_code": query.obsCode,
                "step_minutes": query.stepMinutes,
                "hours": hours,
                "count": len(track),
                "ephemeris": track,
            }
        )
