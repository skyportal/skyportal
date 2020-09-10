class _RequestProcessorBase:

    # subclasses should not modify this
    @classmethod
    def complete_schema(cls):
        return {
            'allOf': [
                {
                    'type': 'object',
                    'properties': {'followup_request_id': {'type': 'integer'}},
                    'required': ['followup_request_id'],
                },
                cls.schema,
            ],
            'title': cls.__name__,
        }


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
