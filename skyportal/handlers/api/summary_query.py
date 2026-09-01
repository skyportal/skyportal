import copy
import os

import yaml
from openai import OpenAI
from skyportal_py_models.summary_query import (
    SummaryQueryPostBody,
    SummaryQueryPostResponse,
)
from tornado.ioloop import IOLoop

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env

from ...models import Classification, Source, User
from ...utils.embedding_store import search_embeddings, search_embeddings_by_obj
from ...utils.embedding_store_config import summary_embeddings_enabled
from ..base import BaseHandler

_, cfg = load_env()


def embed_query_text(query: str, openai_api_key: str) -> list[float]:
    """The query's vector, from whichever server the embedding config names."""
    client = OpenAI(
        # A server of one's own may want no key at all, but the client insists.
        api_key=openai_api_key or "none",
        base_url=summarize_embedding_base_url,
    )
    embedding = client.embeddings.create(
        input=query,
        model=summarize_embedding_model,
    )
    return embedding.data[0].embedding


summarize_embedding_config = (
    cfg["analysis_services.openai_analysis_service.embeddings_store.summary"] or {}
)
summarize_embedding_model = summarize_embedding_config.get("model")
# Any server speaking the OpenAI embeddings protocol, not just OpenAI's.
summarize_embedding_base_url = summarize_embedding_config.get("base_url") or None
summarize_embedding_api_key = summarize_embedding_config.get("api_key") or None
summarize_embedding_min_score = summarize_embedding_config.get("min_score")

USE_PGVECTOR = summary_embeddings_enabled(summarize_embedding_config)

summary_config = copy.deepcopy(cfg["analysis_services.openai_analysis_service.summary"])
if summary_config.get("api_key"):
    openai_api_key = summary_config.pop("api_key")
elif os.path.exists(".secret"):
    openai_api_key = yaml.safe_load(open(".secret")).get("OPENAI_API_KEY")
elif cfg["database.database"] == "skyportal_test":
    openai_api_key = "TEST_KEY"
else:
    openai_api_key = None


class SummaryQueryHandler(BaseHandler):
    @auth_or_token
    async def post(
        self, *, body: SummaryQueryPostBody = None
    ) -> SummaryQueryPostResponse:
        """
        ---
        summary: Search for sources based on their summaries
        description: Get a list of sources with summaries matching the query
        tags:
          - summary
        """
        body = self.parse_body(SummaryQueryPostBody)

        if not USE_PGVECTOR:
            return self.error(
                "No summary embeddings store is configured. Set "
                "analysis_services.openai_analysis_service.embeddings_store.summary."
            )

        query = body.q
        objID = body.objID
        if not query and not objID:
            return self.error('Missing one of the required: "q" or "objID"')
        if query is not None and objID is not None:
            return self.error('Cannot specify both "q" and "objID"')

        k = body.k
        if k < 1 or k > 100:
            return self.error("k must be 1<=k<=100")
        z_min, z_max = body.z_min, body.z_max
        if z_min is not None and z_max is not None and z_min > z_max:
            return self.error("z_min must be <= z_max")

        # Only a text query needs the embedding service; searching from a source
        # uses the vector already stored for it. Only OpenAI itself, configured
        # without a key of its own, is reached with the requester's.
        embedding_key = summarize_embedding_api_key
        if query and not embedding_key and not summarize_embedding_base_url:
            embedding_key = openai_api_key
            if not embedding_key:
                user_id = self.associated_user_object.id
                async with self.AsyncSession() as session:
                    user = await session.scalar(
                        User.select(session.user_or_token, mode="read").where(
                            User.id == user_id
                        )
                    )
                    if user is None:
                        return self.error(
                            "No global OpenAI key found and cannot find user.",
                            status=400,
                        )

                    if user.preferences is not None and user.preferences.get(
                        "summary", {}
                    ).get("OpenAI", {}).get("active", False):
                        embedding_key = user.preferences["summary"]["OpenAI"].get(
                            "apikey"
                        )
            if not embedding_key:
                return self.error("No OpenAI API key found.", status=400)

        classes = body.classificationTypes or None
        try:
            # A blocking HTTP round-trip: run off the event loop, and before a
            # session is taken.
            vector = (
                await IOLoop.current().run_in_executor(
                    None, embed_query_text, query, embedding_key
                )
                if query
                else None
            )
            async with self.AsyncSession() as session:
                # A summary is as readable as the source it describes.
                accessible = Source.select(
                    session.user_or_token, columns=[Source.obj_id]
                ).where(Source.active.is_(True))
                if objID:
                    # The message says nothing about what exists.
                    anchor = await session.scalar(
                        accessible.where(Source.obj_id == objID)
                    )
                    if anchor is None:
                        return self.error(f"Cannot access object {objID}", status=403)
                accessible_classifications = Classification.select(
                    session.user_or_token,
                    columns=[Classification.obj_id, Classification.classification],
                )
                if query:
                    # No cut: a question scores far lower against a summary
                    # than a summary does.
                    results = await search_embeddings(
                        session,
                        vector,
                        k,
                        summarize_embedding_model,
                        accessible,
                        accessible_classifications,
                        z_min,
                        z_max,
                        classes,
                    )
                else:
                    results = await search_embeddings_by_obj(
                        session,
                        objID,
                        k,
                        summarize_embedding_model,
                        accessible,
                        accessible_classifications,
                        z_min,
                        z_max,
                        classes,
                        summarize_embedding_min_score,
                    )
        except Exception as e:
            return self.error(f"Could not search sources: {e}")
        return self.success(data={"query_results": results})
