from sqlalchemy.orm import joinedload
from sqlalchemy.orm.attributes import flag_modified

from baselayer.app.access import auth_or_token, permissions

from ...enum_types import ALLOWED_BROKER_CLASSNAMES
from ...models import Broker, Filter
from ..base import BaseHandler


def broker_to_dict(broker, include_altdata=False):
    """Serialize a Broker, redacting encrypted credentials by default."""
    data = {
        "id": broker.id,
        "name": broker.name,
        "broker_classname": broker.broker_classname,
        "active": broker.active,
        "capabilities": broker.broker_class.implements(),
        "surveys": list(broker.broker_class.surveys),
        "filter_kind": broker.broker_class.filter_kind,
    }
    if include_altdata:
        data["altdata"] = broker.altdata
    return data


class BrokerHandler(BaseHandler):
    @permissions(["System admin"])
    def post(self):
        """
        ---
        summary: Create a broker
        description: Register a configured connection to an external alert broker.
        tags:
          - brokers
        requestBody:
          content:
            application/json:
              schema:
                type: object
                required:
                  - name
                  - broker_classname
                properties:
                  name:
                    type: string
                  broker_classname:
                    type: string
                    description: A registered BrokerAPI provider class name.
                  altdata:
                    type: object
                    description: Endpoints/credentials for this broker instance.
                  active:
                    type: boolean
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
        data = self.get_json()
        name = data.get("name")
        broker_classname = data.get("broker_classname")
        altdata = data.get("altdata", {})

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
                active=data.get("active", True),
            )
            if broker.broker_class.implements()["validate_config"]:
                try:
                    broker.broker_class.validate_config(altdata)
                except Exception as e:
                    return self.error(f"Invalid broker configuration: {e}")
            broker.altdata = altdata

            session.add(broker)
            session.commit()
            return self.success(data={"id": broker.id})

    @auth_or_token
    def get(self, broker_id=None):
        """
        ---
        summary: Retrieve broker(s)
        description: Get one broker (by id) or all brokers. Credentials are
          only included for system admins.
        tags:
          - brokers
        parameters:
          - in: path
            name: broker_id
            required: false
            schema:
              type: integer
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
    def patch(self, broker_id):
        """
        ---
        summary: Update a broker
        tags:
          - brokers
        parameters:
          - in: path
            name: broker_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                type: object
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
        data = self.get_json()
        with self.Session() as session:
            broker = session.scalars(
                Broker.select(self.current_user, mode="update").where(
                    Broker.id == int(broker_id)
                )
            ).first()
            if broker is None:
                return self.error(f"No broker with id {broker_id}")

            if "name" in data:
                broker.name = data["name"]
            if "active" in data:
                broker.active = data["active"]
            if "altdata" in data:
                if broker.broker_class.implements()["validate_config"]:
                    try:
                        broker.broker_class.validate_config(data["altdata"])
                    except Exception as e:
                        return self.error(f"Invalid broker configuration: {e}")
                broker.altdata = data["altdata"]

            session.commit()
            return self.success()

    @permissions(["System admin"])
    def delete(self, broker_id):
        """
        ---
        summary: Delete a broker
        tags:
          - brokers
        parameters:
          - in: path
            name: broker_id
            required: true
            schema:
              type: integer
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
    def get(self, broker_id, alert_id=None):
        """
        ---
        summary: Query broker alerts
        description: Search alerts (or fetch one by id) from a broker, dispatched
          to the broker's registered provider.
        tags:
          - brokers
        parameters:
          - in: path
            name: broker_id
            required: true
            schema:
              type: integer
          - in: path
            name: alert_id
            required: false
            schema:
              type: string
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
        params = {k: self.get_argument(k) for k in self.request.arguments}

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
    def get(self, broker_id, alert_id):
        """
        ---
        summary: Get an alert's cutouts from a broker
        description: Fetch science/template/difference cutouts for an alert,
          dispatched to the broker's provider.
        tags:
          - brokers
        parameters:
          - in: path
            name: broker_id
            required: true
            schema:
              type: integer
          - in: path
            name: alert_id
            required: true
            schema:
              type: string
            description: Alert identifier (e.g. candid) the provider keys cutouts on.
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
        params = {k: self.get_argument(k) for k in self.request.arguments}

        with self.Session() as session:
            broker = session.scalars(
                Broker.select(self.current_user).where(Broker.id == int(broker_id))
            ).first()
            if broker is None:
                return self.error(f"No broker with id {broker_id}")
            if not broker.broker_class.implements()["get_cutouts"]:
                return self.error(f"Broker {broker.name} does not support cutouts.")
            try:
                data = broker.broker_class.get_cutouts(
                    broker, alert_id, session, **params
                )
            except Exception as e:
                return self.error(f"Error fetching cutouts from {broker.name}: {e}")
            return self.success(data=data)


