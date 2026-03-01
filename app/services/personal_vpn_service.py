from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud.user import get_user_by_id, get_user_by_telegram_id, get_user_by_username
from app.database.models import PersonalVPNInstance, PersonalVPNUser, User
from app.external.remnawave_api import TrafficLimitStrategy, UserStatus
from app.services.remnawave_service import RemnaWaveConfigurationError, RemnaWaveService


RESTART_COOLDOWN = timedelta(minutes=10)


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _instance_effective_status(instance: PersonalVPNInstance, now: datetime | None = None) -> str:
    current = now or _now_utc()
    status_value = (instance.status or 'active').lower()
    if status_value != 'active':
        return status_value
    expires_at = _ensure_aware(instance.expires_at)
    if current > expires_at:
        return 'expired'
    return 'active'


def _ensure_instance_actionable(instance: PersonalVPNInstance) -> None:
    if _instance_effective_status(instance) != 'active':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Personal VPN instance is not active',
        )


def _normalize_username(value: str) -> str:
    return value.strip().lstrip('@').lower()


async def _get_instance_for_owner(
    db: AsyncSession,
    owner_user_id: int,
    *,
    for_update: bool = False,
) -> PersonalVPNInstance | None:
    query = select(PersonalVPNInstance).where(PersonalVPNInstance.owner_user_id == owner_user_id)
    if for_update:
        query = query.with_for_update()
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def _get_active_user_count(db: AsyncSession, instance_id: int) -> int:
    result = await db.execute(
        select(func.count(PersonalVPNUser.id)).where(
            PersonalVPNUser.instance_id == instance_id,
            PersonalVPNUser.deleted_at.is_(None),
        )
    )
    return int(result.scalar() or 0)


def _get_remnawave_service() -> RemnaWaveService:
    service = RemnaWaveService()
    if not service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=service.configuration_error or 'RemnaWave API is not configured',
        )
    return service


async def _resolve_owner_user(
    db: AsyncSession,
    *,
    owner_user_id: int | None = None,
    owner_username: str | None = None,
    owner_telegram_id: int | None = None,
) -> User:
    owner: User | None = None

    if owner_user_id is not None:
        owner = await get_user_by_id(db, owner_user_id)
    elif owner_telegram_id is not None:
        owner = await get_user_by_telegram_id(db, owner_telegram_id)
    elif owner_username:
        owner = await get_user_by_username(db, _normalize_username(owner_username))

    if owner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Owner user not found')

    return owner


async def _validate_node_and_squad(*, node_id: str, squad_id: str) -> None:
    service = _get_remnawave_service()

    try:
        async with service.get_api_client() as api:
            node = await api.get_node_by_uuid(node_id)
            if node is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Node not found')

            squad = await api.get_internal_squad_by_uuid(squad_id)
            if squad is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Squad not found')
    except RemnaWaveConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )


async def list_available_nodes() -> list[dict]:
    service = _get_remnawave_service()
    return await service.get_all_nodes()


async def list_squads() -> list[dict]:
    service = _get_remnawave_service()
    return await service.get_all_squads()


async def assign_personal_vpn_instance(
    db: AsyncSession,
    *,
    owner_user_id: int | None,
    owner_username: str | None,
    owner_telegram_id: int | None,
    remnawave_node_id: str,
    remnawave_squad_id: str,
    expires_at: datetime,
    max_users: int,
) -> PersonalVPNInstance:
    if max_users < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='max_users must be at least 1')

    owner = await _resolve_owner_user(
        db,
        owner_user_id=owner_user_id,
        owner_username=owner_username,
        owner_telegram_id=owner_telegram_id,
    )

    existing = await _get_instance_for_owner(db, owner.id)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='User already has personal VPN instance')

    expires_at_aware = _ensure_aware(expires_at)
    if expires_at_aware <= _now_utc():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='expires_at must be in the future')

    await _validate_node_and_squad(node_id=remnawave_node_id, squad_id=remnawave_squad_id)

    instance = PersonalVPNInstance(
        owner_user_id=owner.id,
        remnawave_node_id=remnawave_node_id,
        remnawave_squad_id=remnawave_squad_id,
        expires_at=expires_at_aware,
        status='active',
        max_users=max_users,
    )
    db.add(instance)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='User already has personal VPN instance')
    await db.refresh(instance)
    return instance


