from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database.crud.user_notification import create_user_notification
from app.database.models import FamilyDevice, FamilyGroup, FamilyInvite, FamilyMember, Subscription, Tariff, User


logger = structlog.get_logger(__name__)

MEMBER_ACTIVE = 'active'
MEMBER_INVITED = 'invited'
MEMBER_DECLINED = 'declined'
MEMBER_LEFT = 'left'
MEMBER_REMOVED = 'removed'

INVITE_PENDING = 'pending'
INVITE_ACCEPTED = 'accepted'
INVITE_DECLINED = 'declined'
INVITE_REVOKED = 'revoked'
INVITE_EXPIRED = 'expired'


@dataclass
class FamilyAccessContext:
    requester: User
    owner: User | None
    subscription: Subscription | None
    tariff: Tariff | None
    group: FamilyGroup | None
    role: str | None  # owner/member/None


def normalize_tg_username(raw: str) -> str:
    value = (raw or '').strip()
    if value.startswith('@'):
        value = value[1:]
    return value.lower().strip()


def display_username(user: User | None) -> str:
    if not user:
        return 'Unknown'
    if user.username:
        return f'@{user.username}'
    if user.telegram_id:
        return f'ID{user.telegram_id}'
    return f'User#{user.id}'


async def _load_user(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.subscription).selectinload(Subscription.tariff))
    )
    return result.scalar_one_or_none()


async def _owner_group(db: AsyncSession, owner_user_id: int) -> FamilyGroup | None:
    result = await db.execute(select(FamilyGroup).where(FamilyGroup.owner_user_id == owner_user_id))
    return result.scalar_one_or_none()


async def _active_membership(db: AsyncSession, user_id: int) -> FamilyMember | None:
    result = await db.execute(
        select(FamilyMember)
        .where(FamilyMember.user_id == user_id, FamilyMember.status == MEMBER_ACTIVE)
        .options(selectinload(FamilyMember.family_group))
    )
    return result.scalar_one_or_none()


async def _active_member_count(db: AsyncSession, group_id: int) -> int:
    result = await db.execute(
        select(func.count(FamilyMember.id)).where(
            FamilyMember.family_group_id == group_id,
            FamilyMember.status == MEMBER_ACTIVE,
        )
    )
    return int(result.scalar() or 0)


async def _in_active_family(db: AsyncSession, user_id: int, exclude_group_id: int | None = None) -> bool:
    member_query = select(FamilyMember.id).where(FamilyMember.user_id == user_id, FamilyMember.status == MEMBER_ACTIVE)
    if exclude_group_id is not None:
        member_query = member_query.where(FamilyMember.family_group_id != exclude_group_id)
    if (await db.execute(member_query.limit(1))).scalar_one_or_none() is not None:
        return True

    owner_query = select(FamilyGroup.id).where(FamilyGroup.owner_user_id == user_id)
    if exclude_group_id is not None:
        owner_query = owner_query.where(FamilyGroup.id != exclude_group_id)
    return (await db.execute(owner_query.limit(1))).scalar_one_or_none() is not None


async def get_access_context(db: AsyncSession, user: User) -> FamilyAccessContext:
    requester = await _load_user(db, user.id)
    if not requester:
        return FamilyAccessContext(user, None, None, None, None, None)

    membership = await _active_membership(db, requester.id)
    if membership:
        owner = await _load_user(db, membership.family_group.owner_user_id)
        return FamilyAccessContext(
            requester=requester,
            owner=owner,
            subscription=owner.subscription if owner else None,
            tariff=owner.subscription.tariff if owner and owner.subscription else None,
            group=membership.family_group,
            role='member',
        )

    group = await _owner_group(db, requester.id)
    if group:
        return FamilyAccessContext(
            requester=requester,
            owner=requester,
            subscription=requester.subscription,
            tariff=requester.subscription.tariff if requester.subscription else None,
            group=group,
            role='owner',
        )

    if requester.subscription:
        return FamilyAccessContext(
            requester=requester,
            owner=requester,
            subscription=requester.subscription,
            tariff=requester.subscription.tariff,
            group=None,
            role='owner',
        )

    return FamilyAccessContext(requester, None, None, None, None, None)


def _validate_owner_family_enabled(subscription: Subscription | None, tariff: Tariff | None) -> int:
    if not subscription or not tariff:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='No active subscription with tariff')
    if not tariff.family_enabled or int(tariff.family_max_members or 0) <= 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Family access is not available for your tariff')
    return int(tariff.family_max_members or 0)