class BrokerSaveHandler(BaseHandler):
    @permissions(["Upload data"])
    async def post(self, broker_id, alert_id):
        """
        ---
        summary: Save a broker alert as a source
        description: Ingest an alert/object from a broker into skyportal as an
          Obj/Source with photometry, dispatched to the broker's provider.
        tags:
          - brokers
        parameters:
          - in: path
            name: broker_id
            required: true
            schema:
              type: integer
          - in: path
            name: alert_id
            required: true
            schema:
              type: string
            description: Object identifier to save.
        requestBody:
          content:
            application/json:
              schema:
                type: object
                required:
                  - group_ids
                properties:
                  group_ids:
                    type: array
                    items:
                      type: integer
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
        data = self.get_json()
        try:
            group_ids = [int(gid) for gid in data.get("group_ids") or []]
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
                )
            except Exception as e:
                return self.error(f"Error saving alert as source: {e}")
            return self.success(data=result)


class BrokerFilterTestHandler(BaseHandler):
    @auth_or_token
    def post(self, broker_id):
        """
        ---
        summary: Preview a broker filter
        description: Run/preview a filter against the broker and return matching
          alerts, dispatched to the broker's provider. The request body is
          filter parameters specific to the broker's filter_kind (e.g. Lasair's
          selected/tables/conditions, BOOM's pipeline).
        tags:
          - brokers
        parameters:
          - in: path
            name: broker_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                type: object
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
        params = self.get_json() or {}

        with self.Session() as session:
            broker = session.scalars(
                Broker.select(self.current_user).where(Broker.id == int(broker_id))
            ).first()
            if broker is None:
                return self.error(f"No broker with id {broker_id}")
            if not broker.broker_class.implements()["test_filter"]:
                return self.error(
                    f"Broker {broker.name} does not support filter preview."
                )
            try:
                data = broker.broker_class.test_filter(broker, session, **params)
            except Exception as e:
                return self.error(f"Error running filter on {broker.name}: {e}")
            return self.success(data=data)


def _get_broker(handler, session, broker_id):
    return session.scalars(
        Broker.select(handler.current_user).where(Broker.id == int(broker_id))
    ).first()


# Custom filter-module element types stored broker-scoped in altdata.
_FILTER_MODULE_ELEMENTS = ("variables", "listVariables", "switchCases", "blocks")


