from jsonschema_to_openapi.convert import convert
from copy import deepcopy


class _ListenerBase:

    # subclasses should not modify this
    @classmethod
    def complete_schema(cls):
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
        return convert(cls.complete_schema())

    @classmethod
    def get_acl_id(cls):
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
        }

    # subclasses should not modify this
    @classmethod
    def frontend_render_info(cls):
        return {
            'methodsImplemented': cls.implements(),
            'formSchema': cls.form_json_schema,
            'uiSchema': cls.ui_json_schema,
            'aliasLookup': cls.alias_lookup,
        }
