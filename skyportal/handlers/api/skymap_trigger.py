from astropy.time import Time
import sqlalchemy as sa

from baselayer.app.access import permissions

from ..base import BaseHandler
from ...models import (
    Allocation,
    InstrumentField,
    InstrumentFieldTile,
    Localization,
    LocalizationTile,
)


class SkymapTriggerAPIHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Post a skymap-based trigger
        tags:
          - localizations
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

        with self.Session() as session:

            allocation = session.scalars(
                Allocation.select(session.user_or_token).where(
                    Allocation.id == data['allocation_id']
                )
            ).first()
            if allocation is None:
                return self.error(
                    f"Cannot find Allocation with ID: {data['allocation_id']}"
                )
            instrument = allocation.instrument

            stmt = Localization.select(session.user_or_token).where(
                Localization.id == data['localization_id'],
            )
            localization = session.scalars(stmt).first()
            if localization is None:
                return self.error("Localization not found", status=404)

            cum_prob = (
                sa.func.sum(
                    LocalizationTile.probdensity * LocalizationTile.healpix.area
                )
                .over(order_by=LocalizationTile.probdensity.desc())
                .label('cum_prob')
            )
            localizationtile_subquery = (
                sa.select(LocalizationTile.probdensity, cum_prob).filter(
                    LocalizationTile.localization_id == localization.id
                )
            ).subquery()

            min_probdensity = (
                sa.select(
                    sa.func.min(localizationtile_subquery.columns.probdensity)
                ).filter(
                    localizationtile_subquery.columns.cum_prob <= integrated_probability
                )
            ).scalar_subquery()

            area = (InstrumentFieldTile.healpix * LocalizationTile.healpix).area
            prob = sa.func.sum(LocalizationTile.probdensity * area)

            field_tiles_query = (
                sa.select(InstrumentField.field_id, prob)
                .where(
                    LocalizationTile.localization_id == localization.id,
                    LocalizationTile.probdensity >= min_probdensity,
                    InstrumentFieldTile.instrument_id == instrument.id,
                    InstrumentFieldTile.instrument_field_id == InstrumentField.id,
                    InstrumentFieldTile.healpix.overlaps(LocalizationTile.healpix),
                )
                .group_by(InstrumentField.field_id)
            )

            field_ids, probs = zip(*session.execute(field_tiles_query).all())

            payload = {
                "trigger_name": Time(localization.dateobs).isot,
                "trigger_time": Time.now().mjd,
                "fields": [
                    {'field_id': field_id, 'probability': prob}
                    for field_id, prob in zip(field_ids, probs)
                ],
                "user": self.associated_user_object.username,
            }

            if instrument.api_classname_obsplan is None:
                return self.error('Instrument has no remote observation plan API.')

            if not instrument.api_class_obsplan.implements()['send_skymap']:
                return self.error(
                    'Submitting skymap requests to this Instrument is not available.'
                )

            try:
                instrument.api_class_obsplan.send_skymap(
                    allocation,
                    payload,
                )
                return self.success()
            except Exception as e:
                return self.error(f"Error in querying instrument API: {e}")

    @permissions(['Upload data'])
    def get(self, allocation_id):
        """
        ---
        description: Retrieve skymap-based trigger from external API
        tags:
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
        data = {}
        data["requester_id"] = self.associated_user_object.id
        data["last_modified_by_id"] = self.associated_user_object.id
        data['allocation_id'] = int(allocation_id)

        with self.Session() as session:
            allocation = session.scalars(
                Allocation.select(session.user_or_token).where(
                    Allocation.id == data['allocation_id']
                )
            ).first()
            if allocation is None:
                return self.error(
                    f"Cannot find Allocation with ID: {data['allocation_id']}"
                )

            instrument = allocation.instrument

            if instrument.api_classname_obsplan is None:
                return self.error('Instrument has no remote observation plan API.')

            if not instrument.api_class_obsplan.implements()['queued_skymap']:
                return self.error(
                    'Retrieving skymap queue requests from this Instrument is not available.'
                )

            try:
                # we now retrieve and commit to the database the
                # executed observations
                trigger_names = instrument.api_class_obsplan.queued_skymap(allocation)
                return self.success(data={'trigger_names': trigger_names})
            except Exception as e:
                return self.error(f"Error in querying instrument API: {e}")

    @permissions(['Upload data'])
    def delete(self, allocation_id):
        """
        ---
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
        data = self.get_json()

        if 'trigger_name' not in data:
            return self.error('Missing trigger_name parameter.')
        trigger_name = data['trigger_name']

        data["requester_id"] = self.associated_user_object.id
        data["last_modified_by_id"] = self.associated_user_object.id
        data['allocation_id'] = allocation_id

        with self.Session() as session:
            allocation = session.scalars(
                Allocation.select(session.user_or_token).where(
                    Allocation.id == data['allocation_id']
                )
            ).first()
            if allocation is None:
                return self.error(
                    f"Cannot find Allocation with ID: {data['allocation_id']}"
                )

            instrument = allocation.instrument

            if instrument.api_classname_obsplan is None:
                return self.error('Instrument has no remote observation plan API.')

            if not instrument.api_class_obsplan.implements()['remove_skymap']:
                return self.error(
                    'Cannot delete skymap-based triggers from this Instrument.'
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
