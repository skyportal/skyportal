import sqlalchemy as sa
from astropy.time import Time
from sqlalchemy.orm import selectinload

from baselayer.app.access import permissions

from ...models import (
    Allocation,
    GcnEvent,
    InstrumentField,
    InstrumentFieldTile,
    Localization,
    LocalizationTile,
)
from ..base import BaseHandler


class SkymapTriggerAPIHandler(BaseHandler):
    @permissions(["Upload data"])
    async def post(self):
        """
        ---
        summary: Post a skymap-based trigger
        description: Post a skymap-based trigger
        tags:
          - localizations
          - observations
        requestBody:
          content:
            application/json:
              schema: SkymapQueueAPIHandlerPost
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

        data = self.get_json()
        integrated_probability = data.get("integrated_probability", 0.95)
        try:
            integrated_probability = float(integrated_probability)
        except (TypeError, ValueError):
            return self.error(
                f"Invalid integrated_probability: {integrated_probability}"
            )

        async with self.AsyncSession() as session:
            allocation = await session.scalar(
                Allocation.select(session.user_or_token)
                .where(Allocation.id == data["allocation_id"])
                .options(selectinload(Allocation.instrument))
            )
            if allocation is None:
                return self.error(
                    f"Cannot find Allocation with ID: {data['allocation_id']}"
                )
            instrument = allocation.instrument

            if instrument.api_classname_obsplan is None:
                return self.error("Instrument has no remote observation plan API.")

            if not instrument.api_class_obsplan.implements()["send_skymap"]:
                return self.error(
                    "Submitting skymap requests to this Instrument is not available."
                )

            localization = await session.scalar(
                Localization.select(session.user_or_token).where(
                    Localization.id == data["localization_id"],
                )
            )
            if localization is None:
                return self.error("Localization not found", status=404)

            gcn_event = await session.scalar(
                GcnEvent.select(session.user_or_token).where(
                    GcnEvent.dateobs == localization.dateobs,
                )
            )
            if gcn_event is None:
                return self.error("GcnEvent not found", status=404)

            gracedb_id = None
            aliases = gcn_event.aliases
            for alias in aliases:
                if "LVC" in alias:
                    gracedb_id = alias.split("#")[-1]
                    break

            partition_key = localization.dateobs
            localizationtile_partition_name = (
                f"{partition_key.year}_{partition_key.month:02d}"
            )
            localizationtilescls = LocalizationTile.partitions.get(
                localizationtile_partition_name, None
            )
            if localizationtilescls is None:
                localizationtilescls = LocalizationTile.partitions.get(
                    "def", LocalizationTile
                )
            else:
                partition_check = await session.scalar(
                    sa.select(localizationtilescls.localization_id).where(
                        localizationtilescls.localization_id == localization.id
                    )
                )
                if partition_check is None:
                    localizationtilescls = LocalizationTile.partitions.get(
                        "def", LocalizationTile
                    )

            cum_prob = (
                sa.func.sum(
                    localizationtilescls.probdensity * localizationtilescls.healpix.area
                )
                .over(order_by=localizationtilescls.probdensity.desc())
                .label("cum_prob")
            )
            localizationtile_subquery = (
                sa.select(localizationtilescls.probdensity, cum_prob).filter(
                    localizationtilescls.localization_id == localization.id
                )
            ).subquery()

            min_probdensity = (
                sa.select(
                    sa.func.min(localizationtile_subquery.columns.probdensity)
                ).filter(
                    localizationtile_subquery.columns.cum_prob <= integrated_probability
                )
            ).scalar_subquery()

            area = (InstrumentFieldTile.healpix * localizationtilescls.healpix).area
            prob = sa.func.sum(localizationtilescls.probdensity * area)

            field_tiles_query = (
                sa.select(InstrumentField.field_id, prob)
                .where(
                    localizationtilescls.localization_id == localization.id,
                    localizationtilescls.probdensity >= min_probdensity,
                    InstrumentFieldTile.instrument_id == instrument.id,
                    InstrumentFieldTile.instrument_field_id == InstrumentField.id,
                    InstrumentFieldTile.healpix.overlaps(localizationtilescls.healpix),
                )
                .group_by(InstrumentField.field_id)
            )

            field_tiles_result = await session.execute(field_tiles_query)
            rows = field_tiles_result.all()
            if not rows:
                field_ids, probs = (), ()
            else:
                field_ids, probs = zip(*rows)

            payload = {
                "trigger_name": gracedb_id
                if gracedb_id is not None
                else Time(localization.dateobs).isot,
                "trigger_time": Time.now().mjd,
                "fields": [
                    {"field_id": field_id, "probability": prob}
                    for field_id, prob in zip(field_ids, probs)
                ],
                "user": self.associated_user_object.username,
            }

            try:
                instrument.api_class_obsplan.send_skymap(
                    allocation,
                    payload,
                )
                return self.success()
            except Exception as e:
                return self.error(f"Error in querying instrument API: {e}")

    @permissions(["Upload data"])
    async def get(self, allocation_id):
        """
        ---
        summary: Retrieve skymap-based trigger from external API
        description: Retrieve skymap-based trigger from external API
        tags:
          - localizations
          - observations
        parameters:
          - in: path
            name: allocation_id
            required: true
            schema:
              type: string
            description: |
              ID for the allocation to retrieve
        responses:
          200:
            content:
              application/json:
                schema: ArrayOfPlannedObservations
          400:
            content:
              application/json:
                schema: Error
        """
        try:
            allocation_id_int = int(allocation_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid allocation_id: {allocation_id}")

        data = {}
        data["requester_id"] = self.associated_user_object.id
        data["last_modified_by_id"] = self.associated_user_object.id
        data["allocation_id"] = allocation_id_int

        async with self.AsyncSession() as session:
            allocation = await session.scalar(
                Allocation.select(session.user_or_token)
                .where(Allocation.id == data["allocation_id"])
                .options(selectinload(Allocation.instrument))
            )
            if allocation is None:
                return self.error(
                    f"Cannot find Allocation with ID: {data['allocation_id']}"
                )

            instrument = allocation.instrument

            if instrument.api_classname_obsplan is None:
                return self.error("Instrument has no remote observation plan API.")

            if not instrument.api_class_obsplan.implements()["queued_skymap"]:
                return self.error(
                    "Retrieving skymap queue requests from this Instrument is not available."
                )

            try:
                trigger_names = instrument.api_class_obsplan.queued_skymap(allocation)
                return self.success(data={"trigger_names": trigger_names})
            except Exception as e:
                return self.error(f"Error in querying instrument API: {e}")

    @permissions(["Upload data"])
    async def delete(self, allocation_id):
        """
        ---
        summary: Delete skymap-based trigger from external API
        description: Delete skymap-based trigger from external API
        tags:
          - observations
        parameters:
          - in: path
            name: allocation_id
            required: true
            schema:
              type: string
            description: |
              ID for the allocation to delete queue
          - in: query
            name: queueName
            required: true
            schema:
              type: string
            description: Queue name to remove
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
        try:
            allocation_id_int = int(allocation_id)
        except (TypeError, ValueError):
            return self.error(f"Invalid allocation_id: {allocation_id}")

        data = self.get_json()

        if "trigger_name" not in data:
            return self.error("Missing trigger_name parameter.")
        trigger_name = data["trigger_name"]

        data["requester_id"] = self.associated_user_object.id
        data["last_modified_by_id"] = self.associated_user_object.id
        data["allocation_id"] = allocation_id_int

        async with self.AsyncSession() as session:
            allocation = await session.scalar(
                Allocation.select(session.user_or_token)
                .where(Allocation.id == data["allocation_id"])
                .options(selectinload(Allocation.instrument))
            )
            if allocation is None:
                return self.error(
                    f"Cannot find Allocation with ID: {data['allocation_id']}"
                )

            instrument = allocation.instrument

            if instrument.api_classname_obsplan is None:
                return self.error("Instrument has no remote observation plan API.")

            if not instrument.api_class_obsplan.implements()["remove_skymap"]:
                return self.error(
                    "Cannot delete skymap-based triggers from this Instrument."
                )

            try:
                instrument.api_class_obsplan.remove_skymap(
                    allocation,
                    trigger_name=trigger_name,
                    username=self.associated_user_object.username,
                )
                return self.success(f"Removed skymap-based trigger {trigger_name}.")
            except Exception as e:
                return self.error(f"Error in querying instrument API: {e}")
