import structlog
from aiogram import Dispatcher, F, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import InaccessibleMessage

from app.config import settings
from app.database.models import User
from app.keyboards.inline import get_back_keyboard
from app.localization.texts import get_texts
from app.utils.decorators import error_handler

logger = structlog.get_logger(__name__)

PERSONAL_VPN_CALLBACK = 'menu_personal_vpn'


def _build_text(texts) -> str:
    return f"{texts.t('PERSONAL_VPN_TITLE', '🔒 Личный VPN')}\n\n{texts.t('PERSONAL_VPN_DESCRIPTION', 'VPN под ключ (для продакшена)')}"


@error_handler
async def show_personal_vpn(callback: types.CallbackQuery, db_user: User, state: FSMContext):
    if not settings.PERSONAL_VPN_ENABLED:
        await callback.answer('Раздел временно недоступен', show_alert=True)
        return

    texts = get_texts(db_user.language)
    text = _build_text(texts)

    await callback.answer()

    if isinstance(callback.message, InaccessibleMessage):
        await callback.message.answer(text, reply_markup=get_back_keyboard(db_user.language))
        return

    try:
        await callback.message.edit_text(text, reply_markup=get_back_keyboard(db_user.language))
    except TelegramBadRequest as error:
        if 'there is no text in the message to edit' in str(error).lower():
            await callback.message.answer(text, reply_markup=get_back_keyboard(db_user.language))
        else:
            raise


def register_handlers(dp: Dispatcher):
    dp.callback_query.register(show_personal_vpn, F.data == PERSONAL_VPN_CALLBACK)
