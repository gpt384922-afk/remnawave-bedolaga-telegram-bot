import structlog
from aiogram import Dispatcher, F, types
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.services.family_service import accept_family_invite, decline_family_invite


logger = structlog.get_logger(__name__)


def _extract_invite_id(callback_data: str) -> int | None:
    try:
        _, _, invite_id_str = callback_data.split(':', maxsplit=2)
        return int(invite_id_str)
    except Exception:
        return None


async def handle_family_invite_accept(callback: types.CallbackQuery, db_user: User, db: AsyncSession):
    invite_id = _extract_invite_id(callback.data or '')
    if not invite_id:
        await callback.answer('Invalid invite', show_alert=True)
        return

    user_id = getattr(db_user, 'id', None)
    try:
        await accept_family_invite(db, db_user, invite_id)
        if callback.message:
            await callback.message.edit_text('Family invitation accepted.')
        await callback.answer('Accepted')
    except Exception as exc:
        await db.rollback()
        message = 'Failed to accept invite'
        if isinstance(exc, HTTPException) and isinstance(exc.detail, str):
            message = exc.detail
        logger.warning('Failed to accept family invite', user_id=user_id, invite_id=invite_id, exc=exc)
        await callback.answer(message, show_alert=True)


async def handle_family_invite_decline(callback: types.CallbackQuery, db_user: User, db: AsyncSession):
    invite_id = _extract_invite_id(callback.data or '')
    if not invite_id:
        await callback.answer('Invalid invite', show_alert=True)
        return

    user_id = getattr(db_user, 'id', None)
    try:
        await decline_family_invite(db, db_user, invite_id)
        if callback.message:
            await callback.message.edit_text('Family invitation declined.')
        await callback.answer('Declined')
    except Exception as exc:
        await db.rollback()
        message = 'Failed to decline invite'
        if isinstance(exc, HTTPException) and isinstance(exc.detail, str):
            message = exc.detail
        logger.warning('Failed to decline family invite', user_id=user_id, invite_id=invite_id, exc=exc)
        await callback.answer(message, show_alert=True)


def register_handlers(dp: Dispatcher):
    dp.callback_query.register(handle_family_invite_accept, F.data.startswith('family_invite:accept:'))
    dp.callback_query.register(handle_family_invite_decline, F.data.startswith('family_invite:decline:'))
