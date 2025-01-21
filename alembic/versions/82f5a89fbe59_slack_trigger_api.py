"""slack trigger api

Revision ID: 82f5a89fbe59
Revises: d61a8bea7313
Create Date: 2022-01-26 21:06:14.272254

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "82f5a89fbe59"
down_revision = "aea51b4ff0b0"
branch_labels = None
depends_on = None


def upgrade():
    # add SLACKAPI to followup_apis
    # with op.get_context().autocommit_block():
    #     op.execute("ALTER TYPE followup_apis ADD VALUE IF NOT EXISTS 'SLACKAPI'")

    op.execute(
        """
alter type "public"."followup_apis" rename to "followup_apis__old_version_to_be_dropped";

create type "public"."followup_apis" as enum ('KAITAPI', 'SEDMAPI', 'SEDMV2API', 'IOOAPI', 'IOIAPI', 'SPRATAPI', 'SINISTROAPI', 'SPECTRALAPI', 'FLOYDSAPI', 'MUSCATAPI', 'SLACKAPI', 'ZTFAPI');

alter table "public"."instruments" alter column api_classname type "public"."followup_apis" using api_classname::text::"public"."followup_apis";

drop type "public"."followup_apis__old_version_to_be_dropped";
"""
    )


def downgrade():
    # Values should only be added and never removed from ENUM types in order to
    # avoid having to delete relevant data.
    pass
