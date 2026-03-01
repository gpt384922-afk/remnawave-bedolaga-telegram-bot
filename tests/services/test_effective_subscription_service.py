from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import effective_subscription_service as effective_service
from app.services.family_service import FamilyAccessContext


def _build_subscription(*, days_offset: int, tariff: object | None = None, sub_id: int = 1):
    return SimpleNamespace(
        id=sub_id,
        status='active',
        end_date=datetime.now(UTC) + timedelta(days=days_offset),
        is_cancelled=False,
        tariff=tariff,
        tariff_id=getattr(tariff, 'id', None),
    )


async def test_effective_subscription_member_uses_owner_subscription(monkeypatch):
    requester = SimpleNamespace(id=18, subscription=None)
    owner_tariff = SimpleNamespace(id=10, name='Family Plus')
    owner_subscription = _build_subscription(days_offset=15, tariff=owner_tariff, sub_id=101)
    owner = SimpleNamespace(id=1, subscription=owner_subscription)
    family_ctx = FamilyAccessContext(
        requester=requester,
        owner=owner,
        subscription=owner_subscription,
        tariff=owner_tariff,
        group=SimpleNamespace(id=77),
        role='member',
    )

    monkeypatch.setattr(
        effective_service,
        '_load_user_with_subscription',
        AsyncMock(return_value=requester),
    )
    monkeypatch.setattr(
        effective_service,
        'get_access_context',
        AsyncMock(return_value=family_ctx),
    )

    result = await effective_service.resolve_effective_subscription(
        AsyncMock(spec=AsyncSession),
        SimpleNamespace(id=requester.id),
    )

    assert result.active is True
    assert result.source == 'family_owner'
    assert result.subscription is owner_subscription
    assert result.tariff is owner_tariff
    assert result.owner_user is owner
    assert result.requester_user is requester
    assert result.expires_at == owner_subscription.end_date


async def test_effective_subscription_member_false_when_owner_subscription_inactive(monkeypatch):
    requester = SimpleNamespace(id=18, subscription=None)
    owner_tariff = SimpleNamespace(id=11, name='Family Basic')
    owner_subscription = _build_subscription(days_offset=-1, tariff=owner_tariff, sub_id=102)
    owner = SimpleNamespace(id=1, subscription=owner_subscription)
    family_ctx = FamilyAccessContext(
        requester=requester,
        owner=owner,
        subscription=owner_subscription,
        tariff=owner_tariff,
        group=SimpleNamespace(id=88),
        role='member',
    )

    monkeypatch.setattr(
        effective_service,
        '_load_user_with_subscription',
        AsyncMock(return_value=requester),
    )
    monkeypatch.setattr(
        effective_service,
        'get_access_context',
        AsyncMock(return_value=family_ctx),
    )

    result = await effective_service.resolve_effective_subscription(
        AsyncMock(spec=AsyncSession),
        SimpleNamespace(id=requester.id),
    )

    assert result.active is False
    assert result.source is None
    assert result.subscription is None
    assert result.tariff is None
    assert result.owner_user is None
    assert result.requester_user is requester
    assert result.expires_at is None


async def test_effective_subscription_personal_priority_over_family(monkeypatch):
    personal_tariff = SimpleNamespace(id=3, name='Personal Premium')
    personal_subscription = _build_subscription(days_offset=10, tariff=personal_tariff, sub_id=103)
    requester = SimpleNamespace(id=18, subscription=personal_subscription)

    monkeypatch.setattr(
        effective_service,
        '_load_user_with_subscription',
        AsyncMock(return_value=requester),
    )
    access_context_mock = AsyncMock()
    monkeypatch.setattr(effective_service, 'get_access_context', access_context_mock)

    result = await effective_service.resolve_effective_subscription(
        AsyncMock(spec=AsyncSession),
        SimpleNamespace(id=requester.id),
    )

    assert result.active is True
    assert result.source == 'personal'
    assert result.subscription is personal_subscription
    assert result.tariff is personal_tariff
    assert result.owner_user is requester
    assert result.requester_user is requester
    assert access_context_mock.await_count == 0


async def test_effective_subscription_member_false_after_leave_family(monkeypatch):
    requester = SimpleNamespace(id=18, subscription=None)
    family_ctx_after_leave = FamilyAccessContext(
        requester=requester,
        owner=None,
        subscription=None,
        tariff=None,
        group=None,
        role=None,
    )

    monkeypatch.setattr(
        effective_service,
        '_load_user_with_subscription',
        AsyncMock(return_value=requester),
    )
    monkeypatch.setattr(
        effective_service,
        'get_access_context',
        AsyncMock(return_value=family_ctx_after_leave),
    )

    result = await effective_service.resolve_effective_subscription(
        AsyncMock(spec=AsyncSession),
        SimpleNamespace(id=requester.id),
    )

    assert result.active is False
    assert result.source is None
    assert result.subscription is None
    assert result.tariff is None
    assert result.owner_user is None
    assert result.requester_user is requester
