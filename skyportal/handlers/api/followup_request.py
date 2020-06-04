import arrow
from marshmallow.exceptions import ValidationError

from baselayer.app.access import auth_or_token
from ..base import BaseHandler
from ...models import (DBSession, Instrument, Source, FollowupRequest, Token,
                       ObservingRun)
from ...schema import FollowUpRequestSchema


class FollowupRequestHandler(BaseHandler):


    @auth_or_token
    def post(self):
        """
        ---
        description: Submit follow-up request.
        requestBody:
          content:
            application/json:
              schema:
                oneOf:
                  - $ref: "#/components/schemas/RoboticImagingRequest"
                  - $ref: "#/components/schemas/RoboticSpectroscopyRequest"
                  - $ref: "#/components/schemas/ClassicalImagingRequest"
                  - $ref: "#/components/schemas/ClassicalSpectroscopyRequest"
                discriminator:
                  propertyName: type
                  mapping:
                    robotic_spectroscopy: "#/components/schemas/RoboticSpectroscopyRequest"
                    robotic_imaging: "#/components/schemas/RoboticImagingRequest"
                    classical_spectroscopy: "#/components/schemas/ClassicalSpectroscopyRequest"
                    classical_imaging: "#/components/schemas/ClassicalImagingRequest"

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
                              type: integer
                              description: New follow-up request ID
        """

        data = self.get_json()

        # super basic validation
        try:
            request = FollowUpRequestSchema.load(data=data)
        except ValidationError as e:
            return self.error(f'Error parsing followup request: '
                              f'"{e.normalized_messages()}"')

        followup_request = FollowupRequest()
        followup_request.requester_id = self.current_user.id

        # check the instrument
        instrument_id = request.pop('instrument_id')
        instrument = Instrument.query.get(instrument_id)
        if instrument is None:
            return self.error(f'Invalid instrument id: "{instrument_id}"')
        followup_request.instrument = instrument

        # check the object
        obj_id = request.pop("obj_id")
        source = Source.get_if_owned_by(obj_id, self.current_user)
        if source is None:
            return self.error(f'Invalid obj_id: "{obj_id}"')
        followup_request.obj_id = obj_id

        # check that request type is valid given the instrument
        rtype = request.pop('type')
        rclassical = 'classical' in rtype
        if ('spectroscopy' in rtype and not instrument.does_spectroscopy) or \
                ('imaging' in rtype and not instrument.does_imaging) or \
                (rclassical and instrument.robotic) or \
                (not rclassical and not instrument.robotic):
            return self.error(f'Invalid request type "{rtype}" for instrument '
                              f'"{instrument.name}".')
        followup_request.type = rtype

        # assign an observing run if classical
        if rclassical:
            run_id = request.pop('run_id')
            run = ObservingRun.query.get(run_id)
            if run is None:
                return self.error(f'Invalid observing run: "{run_id}"')
            followup_request.run = run

        # shove whatever's left after the pops into parameters
        followup_request.parameters = request
        followup_request.submit()

        DBSession.add(followup_request)
        DBSession.commit()

        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"obj_id": followup_request.obj_id},
        )
        return self.success(data={"id": followup_request.id})


    @auth_or_token
    def delete(self, request_id):
        """
        ---
        description: Delete follow-up request.
        parameters:
          - in: path
            name: request_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        followup_request = FollowupRequest.query.get(int(request_id))
        if hasattr(self.current_user, "roles"):
            if not (
                "Super admin" in [role.id for role in self.current_user.roles]
                or "Group admin" in [role.id for role in self.current_user.roles]
                or followup_request.requester.username == self.current_user.username
            ):
                return self.error("Insufficient permissions.")
        elif isinstance(self.current_user, Token):
            if self.current_user.created_by_id != followup_request.requester.id:
                return self.error("Insufficient permissions.")
        DBSession.delete(followup_request)
        DBSession.commit()

        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"obj_id": followup_request.obj_id},
        )
        return self.success()
