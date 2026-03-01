"""fix family invite uniqueness to pending status only

Revision ID: 0014
Revises: 0013
Create Date: 2026-03-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection


revision: str = '0014'
down_revision: Union[str, None] = '0013'
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


def _has_constraint(conn: Connection, constraint_name: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM pg_constraint "
            "WHERE conname = :constraint_name)"
        ),
        {'constraint_name': constraint_name},
    )
    return bool(result.scalar())


def _has_index(conn: Connection, index_name: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM pg_indexes "
            "WHERE schemaname = 'public' AND indexname = :index_name)"
        ),
        {'index_name': index_name},
    )
    return bool(result.scalar())


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_table(conn, 'family_invites'):
        return

    if _has_constraint(conn, 'uq_family_invites_pending_tuple'):
        op.drop_constraint('uq_family_invites_pending_tuple', 'family_invites', type_='unique')

    if not _has_index(conn, 'uq_family_invites_pending_tuple'):
        op.create_index(
            'uq_family_invites_pending_tuple',
            'family_invites',
            ['family_group_id', 'invitee_user_id'],
            unique=True,
            postgresql_where=sa.text("status = 'pending'"),
        )


def downgrade() -> None:
    conn = op.get_bind()

    if not _has_table(conn, 'family_invites'):
        return

    if _has_index(conn, 'uq_family_invites_pending_tuple'):
        op.drop_index('uq_family_invites_pending_tuple', table_name='family_invites')

    if not _has_constraint(conn, 'uq_family_invites_pending_tuple'):
        op.create_unique_constraint(
            'uq_family_invites_pending_tuple',
            'family_invites',
            ['family_group_id', 'invitee_user_id', 'status'],
        )
