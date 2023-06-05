import arrow
from ..base import BaseHandler
from baselayer.app.access import auth_or_token
from ...models import Instrument, InstrumentLog
from astropy.time import Time


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
            logs_dict = []
            for line in logs.split("\n"):
                lineSplit = line.strip().split(" ")
                if len(lineSplit) < 4:
                    continue
                if ":" in lineSplit[1]:
                    lineSplit[1] = lineSplit[1][:-1]
                try:
                    tt = Time("T".join(lineSplit[:2]), format='isot')
                except Exception:
                    continue
                log_type = lineSplit[2][1:-2]
                message = " ".join(lineSplit[3:])

                logs_dict.append({'mjd': tt.mjd, 'type': log_type, 'message': message})
            logs = {'logs': logs_dict}
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
