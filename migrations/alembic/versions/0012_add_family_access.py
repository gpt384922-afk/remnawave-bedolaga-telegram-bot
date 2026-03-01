"""add family access tables and tariff settings

Revision ID: 0012
Revises: 0011
Create Date: 2026-03-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection


revision: str = '0012'
down_revision: Union[str, None] = '0011'
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



def _has_column(conn: Connection, table_name: str, column_name: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :table_name AND column_name = :column_name)"
        ),
        {'table_name': table_name, 'column_name': column_name},
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

    if not _has_column(conn, 'tariffs', 'family_enabled'):
        op.add_column(
            'tariffs',
            sa.Column('family_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        )

    if not _has_column(conn, 'tariffs', 'family_max_members'):
        op.add_column(
            'tariffs',
            sa.Column('family_max_members', sa.Integer(), nullable=False, server_default=sa.text('0')),
        )

    if not _has_index(conn, 'ix_users_username'):
        op.create_index('ix_users_username', 'users', ['username'])

    if not _has_table(conn, 'family_groups'):
        op.create_table(
            'family_groups',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('owner_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column(
                'subscription_id',
                sa.Integer(),
                sa.ForeignKey('subscriptions.id', ondelete='CASCADE'),
                nullable=False,
            ),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint('owner_user_id', name='uq_family_groups_owner_user_id'),
            sa.UniqueConstraint('subscription_id', name='uq_family_groups_subscription_id'),
        )

    if not _has_table(conn, 'family_members'):
        op.create_table(
            'family_members',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column(
                'family_group_id',
                sa.Integer(),
                sa.ForeignKey('family_groups.id', ondelete='CASCADE'),
                nullable=False,
            ),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('role', sa.String(length=20), nullable=False, server_default='member'),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='invited'),
            sa.Column('invited_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('invited_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('removed_at', sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint('family_group_id', 'user_id', name='uq_family_members_group_user'),
        )
        op.create_index('ix_family_members_user_status', 'family_members', ['user_id', 'status'])

    if not _has_table(conn, 'family_invites'):
        op.create_table(
            'family_invites',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column(
                'family_group_id',
                sa.Integer(),
                sa.ForeignKey('family_groups.id', ondelete='CASCADE'),
                nullable=False,
            ),
            sa.Column('invitee_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('inviter_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('token', sa.String(length=128), nullable=True, unique=True),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint(
                'family_group_id',
                'invitee_user_id',
                'status',
                name='uq_family_invites_pending_tuple',
            ),
        )
        op.create_index('ix_family_invites_invitee_status', 'family_invites', ['invitee_user_id', 'status'])

    if not _has_table(conn, 'family_devices'):
        op.create_table(
            'family_devices',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column(
                'family_group_id',
                sa.Integer(),
                sa.ForeignKey('family_groups.id', ondelete='CASCADE'),
                nullable=False,
            ),
            sa.Column('hwid', sa.String(length=255), nullable=False),
            sa.Column('owner_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column(
                'subscription_user_id',
                sa.Integer(),
                sa.ForeignKey('users.id', ondelete='SET NULL'),
                nullable=True,
            ),
            sa.Column('platform', sa.String(length=100), nullable=True),
            sa.Column('device_model', sa.String(length=255), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint('family_group_id', 'hwid', name='uq_family_devices_group_hwid'),
        )
        op.create_index('ix_family_devices_owner', 'family_devices', ['owner_user_id'])

    if not _has_table(conn, 'user_notifications'):
        op.create_table(
            'user_notifications',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('notification_type', sa.String(length=50), nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('body', sa.Text(), nullable=True),
            sa.Column('payload', sa.JSON(), nullable=True, server_default=sa.text("'{}'::json")),
            sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index('ix_user_notifications_user_read', 'user_notifications', ['user_id', 'read_at'])



def downgrade() -> None:
    conn = op.get_bind()

    if _has_table(conn, 'user_notifications'):
        if _has_index(conn, 'ix_user_notifications_user_read'):
            op.drop_index('ix_user_notifications_user_read', table_name='user_notifications')
        op.drop_table('user_notifications')

    if _has_table(conn, 'family_devices'):
        if _has_index(conn, 'ix_family_devices_owner'):
            op.drop_index('ix_family_devices_owner', table_name='family_devices')
        op.drop_table('family_devices')

    if _has_table(conn, 'family_invites'):
        if _has_index(conn, 'ix_family_invites_invitee_status'):
            op.drop_index('ix_family_invites_invitee_status', table_name='family_invites')
        op.drop_table('family_invites')

    if _has_table(conn, 'family_members'):
        if _has_index(conn, 'ix_family_members_user_status'):
            op.drop_index('ix_family_members_user_status', table_name='family_members')
        op.drop_table('family_members')

    if _has_table(conn, 'family_groups'):
        op.drop_table('family_groups')

    if _has_index(conn, 'ix_users_username'):
        op.drop_index('ix_users_username', table_name='users')

    if _has_column(conn, 'tariffs', 'family_max_members'):
        op.drop_column('tariffs', 'family_max_members')

    if _has_column(conn, 'tariffs', 'family_enabled'):
        op.drop_column('tariffs', 'family_enabled')
