from skyportal.handlers import BaseHandler
from baselayer.app.access import auth_or_token
import jsonschema

from ...models import FollowupRequest, Instrument, Allocation
from ... import facility_apis, enum_types


class FacilityMessageHandler(BaseHandler):
    @auth_or_token  # ACLs checked in method body below
    def post(self):
        """Docstring rendered as format string below."""
        user = self.current_user
        data = self.get_json()

        if 'followup_request_id' not in data:
            return self.error('Missing required key "followup_request_id".')

        request = FollowupRequest.get_if_accessible_by(
            int(data['followup_request_id']),
            self.current_user,
            raise_if_none=True,
            mode='update',
        )
        instrument = (
            Instrument.query_records_accessible_by(self.current_user)
            .join(Allocation)
            .join(FollowupRequest)
            .filter(FollowupRequest.id == request.id)
            .first()
        )

        if instrument.listener_classname is None:
            return self.error(
                'The instrument associated with this request does not have a Listener API.'
            )

        acl_id = instrument.listener_class.get_acl_id()

        if acl_id not in user.permissions and acl_id is not None:
            return self.error('Insufficient permissions.')

        jsonschema.validate(data, instrument.listener_class.complete_schema())
        instrument.listener_class.process_message(self)
        self.verify_and_commit()

        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"obj_key": request.obj.internal_key},
        )

        return self.success()

    allowed_schemas = [
        iclass.complete_schema()
        for iclass in [
            getattr(facility_apis, classname)
            for classname in enum_types.LISTENER_CLASSNAMES
        ]
    ]
    post.__doc__ = f"""
    ---
    description: Post a message from a remote facility
    tags:
      - facility
    requestBody:
      content:
        application/json:
          schema:
            oneOf: {allowed_schemas}
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
