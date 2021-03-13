from penquins import Kowalski

from baselayer.log import make_log
from baselayer.app.access import auth_or_token, permissions
from baselayer.app.env import load_env
from ..base import BaseHandler
from ...models import DBSession, Filter, Stream


env, cfg = load_env()
log = make_log("kowalski_filter")


kowalski = Kowalski(
    token=cfg["app.kowalski.token"],
    protocol=cfg["app.kowalski.protocol"],
    host=cfg["app.kowalski.host"],
    port=int(cfg["app.kowalski.port"]),
)
log(f"Kowalski connection OK: {kowalski.ping()}")


class KowalskiFilterHandler(BaseHandler):
    @auth_or_token
    def get(self, filter_id):
        """
        ---
        single:
          description: Retrieve a filter as stored on Kowalski
          tags:
            - filters
            - kowalski
          parameters:
            - in: path
              name: filter_id
              required: true
              schema:
                type: integer
          responses:
            200:
              content:
                application/json:
                  schema:
                    type: object
                    required:
                      - status
                      - message
                      - data
                    properties:
                      status:
                        type: string
                        enum: [success]
                      message:
                        type: string
                      data:
                        type: object
            400:
              content:
                application/json:
                  schema: Error
        """
        f = (
            DBSession()
            .query(Filter)
            .filter(
                Filter.id == int(filter_id),
                Filter.group_id.in_(
                    [g.id for g in self.current_user.accessible_groups]
                ),
            )
            .first()
        )
        if f is None:
            return self.error("Invalid filter ID.")
        response = kowalski.api(
            method="get",
            endpoint=f"api/filters/{filter_id}",
        )
        data = response.get("data")
        # drop monogdb's _id's which are not (default) JSON-serializable
        if data is not None:
            data.pop("_id", None)
        status = response.get("status")
        if status == "error":
            message = response.get("message")
            return self.error(message=message)
        return self.success(data=data)

    @auth_or_token
    def post(self, filter_id):
        """
        ---
        description: POST a new filter version.
        tags:
          - filters
          - kowalski
        requestBody:
          content:
            application/json:
              schema: FilterNoID
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
                          required:
                            - filter_id
                            - pipeline
                          properties:
                            pipeline:
                              type: array
                              items:
                                type: object
                              description: "user-defined aggregation pipeline stages in MQL"
                              minItems: 1
        """
        data = self.get_json()
        pipeline = data.get("pipeline", None)
        if pipeline is None:
            return self.error("Missing pipeline parameter")

        f = (
            DBSession()
            .query(Filter)
            .filter(
                Filter.id == int(filter_id),
                Filter.group_id.in_(
                    [g.id for g in self.current_user.accessible_groups]
                ),
            )
            .first()
        )
        if f is None:
            return self.error("Invalid filter ID.")

        group_id = f.group_id

        # get stream:
        stream = DBSession().query(Stream).filter(Stream.id == f.stream_id).first()

        post_data = {
            "group_id": group_id,
            "filter_id": int(filter_id),
            "catalog": stream.altdata["collection"],
            "permissions": stream.altdata["selector"],
            "pipeline": pipeline,
        }
        response = kowalski.api(
            method="post",
            endpoint="api/filters",
            data=post_data,
        )
        data = response.get("data")
        if data is not None:
            data.pop("_id", None)
        status = response.get("status")
        if status == "error":
            message = response.get("message")
            return self.error(message=message)
        return self.success(data=data)

    @auth_or_token
    def patch(self, filter_id):
        """
        ---
        description: Update a filter on Kowalski
        tags:
          - filters
          - kowalski
        parameters:
          - in: path
            name: filter_id
            required: True
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                type: object
                required:
                  - filter_id
                properties:
                  filter_id:
                    type: integer
                    description: "[fritz] science program filter id for this user group id"
                    minimum: 1
                  active:
                    type: boolean
                    description: "activate or deactivate filter"
                  active_fid:
                    description: "set fid as active version"
                    type: string
                    minLength: 6
                    maxLength: 6
                  autosave:
                    type: boolean
                    description: "automatically save passing candidates to filter's group"
                  update_annotations:
                    type: boolean
                    description: "update annotations for existing candidates"
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
        active = data.get("active", None)
        active_fid = data.get("active_fid", None)
        autosave = data.get("autosave", None)
        update_annotations = data.get("update_annotations", None)
        if (active, active_fid, autosave, update_annotations).count(None) == 4:
            return self.error(
                "At least one of (active, active_fid, autosave, update_annotations) must be set"
            )

        f = (
            DBSession()
            .query(Filter)
            .filter(
                Filter.id == int(filter_id),
                Filter.group_id.in_(
                    [g.id for g in self.current_user.accessible_groups]
                ),
            )
            .first()
        )
        if f is None:
            return self.error("Invalid filter ID.")

        patch_data = {"filter_id": int(filter_id)}

        if active is not None:
            patch_data["active"] = bool(active)
        if active_fid is not None:
            patch_data["active_fid"] = str(active_fid)
        if autosave is not None:
            patch_data["autosave"] = bool(autosave)
        if update_annotations is not None:
            patch_data["update_annotations"] = bool(update_annotations)

        response = kowalski.api(
            method="patch",
            endpoint="api/filters",
            data=patch_data,
        )
        data = response.get("data")
        if data is not None:
            data.pop("_id", None)
        status = response.get("status")
        if status == "error":
            message = response.get("message")
            return self.error(message=message)
        return self.success(data=data)

    @permissions(["System admin"])
    def delete(self, filter_id):
        """
        ---
        description: Delete a filter on Kowalski
        tags:
          - filters
          - kowalski
        parameters:
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
        """
        f = (
            DBSession()
            .query(Filter)
            .filter(
                Filter.id == int(filter_id),
                Filter.group_id.in_(
                    [g.id for g in self.current_user.accessible_groups]
                ),
            )
            .first()
        )
        if f is None:
            return self.error("Invalid filter ID.")

        response = kowalski.api(
            method="patch",
            endpoint=f"api/filters/{filter_id}",
        )
        status = response.get("status")
        if status == "error":
            message = response.get("message")
            return self.error(message=message)
        return self.success()
