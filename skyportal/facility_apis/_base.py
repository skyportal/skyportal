from jsonschema_to_openapi.convert import convert
from copy import deepcopy


class _ListenerBase:

    # subclasses should not modify this
    @classmethod
    def complete_schema(cls):
        """Ensures that the all the necessary fields required by the
        frontend, (e.g., followup_request_id) are included in the Listener's
        JSONSchema. If the fields are missing, this function adds them."""
        base = deepcopy(cls.schema)
        if 'type' not in base:
            base['type'] = 'object'
        if 'properties' not in base:
            base['properties'] = {}
        if 'followup_request_id' not in base['properties']:
            base['properties']['followup_request_id'] = {'type': 'integer'}

        if 'required' not in base:
            base['required'] = ['followup_request_id']
        else:
            base['required'].append('followup_request_id')

        base['title'] = cls.__name__
        base['additionalProperties'] = False
        return base

    @classmethod
    def openapi_spec(cls):
        """OpenAPI representation of the user-contributed JSONSchema."""
        return convert(cls.complete_schema())

    @classmethod
    def get_acl_id(cls):
        """Return the ID of the ACL that a User must have in order to use
        this API."""
        return f'Post from {cls.__name__}'


class _Base:

    # subclasses should not modify this
    @classmethod
    def _isimplemented(cls, method_name):
        from .interface import FollowUpAPI

        # check whether the subclass's method is identical in memory to
        # FollowUpAPI's (unimplemented) method stub. if so the method is
        # not implemented

        func = getattr(cls, method_name)
        default_implementation = getattr(FollowUpAPI, method_name)
        return func is not default_implementation

    # subclasses should not modify this
    @classmethod
    def implements(cls):
        return {
            "update": cls._isimplemented('update'),
            "delete": cls._isimplemented('delete'),
            "get": cls._isimplemented('get'),
            "submit": cls._isimplemented('submit'),
            "send": cls._isimplemented('send'),
            "remove": cls._isimplemented('remove'),
            "retrieve": cls._isimplemented('retrieve'),
            "queued": cls._isimplemented('queued'),
        }

    # subclasses should not modify this
    @classmethod
    def frontend_render_info(cls, instrument, user):

        try:
            formSchema = cls.custom_json_schema(instrument, user)
        except AttributeError:
            formSchema = cls.form_json_schema
        return {
            'methodsImplemented': cls.implements(),
            'formSchema': formSchema,
            'uiSchema': cls.ui_json_schema,
            'aliasLookup': cls.alias_lookup,
        }
