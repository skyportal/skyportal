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
            "remove_queue": cls._isimplemented('remove_queue'),
            "prepare_payload": cls._isimplemented('prepare_payload'),
            "send_skymap": cls._isimplemented('send_skymap'),
            "queued_skymap": cls._isimplemented('queued_skymap'),
            "remove_skymap": cls._isimplemented('remove_skymap'),
            "retrieve_log": cls._isimplemented('retrieve_log'),
            "update_status": cls._isimplemented('update_status'),
        }

    # subclasses should not modify this
    @classmethod
    def frontend_render_info(cls, instrument, user, **kwargs):
        try:
            formSchema = cls.custom_json_schema(instrument, user, **kwargs)
        except AttributeError:
            formSchema = cls.form_json_schema
        try:
            formSchemaForcedPhotometry = cls.form_json_schema_forced_photometry
        except AttributeError:
            formSchemaForcedPhotometry = None
        try:
            priority_order = cls.priority_order
        except AttributeError:
            priority_order = None
        return {
            'methodsImplemented': cls.implements(),
            'formSchema': formSchema,
            'formSchemaForcedPhotometry': formSchemaForcedPhotometry,
            'uiSchema': cls.ui_json_schema,
            'aliasLookup': cls.alias_lookup,
            'priorityOrder': priority_order,
        }