async def update_personal_vpn_instance(
    db: AsyncSession,
    *,
    instance_id: int,
    expires_at: datetime | None,
    max_users: int | None,
) -> PersonalVPNInstance:
    instance = await db.get(PersonalVPNInstance, instance_id)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Instance not found')

    if expires_at is None and max_users is None:
        return instance

    if max_users is not None:
        if max_users < 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='max_users must be at least 1')
        active_count = await _get_active_user_count(db, instance.id)
        if max_users < active_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='max_users cannot be less than current active users',
            )
        instance.max_users = max_users

    if expires_at is not None:
        expires_at_aware = _ensure_aware(expires_at)
        instance.expires_at = expires_at_aware
        if expires_at_aware > _now_utc() and instance.status == 'expired':
            instance.status = 'active'

    await db.commit()
    await db.refresh(instance)
    return instance


async def _build_sub_user_item(api, row: PersonalVPNUser) -> dict:
    panel_user = None
    devices_total = 0

    try:
        panel_user = await api.get_user_by_uuid(row.remnawave_user_id)
    except Exception:
        panel_user = None

    try:
        devices = await api.get_user_devices(row.remnawave_user_id)
        devices_total = int(devices.get('total', 0) or 0)
    except Exception:
        devices_total = 0

    traffic_limit_bytes = int(panel_user.traffic_limit_bytes) if panel_user else int(row.traffic_limit_bytes or 0)
    traffic_used_bytes = int(panel_user.used_traffic_bytes) if panel_user else 0
    subscription_link = panel_user.subscription_url if panel_user else row.subscription_link
    user_status = panel_user.status.value.lower() if panel_user else 'unknown'

    return {
        'id': row.id,
        'remnawave_user_id': row.remnawave_user_id,
        'expires_at': row.expires_at,
        'device_limit': row.device_limit,
        'traffic_limit_bytes': traffic_limit_bytes,
        'traffic_limit_gb': round(traffic_limit_bytes / (1024**3), 2),
        'status': user_status,
        'traffic_used_bytes': traffic_used_bytes,
        'traffic_used_gb': round(traffic_used_bytes / (1024**3), 2),
        'devices_used': devices_total,
        'subscription_link': subscription_link,
        'created_at': row.created_at,
    }


async def get_personal_vpn_overview(db: AsyncSession, user: User) -> dict:
    instance = await _get_instance_for_owner(db, user.id)
    if instance is None:
        return {'has_instance': False}

    now = _now_utc()
    effective_status = _instance_effective_status(instance, now)

    query = (
        select(PersonalVPNUser)
        .where(
            PersonalVPNUser.instance_id == instance.id,
            PersonalVPNUser.deleted_at.is_(None),
        )
        .order_by(PersonalVPNUser.created_at.desc())
    )
    rows = (await db.execute(query)).scalars().all()

    service = _get_remnawave_service()

    node_status = {
        'id': instance.remnawave_node_id,
        'name': None,
        'online': False,
        'is_disabled': None,
    }

    sub_users: list[dict] = []
    try:
        node_data = await service.get_node_details(instance.remnawave_node_id)
        if node_data:
            node_status = {
                'id': instance.remnawave_node_id,
                'name': node_data.get('name'),
                'online': bool(node_data.get('is_connected')) and not bool(node_data.get('is_disabled')),
                'is_disabled': bool(node_data.get('is_disabled')),
            }

        async with service.get_api_client() as api:
            sub_users = await asyncio.gather(*[_build_sub_user_item(api, row) for row in rows])
    except Exception:
        sub_users = [
            {
                'id': row.id,
                'remnawave_user_id': row.remnawave_user_id,
                'expires_at': row.expires_at,
                'device_limit': row.device_limit,
                'traffic_limit_bytes': int(row.traffic_limit_bytes or 0),
                'traffic_limit_gb': round(int(row.traffic_limit_bytes or 0) / (1024**3), 2),
                'status': 'unknown',
                'traffic_used_bytes': 0,
                'traffic_used_gb': 0,
                'devices_used': 0,
                'subscription_link': row.subscription_link,
                'created_at': row.created_at,
            }
            for row in rows
        ]

    cooldown_seconds = 0
    if instance.last_restart_at:
        last_restart = _ensure_aware(instance.last_restart_at)
        elapsed = (now - last_restart).total_seconds()
        cooldown_seconds = max(0, int(RESTART_COOLDOWN.total_seconds() - elapsed))

    return {
        'has_instance': True,
        'instance_id': instance.id,
        'status': effective_status,
        'expires_at': instance.expires_at,
        'max_users': int(instance.max_users or 0),
        'current_user_count': len(rows),
        'restart_cooldown_remaining_seconds': cooldown_seconds,
        'last_restart_at': instance.last_restart_at,
        'node': node_status,
        'sub_users': sub_users,
    }