async def _ensure_group(db: AsyncSession, owner: User, subscription: Subscription) -> FamilyGroup:
    group = await _owner_group(db, owner.id)
    if group:
        if group.subscription_id != subscription.id:
            group.subscription_id = subscription.id
            await db.flush()
        return group
    group = FamilyGroup(owner_user_id=owner.id, subscription_id=subscription.id)
    db.add(group)
    await db.flush()
    return group


async def _send_ws(user_id: int, payload: dict[str, Any]) -> None:
    from app.cabinet.routes.websocket import cabinet_ws_manager

    await cabinet_ws_manager.send_to_user(user_id, payload)


async def _notify(
    db: AsyncSession,
    *,
    user_id: int,
    notification_type: str,
    title: str,
    body: str,
    ws_type: str,
    payload: dict[str, Any] | None = None,
) -> None:
    await create_user_notification(
        db,
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        body=body,
        payload=payload or {},
    )
    await db.commit()
    await _send_ws(user_id, {'type': ws_type, 'title': title, 'message': body, **(payload or {})})


async def _send_tg(telegram_id: int | None, text: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
    if not telegram_id:
        return
    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        await bot.send_message(telegram_id, text, reply_markup=reply_markup)
    except Exception as exc:
        logger.warning('Failed to send family telegram notification', telegram_id=telegram_id, exc=exc)
    finally:
        await bot.session.close()


async def _get_pending_invites_for_user(db: AsyncSession, user_id: int) -> list[dict[str, Any]]:
    rows = (
        (
            await db.execute(
                select(FamilyInvite)
                .where(
                    FamilyInvite.invitee_user_id == user_id,
                    FamilyInvite.status == INVITE_PENDING,
                )
                .options(
                    selectinload(FamilyInvite.inviter),
                    selectinload(FamilyInvite.family_group),
                )
                .order_by(FamilyInvite.created_at.desc())
            )
        )
        .scalars()
        .all()
    )

    return [
        {
            'invite_id': row.id,
            'family_group_id': row.family_group_id,
            'status': row.status,
            'created_at': row.created_at,
            'expires_at': row.expires_at,
            'inviter_user_id': row.inviter_user_id,
            'inviter_username': row.inviter.username if row.inviter else None,
            'inviter_display_name': display_username(row.inviter),
        }
        for row in rows
    ]


async def get_family_overview(db: AsyncSession, user: User) -> dict[str, Any]:
    ctx = await get_access_context(db, user)
    pending_invites = await _get_pending_invites_for_user(db, user.id)
    if not ctx.owner or not ctx.subscription:
        return {
            'family_enabled': False,
            'role': None,
            'owner': None,
            'members': [],
            'invites': [],
            'pending_invites_for_you': pending_invites,
            'max_members_including_owner': 0,
            'used_slots': 0,
            'remaining_slots': 0,
            'can_invite': False,
            'device_summary': {'device_limit': 0, 'total_used': 0, 'remaining': 0, 'by_user': []},
        }

    family_enabled = bool(ctx.tariff and ctx.tariff.family_enabled and int(ctx.tariff.family_max_members or 0) > 1)
    max_members = int(ctx.tariff.family_max_members or 0) if ctx.tariff else 0

    group = ctx.group
    if group is None and ctx.role == 'owner' and family_enabled:
        group = await _ensure_group(db, ctx.owner, ctx.subscription)
        await db.commit()

    if not group:
        return {
            'family_enabled': family_enabled,
            'role': ctx.role,
            'owner': {'user_id': ctx.owner.id, 'username': ctx.owner.username, 'display_name': display_username(ctx.owner)},
            'members': [],
            'invites': [],
            'pending_invites_for_you': pending_invites,
            'max_members_including_owner': max_members,
            'used_slots': 1,
            'remaining_slots': max(0, max_members - 1),
            'can_invite': ctx.role == 'owner' and family_enabled,
            'device_summary': {
                'device_limit': ctx.subscription.device_limit or 1,
                'total_used': 0,
                'remaining': ctx.subscription.device_limit or 1,
                'by_user': [],
            },
        }

    member_rows = (
        (
            await db.execute(
                select(FamilyMember)
                .where(
                    FamilyMember.family_group_id == group.id,
                    FamilyMember.status.in_((MEMBER_ACTIVE, MEMBER_INVITED)),
                )
                .options(selectinload(FamilyMember.user))
                .order_by(FamilyMember.invited_at.desc())
            )
        )
        .scalars()
        .all()
    )

    invite_rows = (
        (
            await db.execute(
                select(FamilyInvite)
                .where(
                    FamilyInvite.family_group_id == group.id,
                    FamilyInvite.status == INVITE_PENDING,
                )
                .options(selectinload(FamilyInvite.invitee))
                .order_by(FamilyInvite.created_at.desc())
            )
        )
        .scalars()
        .all()
    )

    device_rows = (
        (
            await db.execute(select(FamilyDevice).where(FamilyDevice.family_group_id == group.id))
        )
        .scalars()
        .all()
    )

    by_user: dict[int, int] = {}
    for d in device_rows:
        by_user[d.owner_user_id] = by_user.get(d.owner_user_id, 0) + 1

    members = [
        {
            'user_id': ctx.owner.id,
            'username': ctx.owner.username,
            'display_name': display_username(ctx.owner),
            'role': 'owner',
            'status': 'active',
            'invited_at': None,
            'accepted_at': None,
            'can_remove': False,
            'devices_count': by_user.get(ctx.owner.id, 0),
        }
    ]

    for m in member_rows:
        u = m.user
        members.append(
            {
                'user_id': m.user_id,
                'username': u.username if u else None,
                'display_name': display_username(u),
                'role': m.role,
                'status': m.status,
                'invited_at': m.invited_at,
                'accepted_at': m.accepted_at,
                'can_remove': ctx.role == 'owner' and m.status in {MEMBER_ACTIVE, MEMBER_INVITED},
                'devices_count': by_user.get(m.user_id, 0),
            }
        )

    invites = [
        {
            'invite_id': inv.id,
            'invitee_user_id': inv.invitee_user_id,
            'username': inv.invitee.username if inv.invitee else None,
            'display_name': display_username(inv.invitee),
            'status': inv.status,
            'created_at': inv.created_at,
            'expires_at': inv.expires_at,
            'can_revoke': ctx.role == 'owner' and inv.status == INVITE_PENDING,
        }
        for inv in invite_rows
    ]

    used_slots = 1 + sum(1 for m in member_rows if m.status == MEMBER_ACTIVE)
    limit = ctx.subscription.device_limit or 1
    total_used = len(device_rows)

    return {
        'family_enabled': family_enabled,
        'role': ctx.role,
        'owner': {'user_id': ctx.owner.id, 'username': ctx.owner.username, 'display_name': display_username(ctx.owner)},
        'family_group_id': group.id,
        'members': members,
        'invites': invites,
        'pending_invites_for_you': pending_invites,
        'max_members_including_owner': max_members,
        'used_slots': used_slots,
        'remaining_slots': max(0, max_members - used_slots),
        'can_invite': ctx.role == 'owner' and family_enabled and used_slots < max_members,
        'device_summary': {
            'device_limit': limit,
            'total_used': total_used,
            'remaining': max(0, limit - total_used),
            'by_user': [{'user_id': uid, 'count': count} for uid, count in by_user.items()],
        },
    }


async def create_family_invite(db: AsyncSession, owner_user: User, tg_username: str) -> FamilyInvite:
    owner = await _load_user(db, owner_user.id)
    if not owner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
    max_members = _validate_owner_family_enabled(owner.subscription, owner.subscription.tariff if owner.subscription else None)

    normalized = normalize_tg_username(tg_username)
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid Telegram username')

    invitee = (
        (
            await db.execute(
                select(User)
                .where(func.lower(User.username) == normalized)
                .options(selectinload(User.subscription))
            )
        )
        .scalars()
        .first()
    )
    if not invitee or not invitee.telegram_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='User must start the bot first')
    if invitee.id == owner.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='You cannot invite yourself')
    invitee_subscription = getattr(invitee, 'subscription', None)
    if invitee_subscription and invitee_subscription.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                'error_code': 'INVITEE_HAS_ACTIVE_SUBSCRIPTION',
                'message': 'Cannot invite user with active subscription',
                'message_ru': 'Нельзя пригласить пользователя с активной подпиской',
            },
        )
    if await _in_active_family(db, invitee.id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='User is already in another family')

    group = await _ensure_group(db, owner, owner.subscription)
    group = (
        (
            await db.execute(select(FamilyGroup).where(FamilyGroup.id == group.id).with_for_update())
        )
        .scalars()
        .first()
    )

    if 1 + await _active_member_count(db, group.id) >= max_members:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Family member limit reached')

    pending = (
        (
            await db.execute(
                select(FamilyInvite).where(
                    FamilyInvite.family_group_id == group.id,
                    FamilyInvite.invitee_user_id == invitee.id,
                    FamilyInvite.status == INVITE_PENDING,
                )
            )
        )
        .scalars()
        .first()
    )
    if pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invite already pending')

    invite = FamilyInvite(
        family_group_id=group.id,
        invitee_user_id=invitee.id,
        inviter_user_id=owner.id,
        status=INVITE_PENDING,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db.add(invite)

    member = (
        (
            await db.execute(
                select(FamilyMember).where(
                    FamilyMember.family_group_id == group.id,
                    FamilyMember.user_id == invitee.id,
                )
            )
        )
        .scalars()
        .first()
    )
    if not member:
        db.add(
            FamilyMember(
                family_group_id=group.id,
                user_id=invitee.id,
                role='member',
                status=MEMBER_INVITED,
                invited_by_user_id=owner.id,
                invited_at=datetime.now(UTC),
            )
        )
    else:
        member.status = MEMBER_INVITED
        member.role = 'member'
        member.invited_by_user_id = owner.id
        member.invited_at = datetime.now(UTC)
        member.removed_at = None

    await db.commit()
    await db.refresh(invite)

    body = f'You were invited to family access by {display_username(owner)}. Accept?'
    try:
        await _notify(
            db,
            user_id=invitee.id,
            notification_type='family_invite_received',
            title='Family invitation',
            body=body,
            ws_type='family.invite_received',
            payload={'invite_id': invite.id, 'owner_user_id': owner.id},
        )
    except Exception as exc:
        logger.warning('Failed to push family invite notification', invite_id=invite.id, exc=exc)
        await db.rollback()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text='Accept', callback_data=f'family_invite:accept:{invite.id}'),
            InlineKeyboardButton(text='Decline', callback_data=f'family_invite:decline:{invite.id}'),
        ]]
    )
    await _send_tg(invitee.telegram_id, body, keyboard)
    return invite

