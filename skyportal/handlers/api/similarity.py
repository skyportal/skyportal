import datetime
from typing import Annotated

from astropy.time import Time
from pydantic import Field
from skyportal_py_models.similarity import (
    MoreLikeThisPostBody,
    MoreLikeThisResponse,
    SimilarityVettingGetQuery,
    SimilarityVettingResponse,
    SimilarSourcesGetQuery,
    SimilarSourcesResponse,
)

from baselayer.app.access import auth_or_token

from ...models import Obj
from ...utils.naive_datetime import utcnow_naive
from ...utils.similarity import (
    classified_as,
    find_neighbors,
    label_neighbors,
    more_like_this,
    similarity_broker,
    vetting_queue,
)
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


class SimilarityVettingHandler(BaseHandler):
    @auth_or_token
    async def get(
        self, *, query: SimilarityVettingGetQuery = None
    ) -> SimilarityVettingResponse:
        """
        ---
        summary: Get the neighbor vetting queue
        description: Sources a person classified recently whose human-classified
          neighbors in a broker's embedding space mostly belong to another
          branch of the taxonomy. Machine classifications are ignored on both
          sides. A subclass agrees with its parent class (SN Ia-91T with SN Ia).
        tags:
          - sources
          - classifications
        """
        query = self.parse_query(SimilarityVettingGetQuery)
        since = utcnow_naive() - datetime.timedelta(days=query.days)
        async with self.AsyncSession() as session:
            user = session.user_or_token
            broker = await similarity_broker(session, user, query.brokerId)
            if broker is None:
                return self.error("No active broker serves similarity search")
            permissions = await alert_permissions_async(self.current_user, session)
            checked, items = await vetting_queue(
                session,
                user,
                broker,
                permissions,
                since,
                query.topK,
                query.minLabeled,
                query.maxAgreement,
                query.groupIds,
            )
            return self.success(
                data={"broker_id": broker.id, "checked": checked, "items": items}
            )


class MoreLikeThisHandler(BaseHandler):
    @auth_or_token
    async def post(self, *, body: MoreLikeThisPostBody = None) -> MoreLikeThisResponse:
        """
        ---
        summary: Find objects like a set of sources
        description: Objects near any of the seed sources in a broker's
          embedding space, with a recent embedding and no human classification,
          ranked by how many seeds they are near. Seeds are the given objects,
          or every source a person gave one of the given classes, optionally
          only those saved to the given groups. Seeds older than the broker's
          embeddings have no neighbors.
        tags:
          - sources
          - classifications
        """
        body = self.parse_body(MoreLikeThisPostBody)
        if not body.objIds and not body.classifications:
            return self.error("Provide objIds or classifications")
        min_jd = Time(utcnow_naive()).jd - body.days
        async with self.AsyncSession() as session:
            user = session.user_or_token
            broker = await similarity_broker(session, user, body.brokerId)
            if broker is None:
                return self.error("No active broker serves similarity search")
            if body.objIds:
                seed_ids = list(
                    await session.scalars(
                        Obj.select(user, columns=[Obj.id]).where(
                            Obj.id.in_(body.objIds)
                        )
                    )
                )
            else:
                seed_ids = await classified_as(
                    session, user, body.classifications, body.groupIds
                )
            permissions = await alert_permissions_async(self.current_user, session)
            searched, items = await more_like_this(
                session,
                user,
                broker,
                permissions,
                seed_ids,
                min_jd,
                body.topK,
                body.limit,
            )
            return self.success(
                data={
                    "broker_id": broker.id,
                    "seeds": len(seed_ids),
                    "seeds_searched": searched,
                    "items": items,
                }
            )
