"""sync legacy tariff columns

Revision ID: 0016
Revises: 0015
Create Date: 2026-03-07 14:20:00.000000
"""

from typing import Final

import sqlalchemy as sa
from alembic import op


revision: str = '0016'
down_revision: str | None = '0015'
branch_labels: str | None = None
depends_on: str | None = None

TARIFFS_TABLE: Final[str] = 'tariffs'


def _has_table(bind: sa.engine.Connection, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _has_column(bind: sa.engine.Connection, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(column['name'] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_table(bind, TARIFFS_TABLE):
        return

    if not _has_column(bind, TARIFFS_TABLE, 'external_squad_uuid'):
        op.add_column(TARIFFS_TABLE, sa.Column('external_squad_uuid', sa.String(length=255), nullable=True))

    if not _has_column(bind, TARIFFS_TABLE, 'max_shared_members'):
        op.add_column(
            TARIFFS_TABLE,
            sa.Column('max_shared_members', sa.Integer(), nullable=False, server_default=sa.text('0')),
        )
        return

    op.execute(sa.text('UPDATE tariffs SET max_shared_members = 0 WHERE max_shared_members IS NULL'))
    op.execute(sa.text('ALTER TABLE tariffs ALTER COLUMN max_shared_members SET DEFAULT 0'))
    op.execute(sa.text('ALTER TABLE tariffs ALTER COLUMN max_shared_members SET NOT NULL'))


def downgrade() -> None:
    bind = op.get_bind()

    if not _has_table(bind, TARIFFS_TABLE):
        return

    if _has_column(bind, TARIFFS_TABLE, 'max_shared_members'):
        op.drop_column(TARIFFS_TABLE, 'max_shared_members')

    if _has_column(bind, TARIFFS_TABLE, 'external_squad_uuid'):
        op.drop_column(TARIFFS_TABLE, 'external_squad_uuid')