async def _invite_for_update(db: AsyncSession, invite_id: int) -> FamilyInvite | None:
    return (
        (
            await db.execute(
                select(FamilyInvite).where(FamilyInvite.id == invite_id).with_for_update()
            )
        )
        .scalars()
        .first()
    )


async def accept_family_invite(db: AsyncSession, user: User, invite_id: int) -> FamilyInvite:
    invite = await _invite_for_update(db, invite_id)
    if not invite or invite.invitee_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Invite not found')
    if invite.status != INVITE_PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invite is not pending')

    now = datetime.now(UTC)
    if invite.expires_at and invite.expires_at <= now:
        invite.status = INVITE_EXPIRED
        invite.decided_at = now
        await db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invite expired')

    group = (
        (
            await db.execute(select(FamilyGroup).where(FamilyGroup.id == invite.family_group_id).with_for_update())
        )
        .scalars()
        .first()
    )
    owner = await _load_user(db, group.owner_user_id) if group else None
    max_members = _validate_owner_family_enabled(owner.subscription if owner else None, owner.subscription.tariff if owner and owner.subscription else None)

    if await _in_active_family(db, user.id, exclude_group_id=group.id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='User is already in another family')

    if 1 + await _active_member_count(db, group.id) >= max_members:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Family member limit reached')

    invite.status = INVITE_ACCEPTED
    invite.decided_at = now

    member = (
        (
            await db.execute(
                select(FamilyMember).where(
                    FamilyMember.family_group_id == group.id,
                    FamilyMember.user_id == user.id,
                )
            )
        )
        .scalars()
        .first()
    )
    if not member:
        db.add(
            FamilyMember(
                family_group_id=group.id,
                user_id=user.id,
                role='member',
                status=MEMBER_ACTIVE,
                invited_by_user_id=invite.inviter_user_id,
                invited_at=invite.created_at,
                accepted_at=now,
            )
        )
    else:
        member.status = MEMBER_ACTIVE
        member.accepted_at = now
        member.removed_at = None

    await db.commit()

    if owner and owner.remnawave_uuid:
        try:
            from app.services.remnawave_service import RemnaWaveService

            service = RemnaWaveService()
            async with service.get_api_client() as api:
                panel_data = await api.get_user_devices(owner.remnawave_uuid)
                await sync_family_devices_from_panel(
                    db,
                    family_group_id=group.id,
                    actor_user_id=owner.id,
                    panel_devices=panel_data.get('devices', []),
                )
        except Exception as exc:
            logger.warning(
                'Failed to seed family device ownership on invite accept',
                invite_id=invite.id,
                exc=exc,
            )

    owner_body = f'{display_username(user)} accepted your family invitation.'
    try:
        await _notify(
            db,
            user_id=group.owner_user_id,
            notification_type='family_invite_accepted',
            title='Family invitation accepted',
            body=owner_body,
            ws_type='family.invite_accepted',
            payload={'invite_id': invite.id, 'member_user_id': user.id},
        )
    except Exception as exc:
        logger.warning('Failed to notify owner about accepted invite', invite_id=invite.id, exc=exc)
        await db.rollback()

    if owner:
        await _send_tg(owner.telegram_id, owner_body)

    return invite


