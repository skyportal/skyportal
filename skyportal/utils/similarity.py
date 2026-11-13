"""Nearest neighbors in a broker's embedding space, labeled from SkyPortal."""

import sqlalchemy as sa
from tornado.ioloop import IOLoop

from ..models import Broker, Classification, Obj


async def similarity_broker(session, user, broker_id=None):
    """The broker to search: ``broker_id`` if given, else the first active one
    whose provider serves similarity search."""
    stmt = Broker.select(user).where(Broker.active.is_(True)).order_by(Broker.id)
    if broker_id is not None:
        stmt = stmt.where(Broker.id == broker_id)
    brokers = (await session.scalars(stmt)).all()
    return next(
        (b for b in brokers if b.broker_class.implements()["similar_objects"]), None
    )


async def find_neighbors(broker, obj_id, top_k, permissions):
    return await IOLoop.current().run_in_executor(
        None,
        lambda: broker.broker_class.similar_objects(
            broker, obj_id, None, top_k=top_k, permissions=permissions
        ),
    )


async def human_classifications(session, user, obj_ids):
    """The most recent positive human classification of each object."""
    if not obj_ids:
        return {}
    rows = await session.scalars(
        Classification.select(user)
        .where(
            Classification.obj_id.in_(obj_ids),
            Classification.ml.is_(False),
            sa.or_(
                Classification.probability.is_(None), Classification.probability > 0
            ),
        )
        .order_by(Classification.created_at.desc())
    )
    latest = {}
    for classification in rows:
        latest.setdefault(classification.obj_id, classification)
    return latest


async def label_neighbors(session, user, neighbors):
    """Add what the requester can read here (redshift, human classification)
    to each neighbor the broker returned."""
    obj_ids = [n["object_id"] for n in neighbors]
    objs = {
        obj.id: obj
        for obj in (
            await session.scalars(Obj.select(user).where(Obj.id.in_(obj_ids)))
        ).all()
    }
    classifications = await human_classifications(session, user, list(objs))
    labeled = []
    for neighbor in neighbors:
        obj = objs.get(neighbor["object_id"])
        classification = classifications.get(neighbor["object_id"])
        labeled.append(
            {
                "obj_id": neighbor["object_id"],
                "score": neighbor["score"],
                "jd": neighbor.get("jd"),
                "model_label": neighbor.get("model_label"),
                "model_probability": neighbor.get("model_probability"),
                "in_skyportal": obj is not None,
                "redshift": obj.redshift if obj is not None else None,
                "classification": {
                    "classification": classification.classification,
                    "probability": classification.probability,
                    "taxonomy_id": classification.taxonomy_id,
                }
                if classification is not None
                else None,
            }
        )
    return labeled
