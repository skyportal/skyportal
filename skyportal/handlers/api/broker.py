import copy
from typing import Annotated, Any

import sqlalchemy as sa
from pydantic import Field
from skyportal_py_models.brokers import (
    _FILTER_MODULE_ELEMENTS,
    MAX_FILTERS_PER_PAGE,
    BrokerConeSearchGetQuery,
    BrokerFilterAttachBody,
    BrokerFilterCatalogGetQuery,
    BrokerFilterModulesGetQuery,
    BrokerFilterModuleWriteBody,
    BrokerFiltersPatchBody,
    BrokerFiltersPostBody,
    BrokerFilterTestBody,
    BrokerFilterValidateBody,
    BrokerPatchBody,
    BrokerPhotometryGetQuery,
    BrokerPostBody,
    BrokerSaveBody,
    BrokerSurveyPhotometryGetQuery,
)
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.attributes import flag_modified

from baselayer.app.access import auth_or_token, permissions
from baselayer.log import make_log

from ...broker_apis.interface import survey_permissions
from ...enum_types import ALLOWED_BROKER_CLASSNAMES
from ...models import Broker, Filter, GroupUser, Stream, set_autosave
from ..base import BaseHandler

log = make_log("api/broker")

AlertId = Annotated[
    str,
    Field(description="Alert identifier (e.g. candid) the provider keys cutouts on."),
]


def alert_permissions(user, session):
    """The requester's survey -> programids scope for alert queries, derived from
    the streams they can access. ``None`` means unrestricted (system admins).

    Handlers must always pass the result down to the provider: a provider that
    receives no scope denies everything.
    """
    if user.is_system_admin:
        return None
    return survey_permissions(session.scalars(Stream.select(user)).all())


async def alert_permissions_async(user, session):
    """``alert_permissions`` for the async handlers."""
    if user.is_system_admin:
        return None
    return survey_permissions((await session.scalars(Stream.select(user))).all())


def strip_secrets(altdata, paths):
    """Drop the given dotted paths from a copy of ``altdata``."""
    data = copy.deepcopy(altdata or {})
    for path in paths:
        *parents, leaf = path.split(".")
        node = data
        for parent in parents:
            node = node.get(parent) if isinstance(node, dict) else None
        if isinstance(node, dict):
            node.pop(leaf, None)
    return data


