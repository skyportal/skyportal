"""order invitation flag arrays by group id

Revision ID: fc2e1adbcf93
Revises: e3c8a7b45d19
Create Date: 2026-10-30

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "fc2e1adbcf93"
down_revision = "e3c8a7b45d19"
branch_labels = None
depends_on = None

REORDER = """
UPDATE invitations AS i
SET admin_for_groups = r.admin_for_groups,
    can_save_to_groups = r.can_save_to_groups,
    can_share_photometry_for_groups = r.can_share_photometry_for_groups
FROM (
    SELECT
        g.invitation_id,
        array_agg(coalesce(inv.admin_for_groups[g.position], false) ORDER BY g.group_id)
            AS admin_for_groups,
        array_agg(coalesce(inv.can_save_to_groups[g.position], false) ORDER BY g.group_id)
            AS can_save_to_groups,
        array_agg(
            coalesce(inv.can_share_photometry_for_groups[g.position], false)
            ORDER BY g.group_id
        ) AS can_share_photometry_for_groups
    FROM (
        SELECT
            invitation_id,
            group_id,
            (row_number() OVER (PARTITION BY invitation_id ORDER BY id))::int AS position
        FROM group_invitations
    ) AS g
    JOIN invitations AS inv ON inv.id = g.invitation_id
    GROUP BY g.invitation_id
    HAVING count(*) > 1
) AS r
WHERE r.invitation_id = i.id
"""


def upgrade():
    op.execute(REORDER)


def downgrade():
    pass