async def decline_family_invite(db: AsyncSession, user: User, invite_id: int) -> FamilyInvite:
    invite = await _invite_for_update(db, invite_id)
    if not invite or invite.invitee_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Invite not found')
    if invite.status != INVITE_PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invite is not pending')

    now = datetime.now(UTC)
    invite.status = INVITE_DECLINED
    invite.decided_at = now

    member = (
        (
            await db.execute(
                select(FamilyMember).where(
                    FamilyMember.family_group_id == invite.family_group_id,
                    FamilyMember.user_id == user.id,
                )
            )
        )
        .scalars()
        .first()
    )
    if member:
        member.status = MEMBER_DECLINED
        member.removed_at = now

    await db.commit()

    group = await db.get(FamilyGroup, invite.family_group_id)
    owner = await _load_user(db, group.owner_user_id) if group else None
    body = f'{display_username(user)} declined your family invitation.'
    if group:
        try:
            await _notify(
                db,
                user_id=group.owner_user_id,
                notification_type='family_invite_declined',
                title='Family invitation declined',
                body=body,
                ws_type='family.invite_declined',
                payload={'invite_id': invite.id, 'member_user_id': user.id},
            )
        except Exception as exc:
            logger.warning('Failed to notify owner about declined invite', invite_id=invite.id, exc=exc)
            await db.rollback()

    if owner:
        await _send_tg(owner.telegram_id, body)
    return invite