class BrokerFilterModulesHandler(BaseHandler):
    @auth_or_token
    def get(self, broker_id, name=None):
        """
        ---
        summary: Broker filter-building vocabulary
        description: Return the filter modules/schema (fields, operators, and any
          broker-scoped custom variables) for a broker's survey, dispatched to the
          broker's provider. Drives the filter builder UI.
        tags:
          - brokers
        parameters:
          - in: path
            name: broker_id
            required: true
            schema:
              type: integer
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
        survey = self.get_query_argument("survey", None)
        elements = self.get_query_argument("elements", "schema")
        with self.Session() as session:
            broker = _get_broker(self, session, broker_id)
            if broker is None:
                return self.error(f"No broker with id {broker_id}")
            if not broker.broker_class.implements()["filter_modules"]:
                return self.error(
                    f"Broker {broker.name} does not support filter modules."
                )
            kwargs = {"elements": elements}
            if survey:
                kwargs["survey"] = survey
            try:
                data = broker.broker_class.filter_modules(broker, session, **kwargs)
            except Exception as e:
                return self.error(
                    f"Error fetching filter modules from {broker.name}: {e}"
                )
            return self.success(data=data)

    @permissions(["Upload data"])
    def post(self, broker_id, name):
        """
        ---
        summary: Create a broker custom filter module
        description: Store a broker-scoped custom filter-building element (a
          variable/listVariable/switchCase/block) named ``name`` in the broker's
          altdata, for reuse by the filter builder.
        tags:
          - brokers
        parameters:
          - in: path
            name: broker_id
            required: true
            schema:
              type: integer
          - in: path
            name: name
            required: true
            schema:
              type: string
        requestBody:
          content:
            application/json:
              schema:
                type: object
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
        return self._write_module(broker_id, name, insert=True)

    @permissions(["Upload data"])
    def put(self, broker_id, name):
        """
        ---
        summary: Update a broker custom filter module
        description: Update an existing broker-scoped custom filter-building
          element named ``name``.
        tags:
          - brokers
        parameters:
          - in: path
            name: broker_id
            required: true
            schema:
              type: integer
          - in: path
            name: name
            required: true
            schema:
              type: string
        requestBody:
          content:
            application/json:
              schema:
                type: object
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
        return self._write_module(broker_id, name, insert=False)

    def _write_module(self, broker_id, name, insert):
        if not name:
            return self.error("A module name is required.")
        data = self.get_json() or {}
        elements = data.get("elements")
        payload = data.get("data")
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
            # Round-trip the whole altdata (credentials preserved, never exposed);
            # only the filter_modules sub-key is mutated.
            altdata = broker.altdata or {}
            modules = altdata.setdefault("filter_modules", {})
            items = modules.setdefault(elements, [])
            existing = next((i for i in items if i.get("name") == name), None)
            if insert:
                item = {"name": name, **payload}
                if existing is not None:
                    items[items.index(existing)] = item
                else:
                    items.append(item)
            else:
                if existing is None:
                    return self.error(f"No {elements} named '{name}'.")
                existing.update(payload)
            broker.altdata = altdata
            session.commit()
            return self.success()


class BrokerFiltersHandler(BaseHandler):
    """Manage a broker's filters, backed by a skyportal ``Filter`` row whose
    ``altdata`` stores the broker-side filter id + the editable version trees.
    The broker-side create/version/activate/delete is dispatched to the provider.
    """

    @auth_or_token
    def get(self, broker_id, filter_id=None):
        """
        ---
        summary: Get broker filter(s)
        description: List skyportal Filters, or get one enriched with the
          broker-side versions/active state (via the provider).
        tags:
          - brokers
        parameters:
          - in: path
            name: broker_id
            required: true
            schema:
              type: integer
          - in: path
            name: filter_id
            required: false
            schema:
              type: integer
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
            if filter_id is None:
                filters = session.scalars(Filter.select(self.current_user)).all()
                return self.success(
                    data=[
                        {
                            "id": f.id,
                            "name": f.name,
                            "group_id": f.group_id,
                            "stream_id": f.stream_id,
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
                "stream_id": f.stream_id,
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
    def post(self, broker_id, filter_id=None):
        """
        ---
        summary: Create a broker filter version
        description: Attach a broker-side filter/version to an existing skyportal
          Filter. The body carries the compiled native filter (``altdata``) and
          the editable version tree (``filters``); the provider forwards it to the
          broker and the broker-side ids are stored in the Filter's altdata.
        tags:
          - brokers
        parameters:
          - in: path
            name: broker_id
            required: true
            schema:
              type: integer
          - in: path
            name: filter_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                type: object
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
        data = self.get_json()
        if filter_id is None:
            return self.error("An existing skyportal filter_id is required.")
        with self.Session() as session:
            broker = _get_broker(self, session, broker_id)
            if broker is None:
                return self.error(f"No broker with id {broker_id}")
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
                        pipeline=data["altdata"],
                        survey=survey,
                        permissions=perms,
                    )
                    f.altdata = {
                        "broker_id": broker.id,
                        "boom": {"filter_id": resp["id"]},
                        "autoAnnotate": False,
                        "autoSave": False,
                        "autoFollowup": False,
                        "filters": [
                            {"fid": resp["active_fid"], "version": data["filters"]}
                        ],
                    }
                else:
                    boom_filter_id = (f.altdata.get("boom") or {}).get("filter_id")
                    if boom_filter_id is None:
                        return self.error("Existing filter has no broker filter id.")
                    resp = broker.broker_class.create_filter(
                        broker,
                        session,
                        boom_filter_id=boom_filter_id,
                        pipeline=data["altdata"],
                    )
                    f.altdata.setdefault("filters", []).append(
                        {"fid": resp["fid"], "version": data["filters"]}
                    )
                    flag_modified(f, "altdata")
            except Exception as e:
                return self.error(f"Error creating filter on {broker.name}: {e}")
            session.commit()
            return self.success(data={"id": f.id})

    @permissions(["Upload data"])
    def patch(self, broker_id, filter_id):
        """
        ---
        summary: Update a broker filter
        description: Activate a version (``active``/``active_fid``, forwarded to
          the broker) or toggle autoAnnotate/autoSave/autoFollowup flags.
        tags:
          - brokers
        parameters:
          - in: path
            name: broker_id
            required: true
            schema:
              type: integer
          - in: path
            name: filter_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                type: object
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
        data = self.get_json()
        with self.Session() as session:
            broker = _get_broker(self, session, broker_id)
            if broker is None:
                return self.error(f"No broker with id {broker_id}")
            f = session.scalars(
                Filter.select(self.current_user, mode="update").where(
                    Filter.id == int(filter_id)
                )
            ).first()
            if f is None or not isinstance(f.altdata, dict) or "boom" not in f.altdata:
                return self.error("Filter not found or not broker-managed.")
            boom_filter_id = (f.altdata.get("boom") or {}).get("filter_id")
            try:
                if "active" in data and "active_fid" in data:
                    broker.broker_class.update_filter(
                        broker,
                        session,
                        boom_filter_id=boom_filter_id,
                        active=data["active"],
                        active_fid=data["active_fid"],
                    )
                for flag in ("autoAnnotate", "autoSave", "autoFollowup"):
                    if flag in data:
                        f.altdata[flag] = data[flag]
                        flag_modified(f, "altdata")
            except Exception as e:
                return self.error(f"Error updating filter on {broker.name}: {e}")
            session.commit()
            return self.success()

    @permissions(["Upload data"])
    def delete(self, broker_id, filter_id):
        """
        ---
        summary: Delete a broker filter
        description: Delete the skyportal Filter and (best-effort) its broker-side
          filter via the provider.
        tags:
          - brokers
        parameters:
          - in: path
            name: broker_id
            required: true
            schema:
              type: integer
          - in: path
            name: filter_id
            required: true
            schema:
              type: integer
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
