from skyportal.handlers import BaseHandler
from baselayer.app.access import auth_or_token
import jsonschema

from ...utils import http
from ...models import FollowupRequest, DBSession, FacilityTransaction
from ... import facility_apis, enum_types


class FacilityMessageHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """Docstring rendered as format string below."""
        user = self.current_user
        data = self.get_json()

        if 'followup_request_id' not in data:
            return self.error('Missing required key "followup_request_id".')

        request = FollowupRequest.query.get(int(data['followup_request_id']))

        if request is None:
            return self.error('Invalid request ID.')

        instrument = request.allocation.instrument

        if instrument.listener_classname is None:
            return self.error(
                'The instrument associated with this request does not have a Listener API.'
            )

        acl_id = instrument.listener_class.get_acl_id()
        user_acls = [a.id for a in user.acls]

        if acl_id not in user_acls and acl_id is not None:
            return self.error('Insufficient permissions.')

        jsonschema.validate(data, instrument.listener_class.openapi_spec())
        instrument.listener_class.process_message(self)

        transaction_record = FacilityTransaction(
            request=http.serialize_tornado_request(self),
            followup_request=request,
            initiator=self.associated_user_object,
        )

        DBSession().add(transaction_record)
        DBSession().add(request)
        DBSession().commit()

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
