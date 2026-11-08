"""Named quick save buttons

Revision ID: e7a41c9d2b58
Revises: e5b1d7c3a920
Create Date: 2026-11-06 00:00:00.000000

"""

from alembic import op

revision = "e7a41c9d2b58"
down_revision = "e5b1d7c3a920"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        UPDATE users
        SET preferences = (preferences - 'quicksave_group_ids') || jsonb_build_object(
            'quickSaveButtons',
            jsonb_build_object('Quick Save', preferences -> 'quicksave_group_ids')
        )
        WHERE jsonb_typeof(preferences -> 'quicksave_group_ids') = 'array'
        AND jsonb_array_length(preferences -> 'quicksave_group_ids') > 0
        """
    )
    op.execute(
        """
        UPDATE users
        SET preferences = preferences - 'quicksave_group_ids'
        WHERE preferences ? 'quicksave_group_ids'
        """
    )


def downgrade():
    op.execute(
        """
        UPDATE users
        SET preferences = (preferences - 'quickSaveButtons') || jsonb_build_object(
            'quicksave_group_ids',
            (
                SELECT jsonb_agg(DISTINCT group_id)
                FROM jsonb_each(preferences -> 'quickSaveButtons') AS button,
                jsonb_array_elements(button.value) AS group_id
            )
        )
        WHERE jsonb_typeof(preferences -> 'quickSaveButtons') = 'object'
        AND preferences -> 'quickSaveButtons' <> '{}'::jsonb
        """
    )
    op.execute(
        """
        UPDATE users
        SET preferences = preferences - 'quickSaveButtons'
        WHERE preferences ? 'quickSaveButtons'
        """
    )
