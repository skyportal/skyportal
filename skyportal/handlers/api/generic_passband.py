from marshmallow.exceptions import ValidationError
from baselayer.app.access import auth_or_token, permissions
from ..base import BaseHandler
from ...models import DBSession, GenericPassband

from ...enum_types import ALLOWED_BANDPASSES, add_passband


class GenericPassbandHandler(BaseHandler):
    @auth_or_token
    def post(self):
        data = self.get_json()
        schema = GenericPassband.__schema__()
        try:
            generic_passband = schema.load(data)
        except ValidationError as exc:
            return self.error(
                'Invalid/missing parameters: ' f'{exc.normalized_messages()}'
            )
        # check if the passband already exists in sncosmo's list of passbands
        if data.get('name') in ALLOWED_BANDPASSES:
            return self.error('Passband already exists')

        # check if the passband already exists in the database
        existing_passband = (
            GenericPassband.query_records_accessible_by(self.current_user)
            .filter(GenericPassband.name == data.get('name'))
            .first()
        )

        if existing_passband is None:
            DBSession().add(generic_passband)
            DBSession().commit()
            add_passband(
                data.get('name'), data.get('min_wavelength'), data.get('max_wavelength')
            )
        else:
            generic_passband = existing_passband

        return self.success(data={"id": generic_passband.id})

    @auth_or_token
    def get(self, generic_passband_id=None):
        if generic_passband_id is not None:
            generic_passband = GenericPassband.get_if_accessible_by(
                int(generic_passband_id),
                self.current_user,
                raise_if_none=True,
                mode="read",
            )
            return self.success(data=generic_passband)
        generic_passbands = DBSession().query(GenericPassband).all()
        return self.success(data=generic_passbands)

    @permissions(['System admin'])
    def delete(self, generic_passband_id):
        instrument = GenericPassband.get_if_accessible_by(
            int(generic_passband_id),
            self.current_user,
            raise_if_none=True,
            mode='update',
        )
        DBSession().delete(instrument)
        self.verify_and_commit()

        return self.success()
