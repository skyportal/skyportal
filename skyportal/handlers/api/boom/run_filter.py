import requests
from sqlalchemy.orm import selectinload

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from baselayer.log import make_log

from ....models import Filter
from ...base import BaseHandler
from .utils import boom_available, boom_token, boom_url

log = make_log("app/boom-run-filter")

_, cfg = load_env()


class BoomRunFilterHandler(BaseHandler):
    @auth_or_token
    @boom_available
    async def post(self):
        data = self.get_json()

        filter_id = data.get("filter_id", None)
        if filter_id is None:
            return self.error("Missing required field: filter_id")
        try:
            filter_id = int(filter_id)
        except ValueError:
            return self.error("`filter_id` must be an integer.")

        selected_collection = data.get("selectedCollection", None)
        if selected_collection is None:
            return self.error("Missing required field: selectedCollection")
        if not isinstance(selected_collection, str):
            return self.error("`selectedCollection` must be a string.")
        try:
            survey = selected_collection.split("_")[0]
        except Exception:
            return self.error(
                "Invalid `selectedCollection` format. Expected format: 'SURVEY_collectionName'."
            )
        pipeline = data.get("pipeline", None)
        if not (
            isinstance(pipeline, list)
            and all(isinstance(stage, dict) for stage in pipeline)
        ):
            return self.error("`pipeline` must be a list of dictionaries.")
        start_jd = data.get("start_jd", None)
        end_jd = data.get("end_jd", None)
        if not (isinstance(start_jd, int | float) and isinstance(end_jd, int | float)):
            return self.error("`start_jd` and `end_jd` must be numbers.")
        if start_jd >= end_jd:
            return self.error("`start_jd` must be less than `end_jd`.")
        sort_by = data.get("sort_by", None)
        sort_order = data.get("sort_order", None)
        if (sort_by is not None and sort_order is None) or (
            sort_by is None and sort_order is not None
        ):
            return self.error(
                "Both `sort_by` and `sort_order` must be provided together."
            )
        if sort_order is not None and sort_order not in ("Ascending", "Descending"):
            return self.error(
                "`sort_order` must be either 'Ascending' or 'Descending'."
            )
        limit = data.get("limit", None)
        if limit is not None:
            try:
                limit = int(limit)
            except ValueError:
                return self.error("`limit` must be an integer.")
            if limit <= 0:
                return self.error("`limit` must be a positive integer.")

        async with self.AsyncSession() as session:
            f = await session.scalar(
                Filter.select(session.user_or_token, mode="read")
                .where(Filter.id == filter_id)
                .options(selectinload(Filter.stream))  # f.stream.altdata read below
            )
            if f is None:
                return self.error("Filter not found", status=404)
            if "sort_by" not in data:
                data_url = f"{boom_url}/filters/test/count"
                data_payload = {
                    "permissions": {survey: f.stream.altdata["selector"]},
                    "survey": survey,
                    "pipeline": data["pipeline"],
                    "start_jd": data["start_jd"],
                    "end_jd": data["end_jd"],
                }
            else:
                data_url = f"{boom_url}/filters/test"
                data_payload = {
                    "permissions": {survey: f.stream.altdata["selector"]},
                    "survey": survey,
                    "pipeline": data["pipeline"],
                    "start_jd": data["start_jd"],
                    "end_jd": data["end_jd"],
                    "sort_by": data["sort_by"],
                    "sort_order": data["sort_order"],
                    "limit": data["limit"],
                }
                if "cursor" in data and data["cursor"] is not None:
                    data["cursor"] = int(data["cursor"])
                    if data["sort_order"] == "Ascending":
                        cursor_condition = {"$gt": int(data["cursor"])}
                    else:
                        cursor_condition = {"$lt": int(data["cursor"])}
                    data_payload["pipeline"].insert(
                        len(data_payload["pipeline"]) - 1,
                        {"$match": {"_id": cursor_condition}},
                    )

            headers = {
                "Authorization": f"Bearer {boom_token}",
                "Content-Type": "application/json",
            }

            response = requests.post(data_url, json=data_payload, headers=headers)

            if response.status_code != 200:
                return self.error(
                    f"Error querying Boom: {response.status_code} {response.text}"
                )
            res = response.json()
            if "sort_by" in data:
                res["data"]["results"] = [
                    {**doc, "_id": str(doc["_id"])} for doc in res["data"]["results"]
                ]
        return self.success(data=res)
