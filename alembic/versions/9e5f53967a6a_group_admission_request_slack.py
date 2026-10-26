"""Keep Slack group admission request notifications for current users

Revision ID: 9e5f53967a6a
Revises: e7f3b9d21a08
Create Date: 2026-10-25 13:00:00.000000

"""

from alembic import op

revision = "9e5f53967a6a"
down_revision = "e7f3b9d21a08"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        UPDATE users
        SET preferences = jsonb_set(
            preferences,
            '{notifications,group_admission_request}',
            '{"slack": {"active": true}}'::jsonb
        )
        WHERE preferences -> 'slack_integration' ->> 'active' = 'true'
        AND jsonb_typeof(preferences -> 'notifications') = 'object'
        AND preferences -> 'notifications' <> '{}'::jsonb
        AND NOT (preferences -> 'notifications' ? 'group_admission_request')
        """
    )


def downgrade():
    op.execute(
        """
        UPDATE users
        SET preferences = preferences #- '{notifications,group_admission_request}'
        WHERE preferences -> 'notifications' ? 'group_admission_request'
        """
    )
