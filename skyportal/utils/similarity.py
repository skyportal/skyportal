"""Nearest neighbors in a broker's embedding space, labeled from SkyPortal."""

import asyncio
from collections import Counter

import sqlalchemy as sa
from tornado.ioloop import IOLoop

from baselayer.log import make_log

from ..models import Broker, Classification, Obj, Source, Taxonomy

log = make_log("similarity")

SEARCH_CONCURRENCY = 8


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


async def find_neighbors_many(broker, obj_ids, top_k, permissions):
    """Neighbors of each object; a failed search leaves that object out."""
    semaphore = asyncio.Semaphore(SEARCH_CONCURRENCY)

    async def search(obj_id):
        async with semaphore:
            try:
                return obj_id, await find_neighbors(broker, obj_id, top_k, permissions)
            except Exception as e:
                log(f"Similarity search failed for {obj_id}: {e}")
                return obj_id, None

    results = await asyncio.gather(*(search(obj_id) for obj_id in obj_ids))
    return {obj_id: hits for obj_id, hits in results if hits is not None}


def class_lineages(hierarchies):
    """Each class mapped to itself and its ancestors in the given taxonomies."""
    lineages = {}

    def walk(node, ancestors):
        name = node.get("class")
        path = [*ancestors, name] if name else ancestors
        if name:
            lineages.setdefault(name, set()).update(path)
        for subclass in node.get("subclasses") or []:
            walk(subclass, path)

    for hierarchy in hierarchies:
        walk(hierarchy, [])
    return lineages


def same_branch(a, b, lineages):
    """Whether one class is the other or one of its ancestors (Ia and Ia-91T)."""
    return a == b or a in lineages.get(b, ()) or b in lineages.get(a, ())


async def recently_classified(session, user, since, group_ids=None, limit=500):
    """Objects a person classified since ``since``, most recent first."""
    stmt = (
        Classification.select(user)
        .where(Classification.ml.is_(False), Classification.created_at >= since)
        .order_by(Classification.created_at.desc())
    )
    if group_ids:
        stmt = stmt.where(
            Classification.obj_id.in_(
                sa.select(Source.obj_id).where(
                    Source.group_id.in_(group_ids), Source.active.is_(True)
                )
            )
        )
    obj_ids = []
    for classification in await session.scalars(stmt):
        if classification.obj_id not in obj_ids:
            obj_ids.append(classification.obj_id)
            if len(obj_ids) >= limit:
                break
    return obj_ids


async def vetting_queue(
    session,
    user,
    broker,
    permissions,
    since,
    top_k,
    min_labeled,
    max_agreement,
    group_ids=None,
):
    """Recently classified sources whose human-classified neighbors mostly
    belong to another branch of the taxonomy, worst first."""
    seed_ids = await recently_classified(session, user, since, group_ids)
    seeds = await human_classifications(session, user, seed_ids)
    neighbors = await find_neighbors_many(broker, list(seeds), top_k, permissions)
    neighbor_ids = {n["object_id"] for hits in neighbors.values() for n in hits}
    labels = await human_classifications(session, user, list(neighbor_ids))
    taxonomy_ids = {c.taxonomy_id for c in [*seeds.values(), *labels.values()]}
    taxonomies = await session.scalars(
        Taxonomy.select(user).where(Taxonomy.id.in_(taxonomy_ids))
    )
    lineages = class_lineages([t.hierarchy for t in taxonomies])

    items = []
    for obj_id, hits in neighbors.items():
        seed = seeds[obj_id]
        classes = [
            labels[n["object_id"]].classification
            for n in hits
            if n["object_id"] in labels
        ]
        if len(classes) < min_labeled:
            continue
        agreement = sum(
            same_branch(seed.classification, c, lineages) for c in classes
        ) / len(classes)
        if agreement > max_agreement:
            continue
        items.append(
            {
                "obj_id": obj_id,
                "classification": seed.classification,
                "probability": seed.probability,
                "classified_at": seed.created_at.isoformat(),
                "labeled_neighbors": len(classes),
                "agreement": agreement,
                "neighbor_classes": dict(Counter(classes).most_common()),
            }
        )
    items.sort(key=lambda item: (item["agreement"], -item["labeled_neighbors"]))
    return len(neighbors), items


async def classified_as(session, user, classifications, group_ids=None, limit=1000):
    """Objects a person gave one of ``classifications``, most recent first."""
    stmt = (
        Classification.select(user)
        .where(
            Classification.ml.is_(False),
            Classification.classification.in_(classifications),
            sa.or_(
                Classification.probability.is_(None), Classification.probability > 0
            ),
        )
        .order_by(Classification.created_at.desc())
    )
    if group_ids:
        stmt = stmt.where(
            Classification.obj_id.in_(
                sa.select(Source.obj_id).where(
                    Source.group_id.in_(group_ids), Source.active.is_(True)
                )
            )
        )
    obj_ids = []
    for classification in await session.scalars(stmt):
        if classification.obj_id not in obj_ids:
            obj_ids.append(classification.obj_id)
            if len(obj_ids) >= limit:
                break
    return obj_ids


async def more_like_this(
    session, user, broker, permissions, seed_ids, min_jd, top_k, limit
):
    """Objects near the seeds with a recent embedding and no human
    classification, ranked by how many seeds they are near."""
    neighbors = await find_neighbors_many(broker, seed_ids, top_k, permissions)
    seeds = set(seed_ids)
    candidates = {}
    for seed_id, hits in neighbors.items():
        for hit in hits:
            if hit["object_id"] in seeds or (hit.get("jd") or 0) < min_jd:
                continue
            candidate = candidates.setdefault(
                hit["object_id"], {**hit, "seeds": 0, "nearest_seed": seed_id}
            )
            candidate["seeds"] += 1
            if hit["score"] > candidate["score"]:
                candidate.update(score=hit["score"], nearest_seed=seed_id)
    classified = await human_classifications(session, user, list(candidates))
    ranked = sorted(
        (c for obj_id, c in candidates.items() if obj_id not in classified),
        key=lambda c: (-c["seeds"], -c["score"]),
    )[:limit]
    labeled = await label_neighbors(session, user, ranked)
    items = [
        {
            "obj_id": item["obj_id"],
            "seeds": candidate["seeds"],
            "best_score": candidate["score"],
            "nearest_seed": candidate["nearest_seed"],
            "jd": item["jd"],
            "model_label": item["model_label"],
            "model_probability": item["model_probability"],
            "in_skyportal": item["in_skyportal"],
            "redshift": item["redshift"],
        }
        for item, candidate in zip(labeled, ranked)
    ]
    searched = sum(1 for hits in neighbors.values() if hits)
    return searched, items
