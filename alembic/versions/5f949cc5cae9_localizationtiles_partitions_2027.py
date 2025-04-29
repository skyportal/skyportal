"""localizationtiles_partitions_2027

Revision ID: 5f949cc5cae9
Revises: 7eab209f29d3
Create Date: 2025-04-29 14:31:17.934329

"""

import datetime

from dateutil.relativedelta import relativedelta

from alembic import op

# revision identifiers, used by Alembic.
revision = "5f949cc5cae9"
down_revision = "7eab209f29d3"
branch_labels = None
depends_on = None


def upgrade():
    for year in range(2025, 2028):
        for month in range(1 if year != 2025 else 5, 13):
            date = datetime.date(year, month, 1)
            partition_name = f"localizationtiles_{date.strftime('%Y_%m')}"
            lower_bound = date.strftime("%Y-%m-%d")
            upper_bound = (date + relativedelta(months=1)).strftime("%Y-%m-%d")
            op.execute(
                f"CREATE TABLE {partition_name} PARTITION OF localizationtiles FOR VALUES FROM ('{lower_bound}') TO ('{upper_bound}')"
            )
            op.execute(
                f"ALTER TABLE {partition_name} RENAME CONSTRAINT localizationtiles_localization_id_fkey TO {partition_name}_localization_id_fkey"
            )
            op.execute(
                f"CREATE SEQUENCE {partition_name}_id_seq START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1"
            )
            op.execute(
                f"ALTER SEQUENCE {partition_name}_id_seq OWNED BY {partition_name}.id"
            )


def downgrade():
    for year in range(2025, 2028):
        for month in range(1 if year != 2025 else 5, 13):
            date = datetime.date(year, month, 1)
            partition_name = f"localizationtiles_{date.strftime('%Y_%m')}"
            op.execute(
                f"INSERT INTO localizationtiles_def(localization_id, probdensity, healpix, created_at, modified, dateobs) SELECT localization_id, probdensity, healpix, created_at, modified, dateobs FROM {partition_name}"
            )
            op.execute(f"DROP TABLE {partition_name}")
