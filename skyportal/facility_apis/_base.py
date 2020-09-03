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
