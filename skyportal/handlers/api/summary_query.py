import copy
import os
from typing import Any

import yaml
from langchain_openai import OpenAIEmbeddings
from pydantic import BaseModel, ConfigDict, Field

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from baselayer.log import make_log

from ...models import Source, User
from ...utils.embedding_store import (
    PGVECTOR,
    search_embeddings,
    search_embeddings_by_obj,
    store_location,
)
from ..base import BaseHandler

_, cfg = load_env()
log = make_log("query")


def embed_query_text(query: str, openai_api_key: str) -> list[float]:
    """The query's vector, from whichever server the embedding config names."""
    embeddings = OpenAIEmbeddings(
        model=summarize_embedding_model,
        openai_api_key=openai_api_key,
        base_url=summarize_embedding_base_url,
        # Send the text itself, as the analysis service does, rather than the
        # token ids langchain sends by default and other servers reject.
        check_embedding_ctx_length=False,
    )
    return embeddings.embed_query(query)


summarize_embedding_config = cfg[
    "analysis_services.openai_analysis_service.embeddings_store.summary"
]
summarize_embedding_model = summarize_embedding_config.get("model")
# Any server speaking the OpenAI embeddings protocol, not just OpenAI's.
summarize_embedding_base_url = summarize_embedding_config.get("base_url") or None

# The vectors live in our own database, so there is nothing to reach for: the
# search is on when the config names the store and the model that filled it.
USE_PGVECTOR = (
    store_location(summarize_embedding_config) == PGVECTOR
    and summarize_embedding_model is not None
)

summary_config = copy.deepcopy(cfg["analysis_services.openai_analysis_service.summary"])
if summary_config.get("api_key"):
    openai_api_key = summary_config.pop("api_key")
elif os.path.exists(".secret"):
    openai_api_key = yaml.safe_load(open(".secret")).get("OPENAI_API_KEY")
elif cfg["database.database"] == "skyportal_test":
    openai_api_key = "TEST_KEY"
else:
    openai_api_key = None


class SummaryQueryPostBody(BaseModel):
    """Request body for a summary similarity search."""

    model_config = ConfigDict(extra="forbid")

    q: str | None = Field(
        default=None,
        description='The query string. E.g. "What sources are associated with '
        'an NGC galaxy?"',
    )
    objID: str | None = Field(
        default=None,
        description="The objID of the source which has a summary to be used as "
        "the query. That is, return the list of sources most similar to the "
        "summary of this source. Ignored if q is provided.",
    )
    k: int = Field(default=5, description="Max number of sources to return. Default 5.")
    z_min: float | None = Field(
        default=None,
        description="Minimum redshift to consider of queries sources. If None or "
        "missing, then no lower limit is applied.",
    )
    z_max: float | None = Field(
        default=None,
        description="Maximum redshift to consider of queries sources. If None or "
        "missing, then no upper limit is applied.",
    )
    classificationTypes: list[str] | None = Field(
        default=None,
        description="List of classification types to consider. If [] or missing, "
        "then all classification types are considered.",
    )


class SummaryQueryPostResponse(BaseModel):
    """Sources whose summaries match the query."""

    query_results: list[dict[str, Any]] = Field(
        description="Matching sources, most similar first, with their scores"
    )


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

        # Searching from a source uses the vector already stored for it, so only
        # a text query needs the embedding service — and so only it needs a key.
        needs_embedding = bool(query) and not (USE_PGVECTOR and objID)

        user_openai_key = None
        if not openai_api_key:
            user_id = self.associated_user_object.id
            async with self.AsyncSession() as session:
                user = await session.scalar(
                    User.select(session.user_or_token, mode="read").where(
                        User.id == user_id
                    )
                )
                if user is None:
                    return self.error(
                        "No global OpenAI key found and cannot find user.", status=400
                    )

                if user.preferences is not None and user.preferences.get(
                    "summary", {}
                ).get("OpenAI", {}).get("active", False):
                    user_openai_key = user.preferences["summary"]["OpenAI"].get(
                        "apikey"
                    )
        else:
            user_openai_key = openai_api_key
        if needs_embedding and not user_openai_key:
            return self.error("No OpenAI API key found.", status=400)

        if objID:
            # Without this, anyone could ask what a source they cannot read is
            # similar to. The message does not distinguish "no such obj" from
            # "not yours", so it says nothing about what exists.
            #
            # Obj itself is public; what a user may see is the Source rows tying
            # an obj to their groups, so that is what decides here.
            async with self.AsyncSession() as session:
                anchor = await session.scalar(
                    Source.select(session.user_or_token, columns=[Source.obj_id]).where(
                        Source.obj_id == objID, Source.active.is_(True)
                    )
                )
            if anchor is None:
                return self.error(f"Cannot access object {objID}", status=403)

        classes = body.classificationTypes or None
        try:
            async with self.AsyncSession() as session:
                # A summary is as readable as the source it describes, so
                # the search sees exactly the sources saved to the
                # requester's groups.
                accessible = Source.select(
                    session.user_or_token, columns=[Source.obj_id]
                ).where(Source.active.is_(True))
                if query:
                    vector = embed_query_text(query, user_openai_key)
                    results = await search_embeddings(
                        session,
                        vector,
                        k,
                        summarize_embedding_model,
                        accessible,
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
                        z_min,
                        z_max,
                        classes,
                    )
        except Exception as e:
            return self.error(f"Could not search sources: {e}")
        return self.success(data={"query_results": results})
