class _Base:
    # The operations a broker provider may implement. A concrete provider
    # overrides only the ones it supports; the rest stay as the base stub and
    # are reported as unimplemented so handlers/frontend can gate on them.
    _methods = (
        "query_alerts",
        "get_alert",
        "get_cutouts",
        "cone_search",
        "get_filters",
        "create_filter",
        "update_filter",
        "delete_filter",
        "test_filter",
        "filter_modules",
        "run_ingestion",
        "validate_config",
    )

    # subclasses should not modify this
    @classmethod
    def _isimplemented(cls, method_name):
        from .interface import BrokerAPI

        # a method is "implemented" only if the subclass overrode the
        # BrokerAPI stub (compare method identity, as facility_apis does).
        func = getattr(cls, method_name)
        default_implementation = getattr(BrokerAPI, method_name)
        return func is not default_implementation

    # subclasses should not modify this
    @classmethod
    def implements(cls):
        caps = {name: cls._isimplemented(name) for name in cls._methods}
        # save_as_source and get_photometry are base defaults (interface.py) for
        # any provider that can fetch an object, so gate both on get_alert.
        caps["save_as_source"] = cls._isimplemented("get_alert")
        caps["get_photometry"] = cls._isimplemented("get_alert")
        return caps

    @classmethod
    def configured_surveys(cls, altdata):
        """Surveys a *configured* broker record serves, for per-record routing.

        Defaults to every survey the provider supports (``cls.surveys``): most
        providers serve all their surveys from one connection (e.g. BOOM picks
        the survey per query). A provider whose instance is survey-specific — one
        deployment/endpoint/token per survey, like Lasair — overrides this to
        narrow it to the deployment's survey.
        """
        return list(cls.surveys)

    # subclasses should not modify this
    @classmethod
    def frontend_render_api_info(cls):
        return {
            "methodsImplemented": cls.implements(),
            "formSchemaConfig": cls.form_json_schema_config,
            "uiSchema": cls.ui_json_schema,
            "aliasLookup": cls.alias_lookup,
            "surveys": list(cls.surveys),
            "filterKind": cls.filter_kind,
        }
