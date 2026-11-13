from typing import Annotated

from pydantic import Field
from skyportal_py_models.similarity import (
    SimilarSourcesGetQuery,
    SimilarSourcesResponse,
)

from baselayer.app.access import auth_or_token

from ...models import Obj
from ...utils.similarity import find_neighbors, label_neighbors, similarity_broker
from ..base import BaseHandler
from .broker import alert_permissions_async

ObjId = Annotated[str, Field(description="Object whose neighbors to find.")]


class SimilarSourcesHandler(BaseHandler):
    @auth_or_token
    async def get(
        self, obj_id: ObjId, *, query: SimilarSourcesGetQuery = None
    ) -> SimilarSourcesResponse:
        """
        ---
        summary: Get an object's nearest neighbors
        description: Objects closest to this one in a broker's embedding
          space (BOOM's AppleCiDEr embeddings), limited to the programs the
          requester's streams grant. Each neighbor carries its redshift and
          latest human classification when the requester can read it here.
        tags:
          - sources
          - brokers
        """
        query = self.parse_query(SimilarSourcesGetQuery)
        async with self.AsyncSession() as session:
            user = session.user_or_token
            if await session.scalar(Obj.select(user).where(Obj.id == obj_id)) is None:
                return self.error(f"Cannot find object with ID {obj_id}")
            broker = await similarity_broker(session, user, query.brokerId)
            if broker is None:
                return self.error("No active broker serves similarity search")
            permissions = await alert_permissions_async(self.current_user, session)
            try:
                neighbors = await find_neighbors(
                    broker, obj_id, query.topK, permissions
                )
            except Exception as e:
                return self.error(f"Error querying broker {broker.name}: {e}")
            return self.success(
                data={
                    "obj_id": obj_id,
                    "broker_id": broker.id,
                    "neighbors": await label_neighbors(session, user, neighbors),
                }
            )
