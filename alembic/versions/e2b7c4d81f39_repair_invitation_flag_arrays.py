"""resize invitation flag arrays to match their groups

Editing an invitation's groups used to leave the per-group flag arrays at their
original length. Onboarding zips them against the groups strictly, so any
invitation edited that way raised on sign-in and locked the invitee out.

Revision ID: e2b7c4d81f39
Revises: a7c94e1d6b30
Create Date: 2026-08-25

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "e2b7c4d81f39"
down_revision = "a7c94e1d6b30"
branch_labels = None
depends_on = None

# Pad with false, or truncate, so each array is exactly one entry per group.
# New entries default to false: the safe direction for a permission flag.
RESIZE = """
UPDATE invitations AS i
SET {column} = (
    SELECT coalesce(
        array_agg(coalesce(i.{column}[n], false) ORDER BY n), ARRAY[]::boolean[]
    )
    FROM generate_series(1, g.group_count) AS n
)
FROM (
    SELECT invitation_id, count(*) AS group_count
    FROM group_invitations
    GROUP BY invitation_id
) AS g
WHERE g.invitation_id = i.id
  AND coalesce(array_length(i.{column}, 1), 0) <> g.group_count
"""

# An invitation with no groups at all should hold empty arrays, not stale ones.
CLEAR = """
UPDATE invitations
SET {column} = ARRAY[]::boolean[]
WHERE id NOT IN (SELECT invitation_id FROM group_invitations)
  AND coalesce(array_length({column}, 1), 0) <> 0
"""

COLUMNS = (
    "admin_for_groups",
    "can_save_to_groups",
    "can_share_photometry_for_groups",
)


def upgrade():
    for column in COLUMNS:
        op.execute(RESIZE.format(column=column))
        op.execute(CLEAR.format(column=column))


def downgrade():
    # The original lengths are not recoverable, and were the defect.
    pass