async def restart_personal_vpn_node(db: AsyncSession, user: User) -> PersonalVPNInstance:
    instance = await _get_instance_for_owner(db, user.id, for_update=True)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Personal VPN instance not found')

    _ensure_instance_actionable(instance)

    now = _now_utc()
    if instance.last_restart_at:
        last_restart = _ensure_aware(instance.last_restart_at)
        if now - last_restart < RESTART_COOLDOWN:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail='Перезапуск доступен раз в 10 минут',
            )

    service = _get_remnawave_service()
    success = await service.manage_node(instance.remnawave_node_id, 'restart')
    if not success:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='Failed to restart node')

    instance.last_restart_at = now
    await db.commit()
    await db.refresh(instance)
    return instance


async def create_personal_vpn_sub_user(
    db: AsyncSession,
    user: User,
    *,
    expires_at: datetime,
    device_limit: int,
    traffic_limit_gb: float,
) -> dict:
    instance = await _get_instance_for_owner(db, user.id, for_update=True)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Personal VPN instance not found')

    _ensure_instance_actionable(instance)

    expires_at_aware = _ensure_aware(expires_at)
    if expires_at_aware > _ensure_aware(instance.expires_at):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Sub-user expiration cannot exceed personal VPN expiration',
        )

    active_count = await _get_active_user_count(db, instance.id)
    if active_count >= int(instance.max_users or 0):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Max sub-users limit reached')

    if device_limit < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='device_limit must be at least 1')
    if traffic_limit_gb < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='traffic_limit must be >= 0')

    traffic_limit_bytes = int(traffic_limit_gb * (1024**3))
    service = _get_remnawave_service()

    created_user = None
    try:
        async with service.get_api_client() as api:
            created_user = await api.create_user(
                username=f'pvpn-{instance.owner_user_id}-{uuid4().hex[:8]}',
                expire_at=expires_at_aware,
                status=UserStatus.ACTIVE,
                traffic_limit_bytes=traffic_limit_bytes,
                traffic_limit_strategy=TrafficLimitStrategy.NO_RESET,
                hwid_device_limit=device_limit,
                description=f'Personal VPN sub-user of owner #{instance.owner_user_id}',
                active_internal_squads=[instance.remnawave_squad_id],
            )

            row = PersonalVPNUser(
                instance_id=instance.id,
                remnawave_user_id=created_user.uuid,
                expires_at=expires_at_aware,
                device_limit=device_limit,
                traffic_limit_bytes=traffic_limit_bytes,
                subscription_link=created_user.subscription_url,
            )
            db.add(row)
            await db.commit()
            await db.refresh(row)

            return await _build_sub_user_item(api, row)
    except RemnaWaveConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        if created_user is not None:
            try:
                async with service.get_api_client() as api:
                    await api.delete_user(created_user.uuid)
            except Exception:
                pass
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f'Failed to create sub-user: {exc!s}')


async def delete_personal_vpn_sub_user(db: AsyncSession, user: User, *, sub_user_id: int) -> None:
    instance = await _get_instance_for_owner(db, user.id, for_update=True)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Personal VPN instance not found')

    _ensure_instance_actionable(instance)

    row = await db.get(PersonalVPNUser, sub_user_id)
    if row is None or row.instance_id != instance.id or row.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Sub-user not found')

    service = _get_remnawave_service()
    try:
        async with service.get_api_client() as api:
            deleted = await api.delete_user(row.remnawave_user_id)
            if not deleted:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='Failed to delete sub-user')
    except RemnaWaveConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f'Failed to delete sub-user: {exc!s}')

    row.deleted_at = _now_utc()
    await db.commit()


async def ensure_owner_instance(db: AsyncSession, user: User) -> PersonalVPNInstance:
    instance = await _get_instance_for_owner(db, user.id)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Personal VPN instance not found')
    return instance

