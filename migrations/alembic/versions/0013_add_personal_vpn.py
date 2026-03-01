"""add personal vpn tables

Revision ID: 0013
Revises: 0012
Create Date: 2026-03-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection


revision: str = '0013'
down_revision: Union[str, None] = '0012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(conn: Connection, table_name: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :name)"
        ),
        {'name': table_name},
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

    if not _has_table(conn, 'personal_vpn_instances'):
        op.create_table(
            'personal_vpn_instances',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('owner_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('remnawave_node_id', sa.String(length=255), nullable=False),
            sa.Column('remnawave_squad_id', sa.String(length=255), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
            sa.Column('max_users', sa.Integer(), nullable=False, server_default=sa.text('1')),
            sa.Column('last_restart_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint('owner_user_id', name='uq_personal_vpn_instances_owner_user_id'),
        )

    if not _has_index(conn, 'ix_personal_vpn_instances_owner_user_id'):
        op.create_index('ix_personal_vpn_instances_owner_user_id', 'personal_vpn_instances', ['owner_user_id'])

    if not _has_table(conn, 'personal_vpn_users'):
        op.create_table(
            'personal_vpn_users',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column(
                'instance_id',
                sa.Integer(),
                sa.ForeignKey('personal_vpn_instances.id', ondelete='CASCADE'),
                nullable=False,
            ),
            sa.Column('remnawave_user_id', sa.String(length=255), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('device_limit', sa.Integer(), nullable=False, server_default=sa.text('1')),
            sa.Column('traffic_limit_bytes', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
            sa.Column('subscription_link', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint(
                'instance_id',
                'remnawave_user_id',
                name='uq_personal_vpn_users_instance_remnawave_user',
            ),
        )

    if not _has_index(conn, 'ix_personal_vpn_users_instance_deleted'):
        op.create_index('ix_personal_vpn_users_instance_deleted', 'personal_vpn_users', ['instance_id', 'deleted_at'])


def downgrade() -> None:
    conn = op.get_bind()

    if _has_table(conn, 'personal_vpn_users'):
        if _has_index(conn, 'ix_personal_vpn_users_instance_deleted'):
            op.drop_index('ix_personal_vpn_users_instance_deleted', table_name='personal_vpn_users')
        op.drop_table('personal_vpn_users')

    if _has_table(conn, 'personal_vpn_instances'):
        if _has_index(conn, 'ix_personal_vpn_instances_owner_user_id'):
            op.drop_index('ix_personal_vpn_instances_owner_user_id', table_name='personal_vpn_instances')
        op.drop_table('personal_vpn_instances')

