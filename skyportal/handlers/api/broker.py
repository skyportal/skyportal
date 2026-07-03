from baselayer.app.access import auth_or_token, permissions

from ...enum_types import ALLOWED_BROKER_CLASSNAMES
from ...models import Broker
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
