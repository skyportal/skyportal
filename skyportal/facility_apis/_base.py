class _Base:

    # subclasses should not modify this
    @classmethod
    def _isimplemented(cls, method_name):
        from .interface import FollowUpAPI

        func = getattr(cls, method_name)
        unimplemented = getattr(FollowUpAPI, method_name)
        return func is not unimplemented

    # subclasses should not modify this
    @classmethod
    def _methods_implemented(cls):
        return {
            "update": cls.implements_update(),
            "delete": cls.implements_delete(),
            "get": cls.implements_get(),
            "submit": cls.implements_submit(),
        }

    @classmethod
    def implements_update(cls):
        return cls._isimplemented('update')

    @classmethod
    def implements_submit(cls):
        return cls._isimplemented('submit')

    @classmethod
    def implements_get(cls):
        return cls._isimplemented('get')

    @classmethod
    def implements_delete(cls):
        return cls._isimplemented('delete')

    # subclasses should not modify this
    @classmethod
    def frontend_render_info(cls):
        return {
            'methodsImplemented': cls._methods_implemented(),
            'formSchema': cls.form_json_schema,
            'uiSchema': cls.ui_json_schema,
            'aliasLookup': cls.alias_lookup,
        }
