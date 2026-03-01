from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Subscription, Tariff, User
from app.services.family_service import get_access_context
from app.utils.subscription_utils import is_subscription_active


EffectiveSubscriptionSource = Literal['personal', 'family_owner']


@dataclass
class EffectiveSubscriptionResult:
    active: bool
    source: EffectiveSubscriptionSource | None
    subscription: Subscription | None
    tariff: Tariff | None
    owner_user: User | None
    requester_user: User | None

    @property
    def expires_at(self) -> datetime | None:
        if not self.active or not self.subscription:
            return None
        return self.subscription.end_date


async def _load_user_with_subscription(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.subscription).selectinload(Subscription.tariff))
    )
    return result.scalar_one_or_none()


async def resolve_effective_subscription(db: AsyncSession, user: User) -> EffectiveSubscriptionResult:
    requester = await _load_user_with_subscription(db, user.id)
    if not requester:
        return EffectiveSubscriptionResult(
            active=False,
            source=None,
            subscription=None,
            tariff=None,
            owner_user=None,
            requester_user=None,
        )

    personal_subscription = requester.subscription
    if is_subscription_active(personal_subscription):
        return EffectiveSubscriptionResult(
            active=True,
            source='personal',
            subscription=personal_subscription,
            tariff=personal_subscription.tariff if personal_subscription else None,
            owner_user=requester,
            requester_user=requester,
        )

    family_ctx = await get_access_context(db, requester)
    if (
        family_ctx.role == 'member'
        and family_ctx.owner
        and family_ctx.subscription
        and is_subscription_active(family_ctx.subscription)
    ):
        return EffectiveSubscriptionResult(
            active=True,
            source='family_owner',
            subscription=family_ctx.subscription,
            tariff=family_ctx.tariff,
            owner_user=family_ctx.owner,
            requester_user=requester,
        )

    return EffectiveSubscriptionResult(
        active=False,
        source=None,
        subscription=personal_subscription,
        tariff=personal_subscription.tariff if personal_subscription else None,
        owner_user=None,
        requester_user=requester,
    )
