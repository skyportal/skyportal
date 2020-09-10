from baselayer.app.handlers import BaseHandler
from baselayer.app.access import auth_or_token
import yaml
import jsonschema

from ...models import FollowupRequest, DBSession, Instrument


instruments = (
    DBSession()
    .query(Instrument)
    .filter(Instrument.listener_classname.isnot(None))
    .all()
)


class FollowupRequestResponseHandler(BaseHandler):
    @auth_or_token
    def post(self):
        """Docstring rendered as format string below."""
        user = self.current_user
        data = self.get_json()
        request = FollowupRequest.get_if_owned_by(int(data['request_id']), user)

        if request is None:
            return self.error('Invalid request ID.')

        instrument = request.allocation.instrument

        if instrument.listener_classname is None:
            return self.error(
                'The instrument associated with this request does not have a Listener API.'
            )

        acl_id = instrument.listener_acl.id
        user_acls = [a.id for a in user.acls]

        if acl_id not in user_acls:
            return self.error('Insufficient permissions.')

        jsonschema.validate(data, instrument.listener_class.complete_schema())
        transaction_record = instrument.listener_class.process_message(self)

        DBSession().add(transaction_record)
        DBSession().add(request)
        DBSession().commit()

        self.push_all(
            action="skyportal/REFRESH_SOURCE",
            payload={"obj_key": request.obj.internal_key},
        )

    post.__doc__ = f"""
        ---
        description: Post a message from a remote facility
        requestBody:
          content:
            application/json:
              schema:
                oneOf: {yaml.dump([i.listener_class.complete_schema() for i in instruments])}
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
