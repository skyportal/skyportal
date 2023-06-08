import arrow
from astropy.time import Time, TimeDelta
import astropy.units as u

from baselayer.app.access import permissions, auth_or_token

from ..base import BaseHandler
from ...models import Allocation, Instrument, InstrumentLog
from ...utils.instrument_log import read_logs


class InstrumentLogHandler(BaseHandler):
    @auth_or_token
    def post(self, instrument_id):
        """
        ---
        description: Add log messages from an instrument
        tags:
          - instruments
          - instrumentlogs
        parameters:
          - in: path
            name: instrument_id
            required: true
            schema:
              type: integer
            description: The instrument ID to post logs for
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  start_date:
                    type: string
                    description: |
                      Arrow-parseable date string (e.g. 2020-01-01).
                  end_date:
                    type: string
                    description: |
                      Arrow-parseable date string (e.g. 2020-01-01).
                  logs:
                    type: object
                    description: |
                       Nested JSON containing the log messages.
                required:
                  - start_date
                  - end_date
                  - logs
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
                            id:
                              type: int
                              description: The id of the InstrumentLog
          400:
            content:
              application/json:
                schema: Error
        """

        data = self.get_json()
        start_date = data.get('start_date')
        if start_date is None:
            return self.error('date is required')
        try:
            start_date = arrow.get(start_date).datetime
        except Exception as e:
            return self.error(f'Invalid start_date: {str(e)}')

        end_date = data.get('end_date')
        if end_date is None:
            return self.error('date is required')
        try:
            end_date = arrow.get(end_date).datetime
        except Exception as e:
            return self.error(f'Invalid end_date: {str(e)}')

        logs = data.get('log')
        if logs is None:
            return self.error('log is required')

        if type(logs) == str:
            logs = read_logs(logs)
        elif not type(logs) == dict:
            return self.error('log must be either dictionary or parsable string')

        with self.Session() as session:
            stmt = Instrument.select(session.user_or_token, mode="update").where(
                Instrument.id == int(instrument_id)
            )
            instrument = session.scalars(stmt).first()
            if instrument is None:
                return self.error(f'Missing instrument with ID {instrument_id}')

            instrument_log = InstrumentLog(
                log=logs,
                start_date=start_date,
                end_date=end_date,
                instrument_id=instrument_id,
            )

            session.add(instrument_log)
            session.commit()

            return self.success(data={'id': instrument_log.id})


class InstrumentLogExternalAPIHandler(BaseHandler):
    @permissions(['Upload data'])
    def get(self, allocation_id):
        """
        ---
        description: Retrieve queued observations from external API
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
          - in: query
            name: startDate
            required: true
            schema:
              type: string
            description: |
              Arrow-parseable date string (e.g. 2020-01-01).
              Defaults to now.
          - in: query
            name: endDate
            required: true
            schema:
              type: string
            description: |
              Arrow-parseable date string (e.g. 2020-01-01).
              Defaults to 72 hours ago.
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

        data = {}
        data["requester_id"] = self.associated_user_object.id
        data["last_modified_by_id"] = self.associated_user_object.id
        data['allocation_id'] = int(allocation_id)

        start_date = self.get_query_argument('startDate')
        end_date = self.get_query_argument('endDate')

        if start_date is not None:
            start_date = arrow.get(start_date.strip()).datetime
        else:
            start_date = (Time.now() - TimeDelta(3 * u.day)).datetime
        if end_date is not None:
            end_date = arrow.get(end_date.strip()).datetime
        else:
            end_date = Time.now().datetime

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

            if instrument.api_classname is None:
                return self.error('Instrument has no remote observation plan API.')

            if not instrument.api_class.implements()['retrieve_log']:
                return self.error(
                    'Submitting executed observation plan requests to this Instrument is not available.'
                )

            try:
                # we now retrieve and commit to the database the
                # instrument logs
                instrument.api_class.retrieve_log(
                    allocation,
                    start_date,
                    end_date,
                )
                return self.success()
            except Exception as e:
                return self.error(f"Error in querying instrument API: {e}")
