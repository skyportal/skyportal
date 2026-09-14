import copy
import os
from typing import Any

import yaml
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone
from pydantic import BaseModel, ConfigDict, Field

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env
from baselayer.log import make_log

from ...models import Source, User
from ...utils.embedding_store import (
    PGVECTOR,
    PINECONE,
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
        embedding_ctx_length=summarize_embedding_index_size,
        openai_api_key=openai_api_key,
        base_url=summarize_embedding_base_url,
    )
    return embeddings.embed_query(query)


def search_sources(
    client: Pinecone,
    query: str,
    k: int = 4,
    filter: dict | None = None,
    index_name: str | None = None,
    namespace: str | None = None,
    openai_api_key: str | None = None,
) -> list[dict]:
    """Return pinecone documents most similar to query, along with scores.

    Args:
        client: Pinecone client object.
        query: Text to look up documents similar to.
        k: Number of Documents to return. Defaults to 4.
        filter: Dictionary of argument(s) to filter on metadata
        index_name: Name of the index to search in.
        namespace: Namespace to search in. Default will search in '' namespace.
        openai_api_key: API key for the embedding service.
    Returns:
        List of source dictionaries most similar to the query and score for each
    """
    if client is None:
        raise ValueError("pinecone_client must be provided")
    if index_name is None:
        raise ValueError("index_name must be provided")
    if openai_api_key is None:
        raise ValueError("openai_api_key must be provided")

    query_vector = embed_query_text(query, openai_api_key)

    # The index stores vectors of one width, set when it was built. Asking a
    # different model for the query vector is the easy mistake once the endpoint
    # is configurable, and pinecone reports it only as a shape error.
    if (
        summarize_embedding_index_size
        and len(query_vector) != summarize_embedding_index_size
    ):
        raise ValueError(
            f"{summarize_embedding_model} returns {len(query_vector)}-d vectors but index "
            f"{index_name} holds {summarize_embedding_index_size}-d ones. Point "
            "embeddings_store.summary at the model the index was built with, or rebuild "
            "the index at this width."
        )

    index = client.Index(index_name)
    results = index.query(
        top_k=k,
        vector=query_vector,
        include_values=False,
        include_metadata=True,
        namespace=namespace,
        filter=filter,
    )

    sources = []
    for res in results["matches"]:
        try:
            sources.append(
                {"id": res["id"], "score": res["score"], "metadata": res["metadata"]}
            )
        except Exception as e:
            log(f"Error: {e}")
    return sources


pinecone_client = None

summarize_embedding_config = cfg[
    "analysis_services.openai_analysis_service.embeddings_store.summary"
]
# Bound unconditionally: the test path turns pinecone on without taking the
# branch below, and search_sources reads these at call time either way.
summarize_embedding_index_name = summarize_embedding_config.get("index_name")
summarize_embedding_index_size = summarize_embedding_config.get("index_size")
summarize_embedding_model = summarize_embedding_config.get("model")
# Any server speaking the OpenAI embeddings protocol, not just OpenAI's.
summarize_embedding_base_url = summarize_embedding_config.get("base_url") or None

EMBEDDING_LOCATION = store_location(summarize_embedding_config)
# pgvector keeps the vectors in our own database, so there is nothing to reach
# for and nothing to check beyond the table the migration creates.
USE_PGVECTOR = EMBEDDING_LOCATION == PGVECTOR

USE_PINECONE = False
if (
    EMBEDDING_LOCATION == PINECONE
    and summarize_embedding_config.get("api_key")
    and summarize_embedding_index_name
    and summarize_embedding_index_size
):
    log("initializing pinecone access...")
    pinecone_client = Pinecone(
        api_key=summarize_embedding_config.get("api_key"),
    )

    if summarize_embedding_index_name in [
        index.name for index in pinecone_client.list_indexes().indexes
    ]:
        USE_PINECONE = True
elif cfg["database.database"] == "skyportal_test":
    USE_PINECONE = True
    log("Setting USE_PINECONE=True as it seems like we are in a test environment")

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

        if not (USE_PINECONE or USE_PGVECTOR):
            return self.error(
                "No valid embeddings_store configuration found. Please check your "
                "config file."
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
                        Source.obj_id == objID
                    )
                )
            if anchor is None:
                return self.error(f"Cannot access object {objID}", status=403)

        if USE_PGVECTOR:
            classes = body.classificationTypes or None
            try:
                async with self.AsyncSession() as session:
                    # A summary is as readable as the source it describes, so
                    # the search sees exactly the sources saved to the
                    # requester's groups.
                    accessible = Source.select(
                        session.user_or_token, columns=[Source.obj_id]
                    )
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

        filters = []
        if z_min is not None:
            filters.append({"redshift": {"$gte": z_min}})
        if z_max is not None:
            filters.append({"redshift": {"$lte": z_max}})
        if body.classificationTypes:
            filters.append({"class": {"$in": body.classificationTypes}})
        if not filters:
            filt = {}
        elif len(filters) == 1:
            filt = filters[0]
        else:
            filt = {"$and": filters}

        if query:
            try:
                results = search_sources(
                    pinecone_client,
                    query,
                    k,
                    filt,
                    summarize_embedding_index_name,
                    "",
                    user_openai_key,
                )
            except Exception as e:
                return self.error(f"Could not search sources: {e}")
        else:
            try:
                index = pinecone_client.Index(summarize_embedding_index_name)
                query_response = index.query(
                    top_k=k,
                    index=summarize_embedding_index_name,
                    include_values=False,
                    include_metadata=True,
                    id=objID,
                    filter=filt,
                )
                results = query_response.get("matches", [])
            except Exception as e:
                return self.error(f"Could not query index: {e}")

        # Pinecone cannot express who may read a source, so its results are
        # filtered here. That can leave fewer than k: another reason to prefer
        # the pgvector backend, which applies the same rule inside the query.
        ids = [r["id"] for r in results if r.get("id")]
        if ids:
            async with self.AsyncSession() as session:
                allowed = set(
                    (
                        await session.scalars(
                            Source.select(
                                session.user_or_token, columns=[Source.obj_id]
                            ).where(Source.obj_id.in_(ids))
                        )
                    ).all()
                )
            results = [r for r in results if r.get("id") in allowed]

        return self.success(data={"query_results": results})