async def revoke_family_invite(db: AsyncSession, owner_user: User, invite_id: int) -> FamilyInvite:
    ctx = await get_access_context(db, owner_user)
    if ctx.role != 'owner' or not ctx.group:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only owner can revoke invites')

    invite = await _invite_for_update(db, invite_id)
    if not invite or invite.family_group_id != ctx.group.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Invite not found')
    if invite.status != INVITE_PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invite is not pending')

    invite.status = INVITE_REVOKED
    invite.decided_at = datetime.now(UTC)
    await db.commit()

    invitee = await _load_user(db, invite.invitee_user_id)
    body = f'Your family invitation from {display_username(ctx.owner)} was revoked.'
    try:
        await _notify(
            db,
            user_id=invite.invitee_user_id,
            notification_type='family_invite_revoked',
            title='Family invitation revoked',
            body=body,
            ws_type='family.invite_revoked',
            payload={'invite_id': invite.id, 'owner_user_id': ctx.owner.id if ctx.owner else None},
        )
    except Exception as exc:
        logger.warning('Failed to notify invitee about revoked invite', invite_id=invite.id, exc=exc)
        await db.rollback()

    if invitee:
        await _send_tg(invitee.telegram_id, body)
    return invite


async def _remove_member_devices(
    db: AsyncSession,
    *,
    group_id: int,
    member_user_id: int,
    owner_uuid: str | None,
) -> int:
    rows = (
        (
            await db.execute(
                select(FamilyDevice).where(
                    FamilyDevice.family_group_id == group_id,
                    FamilyDevice.owner_user_id == member_user_id,
                )
            )
        )
        .scalars()
        .all()
    )
    if not rows:
        return 0

    removed = 0
    if owner_uuid:
        try:
            from app.services.remnawave_service import RemnaWaveService

            service = RemnaWaveService()
            async with service.get_api_client() as api:
                for row in rows:
                    try:
                        await api._make_request('POST', '/api/hwid/devices/delete', data={'userUuid': owner_uuid, 'hwid': row.hwid})
                        removed += 1
                    except Exception as exc:
                        logger.warning('Failed to delete family device from panel', hwid=row.hwid, exc=exc)
        except Exception as exc:
            logger.warning('Failed to initialize panel client for family cleanup', exc=exc)

    for row in rows:
        await db.delete(row)
    return removed