def merge_altdata(stored, incoming):
    """Overlay ``incoming`` on ``stored``; blank values keep what is stored.

    A client that never receives credentials
    can still edit the rest of the config without wiping them.
    """
    merged = dict(stored or {})
    for key, value in (incoming or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_altdata(merged[key], value)
        elif value is None or (isinstance(value, str) and not value.strip()):
            continue
        else:
            merged[key] = value
    return merged


DEFAULT_FIELDS = {
    "default_alert_search": "query_alerts",
    "default_crossmatch": "cross_match_catalogs",
}


def set_default(session, broker, field, value):
    """Make ``broker`` the one holding ``field``, clearing it everywhere else.

    Raises ``ValueError`` if the provider cannot serve what the default targets.
    """
    capability = DEFAULT_FIELDS[field]
    if value and not broker.broker_class.implements()[capability]:
        raise ValueError(
            f"{broker.name} does not implement '{capability}' and cannot be the "
            f"'{field}' broker."
        )
    if value:
        session.execute(
            sa.update(Broker)
            .where(Broker.id != broker.id)
            .values(**{field: False})
            .execution_options(synchronize_session="fetch")
        )
    setattr(broker, field, value)


def broker_to_dict(broker, include_altdata=False):
    """Serialize a Broker, redacting encrypted credentials by default."""
    data = {
        "id": broker.id,
        "name": broker.name,
        "broker_classname": broker.broker_classname,
        "active": broker.active,
        "default_alert_search": broker.default_alert_search,
        "default_crossmatch": broker.default_crossmatch,
        "capabilities": broker.broker_class.implements(),
        # Per-record surveys (what THIS connection serves), so survey-based
        # routing is deterministic for one-deployment-per-survey providers.
        "surveys": broker.broker_class.configured_surveys(broker.altdata),
        "filter_kind": broker.broker_class.filter_kind,
    }
    if include_altdata:
        data["altdata"] = strip_secrets(
            broker.altdata, broker.broker_class.secret_config_fields()
        )
    return data


class BrokerHandler(BaseHandler):
    @permissions(["System admin"])
    def post(self, *, body: BrokerPostBody = None):
        """
        ---
        summary: Create a broker
        description: Register a configured connection to an external alert broker.
          A broker whose provider implements ``test_connection`` is always created
          inactive, since activating it is what checks its credentials.
        tags:
          - brokers
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          type: object
                          properties:
                            id:
                              type: integer
          400:
            content:
              application/json:
                schema: Error
        """
        body = self.parse_body(BrokerPostBody)
        name = body.name
        broker_classname = body.broker_classname
        altdata = body.altdata

        if not name:
            return self.error("Missing required parameter: name")
        if broker_classname not in ALLOWED_BROKER_CLASSNAMES:
            return self.error(
                f"Invalid broker_classname. Must be one of: {ALLOWED_BROKER_CLASSNAMES}"
            )

        with self.Session() as session:
            broker = Broker(
                name=name,
                broker_classname=broker_classname,
                active=body.active,
            )
            if broker.broker_class.implements()["test_connection"]:
                broker.active = False
            if broker.broker_class.implements()["validate_config"]:
                try:
                    broker.broker_class.validate_config(altdata)
                except Exception as e:
                    return self.error(f"Invalid broker configuration: {e}")
            broker.altdata = altdata

            session.add(broker)
            session.flush()
            for field in DEFAULT_FIELDS:
                if getattr(body, field):
                    try:
                        set_default(session, broker, field, True)
                    except ValueError as e:
                        return self.error(str(e))
            session.commit()
            return self.success(data={"id": broker.id})

    @auth_or_token
    def get(self, broker_id: int | None = None):
        """
        ---
        summary: Retrieve broker(s)
        description: Get one broker (by id) or all brokers. Credentials are
          only included for system admins.
        tags:
          - brokers
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
        include_altdata = self.current_user.is_system_admin

        with self.Session() as session:
            if broker_id is not None:
                broker = session.scalars(
                    Broker.select(self.current_user).where(Broker.id == int(broker_id))
                ).first()
                if broker is None:
                    return self.error(f"No broker with id {broker_id}")
                return self.success(data=broker_to_dict(broker, include_altdata))

            brokers = session.scalars(Broker.select(self.current_user)).all()
            return self.success(
                data=[broker_to_dict(b, include_altdata) for b in brokers]
            )

    @permissions(["System admin"])
    def patch(self, broker_id: int, *, body: BrokerPatchBody = None):
        """
        ---
        summary: Update a broker
        description: Activating a broker whose provider implements
          ``test_connection``, or editing an active one's credentials, first
          reaches the broker, and fails if the credentials are refused.
        tags:
          - brokers
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
        body = self.parse_body(BrokerPatchBody)
        with self.Session() as session:
            broker = session.scalars(
                Broker.select(self.current_user, mode="update").where(
                    Broker.id == int(broker_id)
                )
            ).first()
            if broker is None:
                return self.error(f"No broker with id {broker_id}")

            checks_credentials = broker.broker_class.implements()["test_connection"]
            was_active = broker.active
            fields_set = body.model_fields_set
            if "name" in fields_set:
                broker.name = body.name
            if "altdata" in fields_set:
                altdata = merge_altdata(broker.altdata, body.altdata)
                if broker.broker_class.implements()["validate_config"]:
                    try:
                        broker.broker_class.validate_config(altdata)
                    except Exception as e:
                        return self.error(f"Invalid broker configuration: {e}")
                broker.altdata = altdata
            if "active" in fields_set:
                broker.active = body.active
            if (
                checks_credentials
                and broker.active
                and ("altdata" in fields_set or not was_active)
            ):
                try:
                    broker.broker_class.test_connection(broker)
                except Exception as e:
                    action = "stay active" if was_active else "be activated"
                    return self.error(
                        f"Wrong {broker.name} credentials, it cannot {action}: {e}"
                    )
            for field in DEFAULT_FIELDS:
                if field in fields_set:
                    try:
                        set_default(session, broker, field, bool(getattr(body, field)))
                    except ValueError as e:
                        return self.error(str(e))

            session.commit()
            return self.success()

    @permissions(["System admin"])
    def delete(self, broker_id: int):
        """
        ---
        summary: Delete a broker
        tags:
          - brokers
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
        with self.Session() as session:
            broker = session.scalars(
                Broker.select(self.current_user, mode="delete").where(
                    Broker.id == int(broker_id)
                )
            ).first()
            if broker is None:
                return self.error(f"No broker with id {broker_id}")
            session.delete(broker)
            session.commit()
            return self.success()


class BrokerAlertsHandler(BaseHandler):
    @auth_or_token
    def get(self, broker_id: int, alert_id=None):
        """
        ---
        summary: Query broker alerts
        description: Search alerts (or fetch one by id) from a broker, dispatched
          to the broker's registered provider.
        tags:
          - brokers
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
        params: dict[str, Any] = {
            k: self.get_argument(k) for k in self.request.arguments
        }

        with self.Session() as session:
            broker = session.scalars(
                Broker.select(self.current_user).where(Broker.id == int(broker_id))
            ).first()
            if broker is None:
                return self.error(f"No broker with id {broker_id}")
            if not broker.active:
                return self.error(f"Broker {broker.name} is not active")

            operation = "get_alert" if alert_id is not None else "query_alerts"
            if not broker.broker_class.implements()[operation]:
                return self.error(
                    f"Broker {broker.name} does not support '{operation}'."
                )

            params["permissions"] = alert_permissions(self.current_user, session)

            try:
                if alert_id is not None:
                    data = broker.broker_class.get_alert(
                        broker, alert_id, session, **params
                    )
                else:
                    data = broker.broker_class.query_alerts(broker, session, **params)
            except NotImplementedError:
                return self.error(
                    f"Broker {broker.name} does not support '{operation}'."
                )
            except Exception as e:
                return self.error(f"Error querying broker {broker.name}: {e}")

            return self.success(data=data)


class BrokerCutoutsHandler(BaseHandler):
    @auth_or_token
    def get(self, broker_id: int, alert_id: AlertId):
        """
        ---
        summary: Get an alert's cutouts from a broker
        description: Fetch science/template/difference cutouts for an alert,
          dispatched to the broker's provider.
        tags:
          - brokers
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
        params: dict[str, Any] = {
            k: self.get_argument(k) for k in self.request.arguments
        }

        with self.Session() as session:
            broker = session.scalars(
                Broker.select(self.current_user).where(Broker.id == int(broker_id))
            ).first()
            if broker is None:
                return self.error(f"No broker with id {broker_id}")
            if not broker.active:
                return self.error(f"Broker {broker.name} is not active")
            if not broker.broker_class.implements()["get_cutouts"]:
                return self.error(f"Broker {broker.name} does not support cutouts.")
            params["permissions"] = alert_permissions(self.current_user, session)
            try:
                data = broker.broker_class.get_cutouts(
                    broker, alert_id, session, **params
                )
            except Exception as e:
                return self.error(f"Error fetching cutouts from {broker.name}: {e}")
            return self.success(data=data)


class BrokerConeSearchHandler(BaseHandler):
    @auth_or_token
    def get(self, broker_id: int, *, query: BrokerConeSearchGetQuery = None):
        """
        ---
        summary: Cross-match a position against a broker's archival catalogs
        description: Positional cone-search against a broker's reference catalogs
          (e.g. Gaia, PS1, AllWISE), dispatched to the broker's provider. Returns
          matched sources keyed by catalog name.
        tags:
          - brokers
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
        query = self.parse_query(BrokerConeSearchGetQuery)

        with self.Session() as session:
            broker = session.scalars(
                Broker.select(self.current_user).where(Broker.id == int(broker_id))
            ).first()
            if broker is None:
                return self.error(f"No broker with id {broker_id}")
            if not broker.active:
                return self.error(f"Broker {broker.name} is not active")
            if not broker.broker_class.implements()["cone_search"]:
                return self.error(f"Broker {broker.name} does not support cone_search.")
            try:
                data = broker.broker_class.cone_search(
                    broker,
                    query.ra,
                    query.dec,
                    query.radius,
                    session,
                    radius_units=query.radius_units,
                )
            except Exception as e:
                return self.error(f"Error cross-matching with {broker.name}: {e}")
            return self.success(data=data)


class BrokerSaveHandler(BaseHandler):
    @permissions(["Upload data"])
    async def post(
        self, broker_id: int, alert_id: AlertId, *, body: BrokerSaveBody = None
    ):
        """
        ---
        summary: Save a broker alert as a source
        description: Ingest an alert/object from a broker into skyportal as an
          Obj/Source with photometry, dispatched to the broker's provider.
        tags:
          - brokers
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
        body = self.parse_body(BrokerSaveBody)
        try:
            group_ids = [int(gid) for gid in body.group_ids or []]
        except (TypeError, ValueError):
            return self.error("`group_ids` must be a list of integers.")
        if not group_ids:
            return self.error("At least one group_id is required.")

        async with self.AsyncSession() as session:
            broker = await session.scalar(
                Broker.select(self.current_user).where(Broker.id == int(broker_id))
            )
            if broker is None:
                return self.error(f"No broker with id {broker_id}")
            if not broker.active:
                return self.error(f"Broker {broker.name} is not active")
            if not broker.broker_class.implements()["save_as_source"]:
                return self.error(
                    f"Broker {broker.name} does not support save_as_source."
                )
            try:
                result = await broker.broker_class.save_as_source(
                    broker,
                    alert_id,
                    session,
                    self.associated_user_object,
                    group_ids,
                    permissions=await alert_permissions_async(
                        self.current_user, session
                    ),
                )
            except Exception as e:
                return self.error(f"Error saving alert as source: {e}")
            return self.success(data=result)


class BrokerPhotometryHandler(BaseHandler):
    @auth_or_token
    async def get(
        self,
        broker_id: int,
        alert_id: AlertId,
        *,
        query: BrokerPhotometryGetQuery = None,
    ):
        """
        ---
        summary: Display photometry for an object (DB + on-demand broker)
        description: |
          Return an object's photometry for display: the persisted,
          access-controlled photometry from the database merged with photometry
          fetched on demand from the broker (deduped by instrument/filter/mjd,
          so the broker only augments saved points). The broker half is held in
          a read-through cache keyed by the object and the requester's access
          scope, and is never written to the database. Returns a bare list of
          points, matching GET /sources/{id}/photometry.
        tags:
          - brokers
          - photometry
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
        query = self.parse_query(BrokerPhotometryGetQuery)

        async with self.AsyncSession() as session:
            broker = await session.scalar(
                Broker.select(self.current_user).where(Broker.id == int(broker_id))
            )
            if broker is None:
                return self.error(f"No broker with id {broker_id}")
            if not broker.active:
                return self.error(f"Broker {broker.name} is not active")
            if not broker.broker_class.implements()["get_photometry"]:
                return self.error(f"Broker {broker.name} does not support photometry.")
            return await self._respond_photometry(session, broker, alert_id, query)

    async def _respond_photometry(self, session, broker, object_id, query):
        """Serve merged DB + on-demand broker photometry for ``object_id``. When
        ``broker`` is None (no configured provider for the survey), degrade to
        the object's access-controlled DB photometry so the caller still works."""
        from ...broker_apis._photometry import db_photometry_points
        from ...utils.valkey_cache import get_cache

        if broker is None:
            db_points = await db_photometry_points(
                object_id,
                self.associated_user_object,
                session,
                outsys=query.magsys,
                fmt=query.format,
            )
            return self.success(data=db_points)
        try:
            merged = await broker.broker_class.get_photometry(
                broker,
                object_id,
                session,
                self.associated_user_object,
                cache=get_cache(),
                survey=query.survey,
                outsys=query.magsys,
                fmt=query.format,
                refresh=query.refresh,
            )
        except Exception as e:
            return self.error(f"Error fetching photometry from {broker.name}: {e}")
        return self.success(data=merged)


class BrokerSurveyPhotometryHandler(BrokerPhotometryHandler):
    @auth_or_token
    async def get(self, object_id, *, query: BrokerSurveyPhotometryGetQuery = None):
        """
        ---
        summary: Display photometry for an object via the survey's broker
        description: |
          Broker-address-free variant of the photometry passthrough for the
          source-page lightcurve: resolves the active provider that supports
          get_photometry for ``?survey=`` server-side, so a deployment can set
          `photometry_display_endpoint:
          /api/brokers/photometry/{id}?survey=ZTF` without pinning a broker id.
          If no such broker is configured, degrades to the object's DB
          photometry. Returns a bare list of points, matching
          GET /sources/{id}/photometry.
        tags:
          - brokers
          - photometry
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
        query = self.parse_query(BrokerSurveyPhotometryGetQuery)

        async with self.AsyncSession() as session:
            # First active provider that can fetch photometry for this survey.
            # A deployment typically configures one such broker per survey.
            brokers = (
                await session.scalars(
                    Broker.select(self.current_user)
                    .where(Broker.active.is_(True))
                    .order_by(Broker.id)
                )
            ).all()
            broker = next(
                (
                    b
                    for b in brokers
                    if query.survey in b.broker_class.surveys
                    and b.broker_class.implements()["get_photometry"]
                ),
                None,
            )
            return await self._respond_photometry(session, broker, object_id, query)


class BrokerFilterTestHandler(BaseHandler):
    @auth_or_token
    def post(self, broker_id: int, *, body: BrokerFilterTestBody = None):
        """
        ---
        summary: Preview a broker filter
        description: Run/preview a filter against the broker and return matching
          alerts, dispatched to the broker's provider. The request body is
          filter parameters specific to the broker's filter_kind (e.g. Lasair's
          selected/tables/conditions, BOOM's pipeline).
        tags:
          - brokers
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
        params = self.parse_body(BrokerFilterTestBody).root

        with self.Session() as session:
            broker = session.scalars(
                Broker.select(self.current_user).where(Broker.id == int(broker_id))
            ).first()
            if broker is None:
                return self.error(f"No broker with id {broker_id}")
            if not broker.active:
                return self.error(f"Broker {broker.name} is not active")
            if not broker.broker_class.implements()["test_filter"]:
                return self.error(
                    f"Broker {broker.name} does not support filter preview."
                )
            params["permissions"] = alert_permissions(self.current_user, session)
            try:
                data = broker.broker_class.test_filter(broker, session, **params)
            except Exception as e:
                return self.error(f"Error running filter on {broker.name}: {e}")
            return self.success(data=data)


class BrokerFilterValidateHandler(BaseHandler):
    @auth_or_token
    def post(
        self, broker_id: int, filter_id: int, *, body: BrokerFilterValidateBody = None
    ):
        """
        ---
        summary: Validate a broker filter version for activation
        description: Run the broker's activation validation for a filter version
          without changing state, and record the result on the filter so it can
          be activated (skyportal gates activation on this).
        tags:
          - brokers
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
        body = self.parse_body(BrokerFilterValidateBody)
        with self.Session() as session:
            broker = _get_broker(self, session, broker_id)
            if broker is None:
                return self.error(f"No broker with id {broker_id}")
            if not broker.active:
                return self.error(f"Broker {broker.name} is not active")
            if not broker.broker_class.implements()["validate_filter"]:
                return self.error(
                    f"Broker {broker.name} does not support filter validation."
                )
            f = session.scalars(
                Filter.select(self.current_user, mode="update").where(
                    Filter.id == int(filter_id)
                )
            ).first()
            if f is None or not isinstance(f.altdata, dict) or "boom" not in f.altdata:
                return self.error("Filter not found or not broker-managed.")
            boom_filter_id = (f.altdata.get("boom") or {}).get("filter_id")
            try:
                result = broker.broker_class.validate_filter(
                    broker,
                    session,
                    boom_filter_id=boom_filter_id,
                    fid=body.fid,
                )
            except Exception as e:
                return self.error(f"Error validating filter on {broker.name}: {e}")
            # Record the verdict per version (fid) so each version keeps its own
            # result and message; activation reads this. Validating one version no
            # longer clobbers another's verdict.
            _store_version_validation(f.altdata, result)
            flag_modified(f, "altdata")
            session.commit()
            return self.success(data=result)


def _get_broker(handler, session, broker_id):
    return session.scalars(
        Broker.select(handler.current_user).where(Broker.id == int(broker_id))
    ).first()


def _version_validation(altdata, fid):
    """The stored validation verdict for a filter version, or None.

    Reads the per-fid map, falling back to the legacy single-slot record so
    versions validated before the map existed still count.
    """
    boom = (altdata or {}).get("boom") or {}
    verdict = (boom.get("validations") or {}).get(fid)
    if verdict is None:
        legacy = boom.get("validation") or {}
        if legacy.get("fid") == fid:
            verdict = legacy
    return verdict or None


def _store_version_validation(altdata, verdict):
    """Persist a BOOM validation verdict under its fid in the per-fid map."""
    boom = altdata.setdefault("boom", {})
    boom.setdefault("validations", {})[verdict.get("fid")] = {
        "passed": bool(verdict.get("passed")),
        "message": verdict.get("message"),
    }


class BrokerFilterModulesHandler(BaseHandler):
    @auth_or_token
    def get(
        self, broker_id: int, name=None, *, query: BrokerFilterModulesGetQuery = None
    ):
        """
        ---
        summary: Broker filter-building vocabulary
        description: Return the filter modules/schema (fields, operators, and any
          broker-scoped custom variables) for a broker's survey, dispatched to the
          broker's provider. Drives the filter builder UI. With a ``name`` path
          segment, returns just that module (or null when there is no such module).
        tags:
          - brokers
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
        query = self.parse_query(BrokerFilterModulesGetQuery)
        survey, elements = query.survey, query.elements

        with self.Session() as session:
            broker = _get_broker(self, session, broker_id)
            if broker is None:
                return self.error(f"No broker with id {broker_id}")
            if not broker.active:
                return self.error(f"Broker {broker.name} is not active")
            if not broker.broker_class.implements()["filter_modules"]:
                return self.error(
                    f"Broker {broker.name} does not support filter modules."
                )
            kwargs = {"elements": elements}
            if survey:
                kwargs["survey"] = survey
            if name:
                kwargs["name"] = name
            try:
                data = broker.broker_class.filter_modules(broker, session, **kwargs)
            except Exception as e:
                return self.error(
                    f"Error fetching filter modules from {broker.name}: {e}"
                )
            return self.success(data=data)

    @permissions(["Upload data"])
    def post(self, broker_id: int, name, *, body: BrokerFilterModuleWriteBody = None):
        """
        ---
        summary: Create a broker custom filter module
        description: Store a broker-scoped custom filter-building element (a
          variable/listVariable/switchCase/block) named ``name``, for reuse by the
          filter builder. Where it is stored is up to the broker's provider.
        tags:
          - brokers
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
        body = self.parse_body(BrokerFilterModuleWriteBody)
        return self._write_module(broker_id, name, body, insert=True)

    @permissions(["Upload data"])
    def put(self, broker_id: int, name, *, body: BrokerFilterModuleWriteBody = None):
        """
        ---
        summary: Update a broker custom filter module
        description: Update an existing broker-scoped custom filter-building
          element named ``name``.
        tags:
          - brokers
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
        body = self.parse_body(BrokerFilterModuleWriteBody)
        return self._write_module(broker_id, name, body, insert=False)

    def _write_module(self, broker_id, name, body, insert):
        if not name:
            return self.error("A module name is required.")
        elements = body.elements
        payload = body.data
        if elements not in _FILTER_MODULE_ELEMENTS:
            return self.error(
                f"'elements' must be one of {list(_FILTER_MODULE_ELEMENTS)}."
            )
        if not isinstance(payload, dict):
            return self.error("Missing 'data' object.")
        with self.Session() as session:
            broker = _get_broker(self, session, broker_id)
            if broker is None:
                return self.error(f"No broker with id {broker_id}")
            if not broker.active:
                return self.error(f"Broker {broker.name} is not active")
            if not broker.broker_class.implements()["filter_modules"]:
                return self.error(
                    f"Broker {broker.name} does not support filter modules."
                )
            try:
                broker.broker_class.write_filter_module(
                    broker, session, name, elements, payload, insert
                )
            except ValueError as e:
                return self.error(str(e))
            return self.success()


class BrokerFiltersHandler(BaseHandler):
    """Manage a broker's filters, backed by a skyportal ``Filter`` row whose
    ``altdata`` stores the broker-side filter id + the editable version trees.
    The broker-side create/version/activate/delete is dispatched to the provider.
    """

    @auth_or_token
    def get(self, broker_id: int, filter_id: int | None = None):
        """
        ---
        summary: Get broker filter(s)
        description: List skyportal Filters, or get one enriched with the
          broker-side versions/active state (via the provider).
        tags:
          - brokers
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
        with self.Session() as session:
            broker = _get_broker(self, session, broker_id)
            if broker is None:
                return self.error(f"No broker with id {broker_id}")
            if not broker.active:
                return self.error(f"Broker {broker.name} is not active")
            if filter_id is None:
                # .unique(): the access-control join over group members returns a
                # row per member, so a filter would list once per user in its group.
                filters = (
                    session.scalars(
                        Filter.select(self.current_user).where(
                            Filter.broker_id == broker.id
                        )
                    )
                    .unique()
                    .all()
                )
                return self.success(
                    data=[
                        {
                            "id": f.id,
                            "name": f.name,
                            "group_id": f.group_id,
                            "stream_id": f.stream_id,
                            "broker_id": f.broker_id,
                            "autosave": f.autosave,
                            "altdata": f.altdata,
                        }
                        for f in filters
                    ]
                )
            f = session.scalars(
                Filter.select(
                    self.current_user, options=[joinedload(Filter.stream)]
                ).where(Filter.id == int(filter_id))
            ).first()
            if f is None:
                return self.error(f"Cannot find a filter with ID: {filter_id}.")
            result = {
                "id": f.id,
                "name": f.name,
                "group_id": f.group_id,
                "broker_id": f.broker_id,
                "autosave": f.autosave,
                "stream": {"id": f.stream.id, "name": f.stream.name}
                if f.stream
                else None,
                "altdata": f.altdata,
            }
            boom = (
                (f.altdata or {}).get("boom") if isinstance(f.altdata, dict) else None
            )
            if (
                isinstance(boom, dict)
                and boom.get("filter_id") is not None
                and broker.broker_class.implements()["get_filters"]
            ):
                try:
                    v = broker.broker_class.get_filters(
                        broker, session, boom_filter_id=boom["filter_id"]
                    )
                    result["fv"] = v.get("fv")
                    result["active_fid"] = v.get("active_fid")
                    result["active"] = v.get("active")
                    result["filters"] = f.altdata.get("filters")
                except Exception:
                    pass  # broker unreachable: return the local row without versions
            return self.success(data=result)

    @permissions(["Upload data"])
    def post(
        self,
        broker_id: int,
        filter_id: int | None = None,
        *,
        body: BrokerFiltersPostBody = None,
    ):
        """
        ---
        summary: Create a broker filter version
        description: Attach a broker-side filter/version to an existing skyportal
          Filter. The body carries the compiled native filter (``altdata``) and
          the editable version tree (``filters``); the provider forwards it to the
          broker and the broker-side ids are stored in the Filter's altdata.
        tags:
          - brokers
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
        body = self.parse_body(BrokerFiltersPostBody)
        if filter_id is None:
            return self.error("An existing skyportal filter_id is required.")
        with self.Session() as session:
            broker = _get_broker(self, session, broker_id)
            if broker is None:
                return self.error(f"No broker with id {broker_id}")
            if not broker.active:
                return self.error(f"Broker {broker.name} is not active")
            # Query-kind brokers (e.g. Lasair): the "filter" is a saved SQL query
            # (selected/tables/conditions) stored on the skyportal Filter itself,
            # with no broker-side filter object to create.
            if broker.broker_class.filter_kind == "query":
                f = session.scalars(
                    Filter.select(self.current_user, mode="update").where(
                        Filter.id == int(filter_id)
                    )
                ).first()
                if f is None:
                    return self.error(f"Cannot find a filter with ID: {filter_id}.")
                query = body.query or {}
                selected = (query.get("selected") or "").strip()
                tables = (query.get("tables") or "").strip()
                conditions = (query.get("conditions") or "").strip()
                if not selected or not tables:
                    return self.error(
                        "A query filter requires 'selected' and 'tables'."
                    )
                f.broker_id = broker.id
                if "autosave" in body.model_fields_set:
                    set_autosave(f, body.autosave)
                ad = dict(f.altdata) if isinstance(f.altdata, dict) else {}
                ad["lasair"] = {
                    "selected": selected,
                    "tables": tables,
                    "conditions": conditions,
                }
                f.altdata = ad
                flag_modified(f, "altdata")
                session.commit()
                return self.success(
                    data={"id": f.id, "altdata": f.altdata, "autosave": f.autosave}
                )
            if not broker.broker_class.implements()["create_filter"]:
                return self.error(f"Broker {broker.name} does not support filters.")
            f = session.scalars(
                Filter.select(
                    self.current_user,
                    mode="update",
                    options=[joinedload(Filter.stream)],
                ).where(Filter.id == int(filter_id))
            ).first()
            if f is None:
                return self.error(f"Cannot find a filter with ID: {filter_id}.")
            if f.stream is None or not isinstance(f.stream.altdata, dict):
                return self.error(
                    "The filter's stream has no altdata (collection/selector)."
                )
            survey = f.stream.altdata["collection"].split("_")[0]
            perms = {survey: f.stream.altdata["selector"]}
            try:
                if not f.altdata:
                    resp = broker.broker_class.create_filter(
                        broker,
                        session,
                        name=f.name,
                        pipeline=body.altdata,
                        survey=survey,
                        permissions=perms,
                    )
                    f.broker_id = broker.id
                    new_fid = resp["active_fid"]
                    f.altdata = {
                        "boom": {"filter_id": resp["id"]},
                        "autoAnnotate": True,
                        "autoSave": False,
                        "autoFollowup": False,
                        "filters": [{"fid": new_fid, "version": body.filters}],
                    }
                else:
                    boom_filter_id = (f.altdata.get("boom") or {}).get("filter_id")
                    if boom_filter_id is None:
                        return self.error("Existing filter has no broker filter id.")
                    resp = broker.broker_class.create_filter(
                        broker,
                        session,
                        boom_filter_id=boom_filter_id,
                        pipeline=body.altdata,
                    )
                    new_fid = resp["fid"]
                    f.altdata.setdefault("filters", []).append(
                        {"fid": new_fid, "version": body.filters}
                    )
                    flag_modified(f, "altdata")
            except Exception as e:
                return self.error(f"Error creating filter on {broker.name}: {e}")
            # Validate the new version now so its verdict (pass, or the failure
            # reason) is attached immediately, rather than only once the user
            # remembers to validate it. Best-effort: a slow/failed validation must
            # not fail the save -- the user can still validate manually.
            if broker.broker_class.implements()["validate_filter"]:
                try:
                    verdict = broker.broker_class.validate_filter(
                        broker,
                        session,
                        boom_filter_id=(f.altdata.get("boom") or {}).get("filter_id"),
                        fid=new_fid,
                    )
                    _store_version_validation(f.altdata, verdict)
                    flag_modified(f, "altdata")
                except Exception as e:
                    log(f"Auto-validation of filter {f.id} version {new_fid}: {e}")
            session.commit()
            return self.success(data={"id": f.id})

    @permissions(["Upload data"])
    def patch(
        self, broker_id: int, filter_id: int, *, body: BrokerFiltersPatchBody = None
    ):
        """
        ---
        summary: Update a broker filter
        description: Activate a version (``active``/``active_fid``, forwarded to
          the broker) or toggle autoAnnotate/autoSave/autoFollowup flags.
        tags:
          - brokers
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
        body = self.parse_body(BrokerFiltersPatchBody)
        with self.Session() as session:
            broker = _get_broker(self, session, broker_id)
            if broker is None:
                return self.error(f"No broker with id {broker_id}")
            if not broker.active:
                return self.error(f"Broker {broker.name} is not active")
            f = session.scalars(
                Filter.select(self.current_user, mode="update").where(
                    Filter.id == int(filter_id)
                )
            ).first()
            if f is None or not isinstance(f.altdata, dict) or "boom" not in f.altdata:
                return self.error("Filter not found or not broker-managed.")
            boom_filter_id = (f.altdata.get("boom") or {}).get("filter_id")
            try:
                if (
                    "active" in body.model_fields_set
                    and "active_fid" in body.model_fields_set
                ):
                    # skyportal owns the activation gate: activate only if the
                    # selected version has a passing validation on record, or the
                    # user is an admin. BOOM then skips its own (slow) inline
                    # validation, so the toggle is fast.
                    if body.active:
                        verdict = _version_validation(f.altdata, body.active_fid) or {}
                        if (
                            verdict.get("passed") is not True
                            and not self.current_user.is_system_admin
                        ):
                            reason = verdict.get("message")
                            return self.error(
                                "This filter version must be validated before it "
                                "can be activated."
                                + (
                                    f" Last validation failed: {reason}"
                                    if reason
                                    else ""
                                )
                            )
                    broker.broker_class.update_filter(
                        broker,
                        session,
                        boom_filter_id=boom_filter_id,
                        active=body.active,
                        active_fid=body.active_fid,
                        skip_validation=True,
                    )
                for flag in ("autoAnnotate", "autoSave", "autoFollowup"):
                    if flag in body.model_fields_set:
                        f.altdata[flag] = getattr(body, flag)
                        flag_modified(f, "altdata")
                # autoSave is the UI's name for the column ingestion reads.
                if "autoSave" in body.model_fields_set:
                    set_autosave(f, body.autoSave)
                # Groups whose members are not auto-saved (e.g. junk).
                if "autoSaveIgnoreGroupIds" in body.model_fields_set:
                    f.altdata["autoSaveIgnoreGroupIds"] = [
                        int(g) for g in (body.autoSaveIgnoreGroupIds or [])
                    ]
                    flag_modified(f, "altdata")
                # Also skip auto-save if a junk-group source lies within this many
                # arcsec (positional dedup for AGN / high-PM duplicates).
                if "autoSaveIgnoreRadius" in body.model_fields_set:
                    radius = body.autoSaveIgnoreRadius
                    if radius in (None, ""):
                        f.altdata.pop("autoSaveIgnoreRadius", None)
                    else:
                        f.altdata["autoSaveIgnoreRadius"] = float(radius)
                    flag_modified(f, "altdata")
                # Attribute auto-saves to a service user (must be in the group).
                if "autoSaveSaverId" in body.model_fields_set:
                    saver_id = body.autoSaveSaverId
                    if saver_id in (None, ""):
                        f.altdata.pop("autoSaveSaverId", None)
                    else:
                        saver_id = int(saver_id)
                        member = session.scalar(
                            sa.select(GroupUser).where(
                                GroupUser.user_id == saver_id,
                                GroupUser.group_id == f.group_id,
                            )
                        )
                        if member is None:
                            return self.error(
                                "autoSaveSaverId must be a member of the "
                                "filter's group."
                            )
                        f.altdata["autoSaveSaverId"] = saver_id
                    flag_modified(f, "altdata")
                # Comment posted on each auto-save.
                if "autoSaveComment" in body.model_fields_set:
                    comment = body.autoSaveComment
                    if comment in (None, ""):
                        f.altdata.pop("autoSaveComment", None)
                    else:
                        f.altdata["autoSaveComment"] = str(comment)
                    flag_modified(f, "altdata")
                # Links the filter to its auto-followup DefaultFollowupRequest.
                if "autoFollowupDefaultId" in body.model_fields_set:
                    default_id = body.autoFollowupDefaultId
                    if default_id in (None, ""):
                        f.altdata.pop("autoFollowupDefaultId", None)
                    else:
                        f.altdata["autoFollowupDefaultId"] = int(default_id)
                    flag_modified(f, "altdata")
            except Exception as e:
                return self.error(f"Error updating filter on {broker.name}: {e}")
            session.commit()
            return self.success()

    @permissions(["Upload data"])
    def delete(self, broker_id: int, filter_id: int):
        """
        ---
        summary: Delete a broker filter
        description: Delete the skyportal Filter and (best-effort) its broker-side
          filter via the provider.
        tags:
          - brokers
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
        with self.Session() as session:
            broker = _get_broker(self, session, broker_id)
            if broker is None:
                return self.error(f"No broker with id {broker_id}")
            if not broker.active:
                return self.error(f"Broker {broker.name} is not active")
            f = session.scalars(
                Filter.select(self.current_user, mode="delete").where(
                    Filter.id == int(filter_id)
                )
            ).first()
            if f is None:
                return self.error(f"Cannot find a filter with ID: {filter_id}.")
            boom = (
                (f.altdata or {}).get("boom") if isinstance(f.altdata, dict) else None
            )
            if (
                isinstance(boom, dict)
                and boom.get("filter_id") is not None
                and broker.broker_class.implements()["delete_filter"]
            ):
                try:
                    broker.broker_class.delete_filter(
                        broker, session, boom_filter_id=boom["filter_id"]
                    )
                except Exception:
                    pass
            session.delete(f)
            session.commit()
            return self.success()


class BrokerFilterCatalogHandler(BaseHandler):
    @auth_or_token
    def get(self, *, query: BrokerFilterCatalogGetQuery = None):
        """
        ---
        summary: List filters and their broker
        description: Paginated list of the skyportal Filters accessible to the
          user, optionally restricted to the ones attached to no broker.
        tags:
          - brokers
          - filters
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
        query = self.parse_query(BrokerFilterCatalogGetQuery)

        n_per_page = min(max(query.numPerPage, 1), MAX_FILTERS_PER_PAGE)
        page_number = max(query.pageNumber, 1)

        name = query.name
        group_id = query.groupID
        stream_id = query.streamID
        broker_id = query.brokerID
        try:
            if broker_id and broker_id != "none":
                broker_id = int(broker_id)
        except ValueError:
            return self.error("brokerID must be an integer.")

        with self.Session() as session:
            stmt = Filter.select(self.current_user).distinct()
            if broker_id == "none":
                stmt = stmt.where(Filter.broker_id.is_(None))
            elif broker_id:
                stmt = stmt.where(Filter.broker_id == broker_id)
            if name:
                stmt = stmt.where(Filter.name.ilike(f"%{name}%"))
            if group_id:
                stmt = stmt.where(Filter.group_id == group_id)
            if stream_id:
                stmt = stmt.where(Filter.stream_id == stream_id)

            total_matches = session.scalar(
                sa.select(sa.func.count()).select_from(stmt.subquery())
            )
            filters = session.scalars(
                stmt.order_by(Filter.name, Filter.id)
                .limit(n_per_page)
                .offset((page_number - 1) * n_per_page)
            ).all()
            return self.success(
                data={
                    "filters": [
                        {
                            "id": f.id,
                            "name": f.name,
                            "group_id": f.group_id,
                            "stream_id": f.stream_id,
                            "broker_id": f.broker_id,
                            "autosave": f.autosave,
                            "altdata": f.altdata,
                        }
                        for f in filters
                    ],
                    "totalMatches": int(total_matches),
                }
            )


class BrokerFilterAttachHandler(BaseHandler):
    @permissions(["Upload data"])
    def post(self, filter_id: int, *, body: BrokerFilterAttachBody = None):
        """
        ---
        summary: Attach a filter to a broker
        description: Bind an unattached skyportal Filter to a broker.
        tags:
          - brokers
          - filters
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
        broker_id = self.parse_body(BrokerFilterAttachBody).broker_id
        with self.Session() as session:
            broker = _get_broker(self, session, broker_id)
            if broker is None:
                return self.error(f"No broker with id {broker_id}")
            if not broker.active:
                return self.error(f"Broker {broker.name} is not active")
            if broker.broker_class.filter_kind == "none":
                return self.error(f"Broker {broker.name} does not accept filters.")
            f = session.scalars(
                Filter.select(self.current_user, mode="update").where(
                    Filter.id == int(filter_id)
                )
            ).first()
            if f is None:
                return self.error(f"Cannot find a filter with ID: {filter_id}.")
            if f.broker_id not in (None, broker.id):
                return self.error("This filter is already attached to a broker.")
            f.broker_id = broker.id
            session.commit()
            return self.success(data={"id": f.id, "broker_id": f.broker_id})
