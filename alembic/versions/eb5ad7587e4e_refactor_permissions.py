"""refactor  permissions

Revision ID: eb5ad7587e4e
Revises: 2a17ca9d5438
Create Date: 2020-12-07 20:02:36.221787

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'eb5ad7587e4e'
down_revision = '2a17ca9d5438'
branch_labels = None
depends_on = None

# This migration adds an integer primary key to the join tables

tables = [
    'group_annotations',
    'group_classifications',
    'group_comments',
    'group_invitations',
    'group_notifications',
    'group_photometry',
    'group_spectra',
    'group_streams',
    'group_taxonomy',
    'group_users',
    'request_groups',
    'role_acls',
    'sources',
    'spectrum_observers',
    'spectrum_reducers',
    'stream_invitations',
    'stream_users',
    'token_acls',
    'user_acls',
    'user_invitations',
    'user_roles',
]

columns = [
    ['group_id', 'annotation_id'],
    ['group_id', 'classification_id'],
    ['group_id', 'comment_id'],
    ['group_id', 'invitation_id'],
    ['group_id', 'sourcenotification_id'],
    ['group_id', 'photometr_id'],
    ['group_id', 'spectr_id'],
    ['group_id', 'stream_id'],
    ['group_id', 'taxonomie_id'],
    ['group_id', 'user_id'],
    ['followuprequest_id', 'group_id'],
    ['role_id', 'acl_id'],
    ['group_id', 'obj_id'],
    ['spectr_id', 'user_id'],
    ['spectr_id', 'user_id'],
    ['stream_id', 'invitation_id'],
    ['stream_id', 'user_id'],
    ['token_id', 'acl_id'],
    ['user_id', 'acl_id'],
    ['user_id', 'invitation_id'],
    ['user_id', 'role_id'],
]


def upgrade():
    # add an integer primary key to the join tables this primary key is not
    # used anywhere as a foreign key so is safe to delete on schema downgrade

    for table, colpair in zip(tables, columns):
        op.execute(f'ALTER TABLE {table} DROP CONSTRAINT "{table}_pkey"')
        op.add_column(table, sa.Column('id', sa.Integer, primary_key=True))
        op.create_index(f'{table}_forward_ind', table, colpair, unique=True)


def downgrade():
    # restore a composite 2-column primary key to the join tables
    for table, colpair in zip(tables, columns):
        op.drop_index(f'{table}_forward_ind')
        op.drop_column(table, 'id')
        op.create_primary_key(f'{table}_pkey', table, colpair)
