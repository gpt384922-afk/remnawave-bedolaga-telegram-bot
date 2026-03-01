from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import personal_vpn_service


async def test_create_sub_user_fails_when_max_users_reached(monkeypatch):
    instance = SimpleNamespace(
        id=11,
        owner_user_id=1,
        status='active',
        expires_at=datetime.now(UTC) + timedelta(days=5),
        max_users=2,
    )

    monkeypatch.setattr(personal_vpn_service, '_get_instance_for_owner', AsyncMock(return_value=instance))
    monkeypatch.setattr(personal_vpn_service, '_get_active_user_count', AsyncMock(return_value=2))

    db = AsyncMock(spec=AsyncSession)
    user = SimpleNamespace(id=1)

    with pytest.raises(HTTPException) as exc:
        await personal_vpn_service.create_personal_vpn_sub_user(
            db,
            user,
            expires_at=datetime.now(UTC) + timedelta(days=1),
            device_limit=1,
            traffic_limit_gb=10,
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == 'Max sub-users limit reached'


async def test_create_sub_user_fails_when_expiration_exceeds_instance(monkeypatch):
    instance = SimpleNamespace(
        id=22,
        owner_user_id=1,
        status='active',
        expires_at=datetime.now(UTC) + timedelta(days=1),
        max_users=5,
    )

    monkeypatch.setattr(personal_vpn_service, '_get_instance_for_owner', AsyncMock(return_value=instance))
    monkeypatch.setattr(personal_vpn_service, '_get_active_user_count', AsyncMock(return_value=0))

    db = AsyncMock(spec=AsyncSession)
    user = SimpleNamespace(id=1)

    with pytest.raises(HTTPException) as exc:
        await personal_vpn_service.create_personal_vpn_sub_user(
            db,
            user,
            expires_at=datetime.now(UTC) + timedelta(days=2),
            device_limit=1,
            traffic_limit_gb=10,
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == 'Sub-user expiration cannot exceed personal VPN expiration'


async def test_restart_rate_limit(monkeypatch):
    instance = SimpleNamespace(
        id=33,
        owner_user_id=1,
        status='active',
        expires_at=datetime.now(UTC) + timedelta(days=5),
        last_restart_at=datetime.now(UTC) - timedelta(minutes=3),
    )

    monkeypatch.setattr(personal_vpn_service, '_get_instance_for_owner', AsyncMock(return_value=instance))

    db = AsyncMock(spec=AsyncSession)
    user = SimpleNamespace(id=1)

    with pytest.raises(HTTPException) as exc:
        await personal_vpn_service.restart_personal_vpn_node(db, user)

    assert exc.value.status_code == 429
    assert exc.value.detail == 'Перезапуск доступен раз в 10 минут'


async def test_overview_is_isolated_from_subscription_logic(monkeypatch):
    monkeypatch.setattr(personal_vpn_service, '_get_instance_for_owner', AsyncMock(return_value=None))

    db = AsyncMock(spec=AsyncSession)
    # User intentionally has no subscription-related fields.
    user = SimpleNamespace(id=123)

    result = await personal_vpn_service.get_personal_vpn_overview(db, user)

    assert result == {'has_instance': False}


async def test_admin_assign_conflict_returns_409(monkeypatch):
    owner = SimpleNamespace(id=777)
    existing = SimpleNamespace(id=1, owner_user_id=owner.id)

    resolve_owner = AsyncMock(return_value=owner)
    get_instance = AsyncMock(return_value=existing)
    validate = AsyncMock()

    monkeypatch.setattr(personal_vpn_service, '_resolve_owner_user', resolve_owner)
    monkeypatch.setattr(personal_vpn_service, '_get_instance_for_owner', get_instance)
    monkeypatch.setattr(personal_vpn_service, '_validate_node_and_squad', validate)

    db = AsyncMock(spec=AsyncSession)

    with pytest.raises(HTTPException) as exc:
        await personal_vpn_service.assign_personal_vpn_instance(
            db,
            owner_user_id=owner.id,
            owner_username=None,
            owner_telegram_id=None,
            remnawave_node_id='node-1',
            remnawave_squad_id='squad-1',
            expires_at=datetime.now(UTC) + timedelta(days=30),
            max_users=3,
        )

    assert exc.value.status_code == 409
    validate.assert_not_awaited()

