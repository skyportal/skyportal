"""Reading the embeddings store config. Kept apart from the search so services
that only need to know whether it is on do not import the model layer."""

__all__ = ["summary_embeddings_enabled"]

PGVECTOR = "pgvector"


def summary_embeddings_enabled(config: dict) -> bool:
    """Whether summary vectors are made and kept: a store, and a model to fill it."""
    config = config or {}
    location = config.get("location")
    return (
        bool(location)
        and str(location).strip().lower() == PGVECTOR
        and config.get("model") is not None
    )
