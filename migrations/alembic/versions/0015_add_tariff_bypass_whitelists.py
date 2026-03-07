"""add bypass_whitelists to tariffs

Revision ID: 0015
Revises: 0014
Create Date: 2026-03-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Connection


revision: str = '0015'
down_revision: Union[str, None] = '0014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(conn: Connection, table_name: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :table_name)"
        ),
        {'table_name': table_name},
    )
    return bool(result.scalar())


def _has_column(conn: Connection, table_name: str, column_name: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :table_name AND column_name = :column_name)"
        ),
        {'table_name': table_name, 'column_name': column_name},
    )
    return bool(result.scalar())


def _get_column_udt_name(conn: Connection, table_name: str, column_name: str) -> str | None:
    result = conn.execute(
        sa.text(
            "SELECT udt_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :table_name AND column_name = :column_name"
        ),
        {'table_name': table_name, 'column_name': column_name},
    )
    return result.scalar()


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_table(conn, 'tariffs'):
        return

    if not _has_column(conn, 'tariffs', 'bypass_whitelists'):
        op.add_column(
            'tariffs',
            sa.Column(
                'bypass_whitelists',
                JSONB,
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
        )
        return

    column_udt_name = _get_column_udt_name(conn, 'tariffs', 'bypass_whitelists')
    if column_udt_name == 'json':
        empty_value = "'[]'::json"
    elif column_udt_name == 'jsonb':
        empty_value = "'[]'::jsonb"
    else:
        raise RuntimeError(f'Unsupported tariffs.bypass_whitelists type: {column_udt_name}')

    op.execute(sa.text(f'UPDATE tariffs SET bypass_whitelists = {empty_value} WHERE bypass_whitelists IS NULL'))
    op.execute(sa.text(f'ALTER TABLE tariffs ALTER COLUMN bypass_whitelists SET DEFAULT {empty_value}'))
    op.execute(sa.text('ALTER TABLE tariffs ALTER COLUMN bypass_whitelists SET NOT NULL'))


def downgrade() -> None:
    conn = op.get_bind()

    if _has_table(conn, 'tariffs') and _has_column(conn, 'tariffs', 'bypass_whitelists'):
        op.drop_column('tariffs', 'bypass_whitelists')
