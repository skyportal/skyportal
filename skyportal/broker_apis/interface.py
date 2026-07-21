from ._base import _Base


class BrokerAPI(_Base):
    """An interface that broker providers must implement.

    A "broker" is an external source of alerts (e.g. BOOM, Kowalski, Fink,
    Lasair). A provider is a registered class that knows how to talk to one
    broker; a configured instance lives in the ``Broker`` model, which supplies
    per-instance credentials/endpoints via its encrypted ``altdata``.

    Providers override only the operations they support. Every stub below
    raises ``NotImplementedError``; ``implements()`` (in ``_base``) reports which
    were overridden so handlers and the frontend can gate features. Each method
    is a ``staticmethod`` taking the configured ``broker`` (a ``Broker`` model
    instance) plus a DB ``session`` and operation-specific keyword arguments.
    """

    # ------------------------------------------------------------------ #
    # Interactive operations (skyportal -> broker)                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def query_alerts(broker, session, **kwargs):
        """Search/list alerts (by object id, candid, or cone search).

        Parameters
        ----------
        broker: skyportal.models.Broker
            The configured broker instance (credentials in ``broker.altdata``).
        session: sqlalchemy.orm.Session
            A database session.
        kwargs: dict
            Query parameters (e.g. ``objectId``, ``candid``, ``ra``, ``dec``,
            ``radius``).

        Returns
        -------
        list
            A list of alert records (provider-specific dicts).
        """
        raise NotImplementedError

    @staticmethod
    def get_alert(broker, alert_id, session, **kwargs):
        """Return a single alert (with auxiliary/history data if available)."""
        raise NotImplementedError

    @staticmethod
    def get_cutouts(broker, alert_id, session, **kwargs):
        """Return the science/template/difference cutouts for an alert."""
        raise NotImplementedError

    @staticmethod
    def cone_search(broker, ra, dec, radius, session, **kwargs):
        """Cross-match a position against the broker's archival catalogs."""
        raise NotImplementedError

    @classmethod
    async def save_as_source(cls, broker, alert_id, session, user, group_ids, **kwargs):
        """Ingest an object (``alert_id`` = objectId) as an Obj/Source + photometry.

        Default implementation, free to any provider that implements
        ``get_alert``: fetch the object (and cutouts via ``get_cutouts`` if
        available), then hand off to the shared, survey-keyed writer
        (``_save.save_object_as_source``). Override only for a non-standard
        alert shape.
        """
        from ._save import save_object_as_source

        data = cls.get_alert(broker, alert_id, session, **kwargs)
        survey = (
            kwargs.get("survey")
            or (data.get("survey") if isinstance(data, dict) else None)
            or (broker.altdata or {}).get("survey")
        )
        cutouts = None
        candid = None
        if isinstance(data, dict):
            candid = data.get("candid") or (data.get("candidate") or {}).get("candid")
        if candid is not None and cls.implements().get("get_cutouts"):
            try:
                cutouts = cls.get_cutouts(broker, candid, session, **kwargs)
            except Exception:
                cutouts = None
        return await save_object_as_source(
            data, survey, session, user, group_ids, cutouts=cutouts
        )

    @classmethod
    async def get_photometry(cls, broker, alert_id, session, user, **kwargs):
        """Display-only photometry for an object (``alert_id`` = objectId): the
        persisted, access-controlled DB photometry merged with photometry fetched
        on demand from the broker, cached per access scope and never written to
        Postgres (the broker-canonical / marshal-as-cache pattern).

        Default implementation, free to any provider that implements
        ``get_alert``: fetch the object and hand off to the shared, survey-keyed
        transform + cache (``_photometry.display_photometry``). Override only for
        a non-standard alert shape.
        """
        from ._photometry import display_photometry

        return await display_photometry(cls, broker, alert_id, session, user, **kwargs)

    @staticmethod
    def get_filters(broker, session, **kwargs):
        """Retrieve broker-side filter(s) and their status."""
        raise NotImplementedError

    @staticmethod
    def create_filter(broker, session, **kwargs):
        """Create a filter (version) on the broker."""
        raise NotImplementedError

    @staticmethod
    def update_filter(broker, session, **kwargs):
        """Update a filter's state on the broker (active/version/flags)."""
        raise NotImplementedError

    @staticmethod
    def validate_filter(broker, session, **kwargs):
        """Validate a filter version for activation without changing state."""
        raise NotImplementedError

    @staticmethod
    def delete_filter(broker, session, **kwargs):
        """Delete a filter on the broker."""
        raise NotImplementedError

    @staticmethod
    def test_filter(broker, session, **kwargs):
        """Run/preview a filter (count or paginated results)."""
        raise NotImplementedError

    @staticmethod
    def filter_modules(broker, session, **kwargs):
        """Return the pipeline stages/modules the broker's filters support."""
        raise NotImplementedError

    # ------------------------------------------------------------------ #
    # Ingestion (broker -> skyportal). Implemented in a later stage on    #
    # top of the shared ETL helpers; declared here to keep the contract   #
    # unified.                                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def run_ingestion(broker, session, **kwargs):
        """Run the long-lived ingestion loop for this broker (consumer/poller)."""
        raise NotImplementedError

    # ------------------------------------------------------------------ #
    # Configuration / UI                                                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def validate_config(altdata):
        """Validate a broker instance's ``altdata`` (credentials/endpoints)."""
        raise NotImplementedError

    # jsonschema for the "configure this broker" frontend form (react-jsonschema-form).
    # Contains the fields stored (encrypted) in ``Broker.altdata``.
    form_json_schema_config = None

    # ui-schema overrides for the config form.
    ui_json_schema = None

    # mapping of jsonschema property names to display labels on the frontend.
    alias_lookup = {}

    # surveys this broker serves (e.g. ["ZTF", "LSST"]); advertised to the frontend.
    surveys = []

    # how this broker models filters, so the frontend can pick an editor:
    #   "pipeline" (BOOM: server-side aggregation stages, versioned)
    #   "query"    (Lasair: a SQL-style query)
    #   "tags"     (Fink: select from a fixed menu of topics/classifications)
    #   "none"     (no custom filtering)
    filter_kind = "none"

    # whether cone_search returns reference/cross-match catalogs (Gaia/PS1/AllWISE,
    # ...) keyed by catalog name — i.e. usable for the source-page centroid
    # cross-match overlay. Providers whose cone_search returns their own alert
    # objects (Lasair, Fink) leave this False so the overlay doesn't query them.
    cross_match_catalogs = False
