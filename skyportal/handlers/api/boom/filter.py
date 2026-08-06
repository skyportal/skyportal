import requests
from marshmallow.exceptions import ValidationError
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.attributes import flag_modified

from baselayer.app.access import auth_or_token, permissions
from baselayer.app.env import load_env
from baselayer.log import make_log

from ....models import Filter
from ...base import BaseHandler
from .utils import boom_available, boom_token, boom_url

log = make_log("app/boom-filter")

_, cfg = load_env()


class BoomFilterHandler(BaseHandler):
    @auth_or_token
    @boom_available
    async def get(self, filter_id):
        """
        ---
        summary: Get a filter
        description: Retrieve a filter
        tags:
          - filters
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
                schema: SingleFilter
          400:
            content:
              application/json:
                schema: Error
        """
        try:
            filter_id = int(filter_id)
        except ValueError:
            return self.error(f"Invalid filter_id: {filter_id}. Must be an integer.")

        async with self.AsyncSession() as session:
            if filter_id is not None:
                f = await session.scalar(
                    Filter.select(
                        session.user_or_token, options=[joinedload(Filter.stream)]
                    ).where(Filter.id == filter_id)
                )
                if f is None:
                    return self.error(f"Cannot find a filter with ID: {filter_id}.")

                if isinstance(f.altdata, dict) and isinstance(
                    f.altdata.get("boom"), dict
                ):
                    boom_filter_id = f.altdata["boom"].get("filter_id", None)
                    if boom_filter_id is not None:
                        url = f"{boom_url}/filters/{f.altdata['boom']['filter_id']}"
                        headers = {
                            "Authorization": f"Bearer {boom_token}",
                        }
                        response = requests.get(url, headers=headers, timeout=10)
                        response.raise_for_status()

                        f.fv = response.json()["data"]["fv"]
                        f.active_fid = response.json()["data"]["active_fid"]
                        f.active = response.json()["data"]["active"]
                        f.filters = f.altdata["filters"]

                return self.success(data=f)

            filters = (
                await session.scalars(Filter.select(session.user_or_token))
            ).all()
            return self.success(data=filters)

    @permissions(["Upload data"])
    @boom_available
    async def post(self, filter_id=None):
        """
        ---
        summary: Create a new filter
        description: POST a new filter.
        tags:
          - filters
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
                          properties:
                            id:
                              type: integer
                              description: New filter ID
        """
        data = self.get_json()
        async with self.AsyncSession() as session:
            if filter_id is not None:
                try:
                    filter_id = int(filter_id)
                except ValueError:
                    return self.error(
                        f"Invalid filter_id: {filter_id}. Must be an integer."
                    )
                f = await session.scalar(
                    Filter.select(session.user_or_token, mode="update")
                    .where(Filter.id == filter_id)
                    .options(selectinload(Filter.stream))  # f.stream read below
                )

                if f is None:
                    return self.error(f"Cannot find a filter with ID: {filter_id}.")

                if not f.altdata:
                    data_url = f"{boom_url}/filters"
                    data_payload = {
                        "name": data["name"],
                        "pipeline": data["altdata"],
                        "permissions": {
                            f.stream.altdata["collection"].split("_")[
                                0
                            ]: f.stream.altdata["selector"]
                        },
                        "survey": f.stream.altdata["collection"].split("_")[0],
                    }

                    headers = {
                        "Authorization": f"Bearer {boom_token}",
                        "Content-Type": "application/json",
                    }

                    response = requests.post(
                        data_url, json=data_payload, headers=headers, timeout=10
                    )
                    if not response.ok:
                        # Surface BOOM's actual rejection message instead
                        # of just the bare HTTP status from raise_for_status.
                        return self.error(
                            f"BOOM rejected filter creation "
                            f"({response.status_code}): {response.text}"
                        )
                    data = {
                        "altdata": {
                            "boom": {"filter_id": response.json()["data"]["id"]},
                            "autoAnnotate": False,
                            "autoSave": False,
                            "autoFollowup": False,
                            "filters": [
                                {
                                    "fid": response.json()["data"]["active_fid"],
                                    "version": data["filters"],
                                }
                            ],
                        },
                    }
                else:
                    if not (
                        isinstance(f.altdata, dict)
                        and isinstance(f.altdata.get("boom"), dict)
                    ):
                        return self.error(
                            "Existing filter altdata is not in expected format."
                        )
                    if "filter_id" not in f.altdata["boom"]:
                        return self.error(
                            "Existing filter altdata does not contain Boom filter ID."
                        )
                    if "filters" not in f.altdata or not isinstance(
                        f.altdata["filters"], list
                    ):
                        return self.error(
                            "Existing filter altdata does not contain filters list."
                        )
                    data_url = (
                        f"{boom_url}/filters/{f.altdata['boom']['filter_id']}/versions"
                    )
                    data_payload = {
                        "pipeline": data["altdata"],
                    }

                    headers = {
                        "Authorization": f"Bearer {boom_token}",
                        "Content-Type": "application/json",
                    }
                    response = requests.post(
                        data_url, json=data_payload, headers=headers, timeout=10
                    )
                    response.raise_for_status()

                    f.altdata["filters"].append(
                        {
                            "fid": response.json()["data"]["fid"],
                            "version": data["filters"],
                        }
                    )
                    flag_modified(f, "altdata")
                    await session.commit()
                    return self.success(data={"id": f.id})

                for k in data:
                    setattr(f, k, data[k])
                await session.commit()
                return self.success(data={"id": f.id})

            schema = Filter.__schema__()
            try:
                fil = schema.load(data, partial=False)
            except ValidationError as e:
                return self.error(
                    f"Invalid/missing parameters: {e.normalized_messages()}"
                )

            session.add(fil)
            await session.commit()
            return self.success(data={"id": fil.id})

    @permissions(["Upload data"])
    @boom_available
    async def patch(self, filter_id):
        """
        ---
        summary: Update a filter
        description: Update filter name
        tags:
          - filters
        parameters:
          - in: path
            name: filter_id
            required: True
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: FilterNoID
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
        try:
            filter_id = int(filter_id)
        except ValueError:
            return self.error(f"Invalid filter_id: {filter_id}. Must be an integer.")

        async with self.AsyncSession() as session:
            f = await session.scalar(
                Filter.select(session.user_or_token, mode="update").where(
                    Filter.id == filter_id
                )
            )
            if f is None:
                return self.error(f"Cannot find a filter with ID: {filter_id}.")
            if not isinstance(f.altdata, dict) or not isinstance(
                f.altdata.get("boom"), dict
            ):
                return self.error("Filter altdata is not in expected format.")
            if "filter_id" not in f.altdata["boom"]:
                return self.error("Filter altdata does not contain Boom filter ID.")

            data = self.get_json()
            if "active" in data and "active_fid" in data:
                data_url = f"{boom_url}/filters/{f.altdata['boom']['filter_id']}"
                data_payload = {
                    # Your data here, e.g. for /filters:
                    "active": data["active"],
                    "active_fid": data["active_fid"],
                }

                # Step 3: Send the PATCH request with the token
                headers = {
                    "Authorization": f"Bearer {boom_token}",
                    "Content-Type": "application/json",
                }
                response = requests.patch(
                    data_url, json=data_payload, headers=headers, timeout=10
                )
                response.raise_for_status()
            elif "autoAnnotate" in data:
                f.altdata["autoAnnotate"] = data["autoAnnotate"]
                flag_modified(f, "altdata")
            elif "autoSave" in data:
                f.altdata["autoSave"] = data["autoSave"]
                flag_modified(f, "altdata")
            elif "autoFollowup" in data:
                f.altdata["autoFollowup"] = data["autoFollowup"]
                flag_modified(f, "altdata")

            await session.commit()
            return self.success()

    @permissions(["Upload data"])
    @boom_available
    async def delete(self, filter_id):
        """
        ---
        summary: Delete a filter
        description: Delete a filter
        tags:
          - filters
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
        try:
            filter_id = int(filter_id)
        except ValueError:
            return self.error(f"Invalid filter_id: {filter_id}. Must be an integer.")

        async with self.AsyncSession() as session:
            f = (
                await session.scalars(
                    Filter.select(session.user_or_token, mode="delete").where(
                        Filter.id == filter_id
                    )
                )
            ).first()
            if f is None:
                return self.error(f"Cannot find a filter with ID: {filter_id}.")
            await session.delete(f)
            await session.commit()
            return self.success()
