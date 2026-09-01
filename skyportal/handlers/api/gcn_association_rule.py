import sqlalchemy as sa
from skyportal_py_models.gcn_events import GcnAssociationRuleBody

from baselayer.app.access import auth_or_token

from ...enum_types import MMA_DETECTOR_TYPES
from ...models import GcnAssociationRule, Group
from ..base import BaseHandler


class GcnAssociationRuleHandler(BaseHandler):
    @auth_or_token
    async def get(self, rule_id=None):
        """
        ---
        summary: Get the association rules you can see
        description: |
          The cuts your groups apply to event-to-event associations, one per
          pair of messengers per group.
        tags:
          - gcn events
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        async with self.AsyncSession() as session:
            # the policy is group membership, so no further scoping here
            stmt = GcnAssociationRule.select(session.user_or_token)
            if rule_id is not None:
                rule = await session.scalar(
                    stmt.where(GcnAssociationRule.id == int(rule_id))
                )
                if rule is None:
                    return self.error("Rule not found", status=404)
                return self.success(data=rule)
            rules = (await session.scalars(stmt)).unique().all()
            return self.success(data=rules)

    @auth_or_token
    async def post(self, rule_id=None, *, body: GcnAssociationRuleBody = None):
        """
        ---
        summary: Create or update an association rule
        description: |
          Sets your cut for one pair of messengers; posting the same pair again
          replaces it.
        tags:
          - gcn events
        requestBody:
          content:
            application/json:
              schema: Success
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
        body = self.parse_body(GcnAssociationRuleBody)
        for messenger in (body.detector_type_1, body.detector_type_2):
            if messenger not in MMA_DETECTOR_TYPES:
                return self.error(
                    f"detector type must be one of {', '.join(MMA_DETECTOR_TYPES)}"
                )
        if body.days <= 0:
            return self.error("days must be positive")
        if not 0.0 <= body.min_consistency <= 1.0:
            return self.error("min_consistency must be between 0 and 1")

        # stored sorted, so a rule is one row however it was entered; the tag
        # lists travel with their messenger
        pairs = sorted(
            [
                (body.detector_type_1, list(body.tags_1)),
                (body.detector_type_2, list(body.tags_2)),
            ],
            key=lambda pair: pair[0],
        )
        (type_1, tags_1), (type_2, tags_2) = pairs

        async with self.AsyncSession() as session:
            group = await session.scalar(
                Group.select(session.user_or_token).where(Group.id == body.group_id)
            )
            if group is None:
                return self.error(
                    "Group not found, or you are not a member of it", status=403
                )

            rule = await session.scalar(
                GcnAssociationRule.select(session.user_or_token, mode="update").where(
                    GcnAssociationRule.group_id == body.group_id,
                    GcnAssociationRule.detector_type_1 == type_1,
                    GcnAssociationRule.detector_type_2 == type_2,
                )
            )
            if rule is None:
                rule = GcnAssociationRule(
                    group_id=body.group_id,
                    detector_type_1=type_1,
                    detector_type_2=type_2,
                    tags_1=tags_1,
                    tags_2=tags_2,
                    days=body.days,
                    min_consistency=body.min_consistency,
                )
                session.add(rule)
            else:
                rule.tags_1 = tags_1
                rule.tags_2 = tags_2
                rule.days = body.days
                rule.min_consistency = body.min_consistency
            await session.commit()

            self.push_all(action="skyportal/REFRESH_GCN_ASSOCIATION_RULES")
            return self.success(data={"id": rule.id})

    @auth_or_token
    async def delete(self, rule_id):
        """
        ---
        summary: Delete an association rule
        description: Removes one of your cuts.
        tags:
          - gcn events
        parameters:
          - in: path
            name: rule_id
            required: true
            schema:
              type: integer
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
        async with self.AsyncSession() as session:
            rule = await session.scalar(
                GcnAssociationRule.select(session.user_or_token, mode="delete").where(
                    GcnAssociationRule.id == int(rule_id),
                )
            )
            if rule is None:
                return self.error("Rule not found", status=404)
            await session.execute(
                sa.delete(GcnAssociationRule).where(GcnAssociationRule.id == rule.id)
            )
            await session.commit()

            self.push_all(action="skyportal/REFRESH_GCN_ASSOCIATION_RULES")
            return self.success()