async def remove_family_member(db: AsyncSession, owner_user: User, member_user_id: int) -> None:
    ctx = await get_access_context(db, owner_user)
    if ctx.role != 'owner' or not ctx.group or not ctx.owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only owner can remove members')
    if member_user_id == ctx.owner.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Owner cannot remove themselves')

    member = (
        (
            await db.execute(
                select(FamilyMember)
                .where(
                    FamilyMember.family_group_id == ctx.group.id,
                    FamilyMember.user_id == member_user_id,
                    FamilyMember.status == MEMBER_ACTIVE,
                )
                .with_for_update()
            )
        )
        .scalars()
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Active family member not found')

    member.status = MEMBER_REMOVED
    member.removed_at = datetime.now(UTC)

    await _remove_member_devices(db, group_id=ctx.group.id, member_user_id=member_user_id, owner_uuid=ctx.owner.remnawave_uuid)
    await db.commit()

    removed_user = await _load_user(db, member_user_id)
    body = f'You were removed from family access by {display_username(ctx.owner)}.'
    try:
        await _notify(
            db,
            user_id=member_user_id,
            notification_type='family_member_removed',
            title='Removed from family',
            body=body,
            ws_type='family.member_removed',
            payload={'owner_user_id': ctx.owner.id},
        )
    except Exception as exc:
        logger.warning('Failed to notify removed family member', member_user_id=member_user_id, exc=exc)
        await db.rollback()

    if removed_user:
        await _send_tg(removed_user.telegram_id, body)


async def leave_family(db: AsyncSession, user: User) -> None:
    ctx = await get_access_context(db, user)
    if ctx.role != 'member' or not ctx.group or not ctx.owner:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='User is not an active family member')

    member = (
        (
            await db.execute(
                select(FamilyMember)
                .where(
                    FamilyMember.family_group_id == ctx.group.id,
                    FamilyMember.user_id == user.id,
                    FamilyMember.status == MEMBER_ACTIVE,
                )
                .with_for_update()
            )
        )
        .scalars()
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Active family membership not found')

    member.status = MEMBER_LEFT
    member.removed_at = datetime.now(UTC)
    await _remove_member_devices(db, group_id=ctx.group.id, member_user_id=user.id, owner_uuid=ctx.owner.remnawave_uuid)
    await db.commit()

    body = f'{display_username(user)} left your family access.'
    try:
        await _notify(
            db,
            user_id=ctx.owner.id,
            notification_type='family_member_left',
            title='Family member left',
            body=body,
            ws_type='family.member_left',
            payload={'member_user_id': user.id},
        )
    except Exception as exc:
        logger.warning('Failed to notify owner about member leave', owner_user_id=ctx.owner.id, exc=exc)
        await db.rollback()

    await _send_tg(ctx.owner.telegram_id, body)


async def sync_family_devices_from_panel(
    db: AsyncSession,
    *,
    family_group_id: int,
    actor_user_id: int,
    panel_devices: list[dict[str, Any]],
) -> dict[str, FamilyDevice]:
    existing = (
        (
            await db.execute(select(FamilyDevice).where(FamilyDevice.family_group_id == family_group_id))
        )
        .scalars()
        .all()
    )
    by_hwid = {row.hwid: row for row in existing}

    active_ids = {actor_user_id}
    member_ids = (
        (
            await db.execute(
                select(FamilyMember.user_id).where(
                    FamilyMember.family_group_id == family_group_id,
                    FamilyMember.status == MEMBER_ACTIVE,
                )
            )
        )
        .all()
    )
    for item in member_ids:
        active_ids.add(int(item[0]))

    current: set[str] = set()
    for item in panel_devices:
        hwid = (item.get('hwid') or item.get('deviceId') or item.get('id') or '').strip()
        if not hwid:
            continue
        current.add(hwid)

        platform = item.get('platform') or item.get('platformType') or 'Unknown'
        model = item.get('deviceModel') or item.get('model') or item.get('name') or 'Unknown'
        row = by_hwid.get(hwid)
        if not row:
            row = FamilyDevice(
                family_group_id=family_group_id,
                hwid=hwid,
                owner_user_id=actor_user_id if actor_user_id in active_ids else min(active_ids),
                platform=platform,
                device_model=model,
            )
            db.add(row)
            by_hwid[hwid] = row
        else:
            row.platform = platform
            row.device_model = model
            row.last_seen_at = datetime.now(UTC)

    for hwid, row in list(by_hwid.items()):
        if hwid not in current:
            await db.delete(row)
            del by_hwid[hwid]

    await db.commit()
    return by_hwid
