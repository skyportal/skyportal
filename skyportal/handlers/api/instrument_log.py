import json
from datetime import datetime

import arrow
import astropy.units as u
from astropy.time import Time, TimeDelta

from baselayer.app.access import auth_or_token, permissions

from ...models import Allocation, Instrument, InstrumentLog
from ...utils.instrument_log import read_logs
from ..base import BaseHandler


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

        if isinstance(logs, str):
            logs = read_logs(logs)
        elif not isinstance(logs, dict):
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


class InstrumentStatusHandler(BaseHandler):
    @permissions(['Upload data'])
    def put(self, instrument_id):
        """
        ---
        description: Update the status of an instrument
        tags:
          - instruments
        parameters:
          - in: path
            name: instrument_id
            required: true
            schema:
              type: integer
            description: The instrument ID to update the status for
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    description: |
                      The status of the instrument
                required:
                  - status
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
        status = data.get('status', None)
        if status in [None, '', {}, []]:
            with self.Session() as session:
                stmt = Instrument.select(session.user_or_token, mode="update").where(
                    Instrument.id == int(instrument_id)
                )
                instrument = session.scalars(stmt).first()
                if instrument is None:
                    return self.error(f'Missing instrument with ID {instrument_id}')

                if instrument.api_classname is None:
                    return self.error('Instrument has no remote observation plan API.')

                if not instrument.api_class.implements()['update_status']:
                    return self.error(
                        'Updating status of this Instrument is not available.'
                    )

                allocations = session.scalars(
                    Allocation.select(session.user_or_token).where(
                        Allocation.instrument_id == instrument_id
                    )
                ).all()
                if len(allocations) == 0:
                    return self.error(
                        f"Cannot find any allocations for instrument with ID: {instrument_id}"
                    )
                allocation = None
                for alloc in allocations:
                    if alloc.altdata is not None:
                        if set(list(alloc.altdata.keys())).issuperset(
                            ["ssh_host", "ssh_username", "ssh_password"]
                        ):
                            allocation = alloc
                            break
                if allocation is None:
                    return self.error(
                        f"Cannot find any allocations with valid altdata (ssh_host, ssh_username, ssh_password) for instrument with ID: {instrument_id}"
                    )

                try:
                    instrument.api_class.update_status(
                        allocation,
                        session,
                    )
                    self.push_all(
                        action='skyportal/REFRESH_INSTRUMENT',
                        payload={'instrument_id': instrument_id},
                    )
                    return self.success()
                except Exception as e:
                    return self.error(f"Error in querying instrument API: {e}")
        else:
            if isinstance(status, str):
                try:
                    status = json.loads(status)
                except Exception:
                    return self.error('Invalid status (must be non-empty JSON)')
            if not isinstance(status, dict):
                return self.error('Invalid status (must be non-empty JSON)')

            status = {
                k: v
                for k, v in status.items()
                if v is not None and v not in [None, '', {}, []]
            }
            if len(status) == 0:
                return self.error('Invalid status (must be non-empty JSON)')

            with self.Session() as session:
                try:
                    instrument = session.scalars(
                        Instrument.select(session.user_or_token).where(
                            Instrument.id == int(instrument_id)
                        )
                    ).first()
                    if instrument is None:
                        return self.error(f'Missing instrument with ID {instrument_id}')

                    if instrument.api_classname is None:
                        return self.error(
                            'Instrument has no remote observation plan API.'
                        )

                    if not instrument.api_class.implements()['update_status']:
                        return self.error(
                            'Updating status of this Instrument is not available.'
                        )

                    instrument.status = status
                    instrument.last_status_update = datetime.utcnow()
                    session.commit()

                    self.push_all(
                        action='skyportal/REFRESH_INSTRUMENT',
                        payload={'instrument_id': instrument_id},
                    )
                    return self.success()
                except Exception as e:
                    return self.error(f"Error updating instrument status: {e}")
