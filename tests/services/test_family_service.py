from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.cabinet.routes.subscription import delete_device
from app.services import family_service
from app.services.family_service import FamilyAccessContext


class FakeScalarResult:
    def __init__(self, value=None, values=None):
        self._value = value
        self._values = values if values is not None else ([value] if value is not None else [])

    def scalars(self):
        return self

    def first(self):
        return self._value

    def all(self):
        return self._values

    def scalar_one_or_none(self):
        return self._value


def _make_owner(*, family_enabled: bool, family_max_members: int):
    tariff = SimpleNamespace(family_enabled=family_enabled, family_max_members=family_max_members)
    subscription = SimpleNamespace(id=101, tariff=tariff, device_limit=3)
    owner = SimpleNamespace(
        id=1,
        username='owner',
        telegram_id=111,
        subscription=subscription,
        remnawave_uuid='owner-uuid',
    )
    return owner


async def test_create_family_invite_rejected_when_tariff_disables_family(monkeypatch):
    owner = _make_owner(family_enabled=False, family_max_members=0)
    monkeypatch.setattr(family_service, '_load_user', AsyncMock(return_value=owner))

    db = AsyncMock(spec=AsyncSession)

    with pytest.raises(HTTPException) as exc:
        await family_service.create_family_invite(db, SimpleNamespace(id=owner.id), '@member')

    assert exc.value.status_code == 400
    assert 'Family access is not available' in str(exc.value.detail)


@pytest.mark.parametrize(
    'invitee',
    [
        None,
        SimpleNamespace(id=2, username='member', telegram_id=None),
    ],
)
async def test_create_family_invite_requires_existing_bot_user(monkeypatch, invitee):
    owner = _make_owner(family_enabled=True, family_max_members=3)
    monkeypatch.setattr(family_service, '_load_user', AsyncMock(return_value=owner))

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(side_effect=[FakeScalarResult(value=invitee)])

    with pytest.raises(HTTPException) as exc:
        await family_service.create_family_invite(db, SimpleNamespace(id=owner.id), '@member')

    assert exc.value.status_code == 400
    assert exc.value.detail == 'User must start the bot first'


async def test_create_family_invite_rejected_when_max_members_reached(monkeypatch):
    owner = _make_owner(family_enabled=True, family_max_members=2)
    invitee = SimpleNamespace(id=2, username='member', telegram_id=222)
    group = SimpleNamespace(id=77, owner_user_id=owner.id, subscription_id=owner.subscription.id)

    monkeypatch.setattr(family_service, '_load_user', AsyncMock(return_value=owner))
    monkeypatch.setattr(family_service, '_in_active_family', AsyncMock(return_value=False))
    monkeypatch.setattr(family_service, '_ensure_group', AsyncMock(return_value=group))
    monkeypatch.setattr(family_service, '_active_member_count', AsyncMock(return_value=1))

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(
        side_effect=[
            FakeScalarResult(value=invitee),  # invitee lookup
            FakeScalarResult(value=group),  # group lock
        ]
    )

    with pytest.raises(HTTPException) as exc:
        await family_service.create_family_invite(db, SimpleNamespace(id=owner.id), '@member')

    assert exc.value.status_code == 400
    assert exc.value.detail == 'Family member limit reached'


async def test_accept_family_invite_rejected_if_user_in_another_family(monkeypatch):
    owner = _make_owner(family_enabled=True, family_max_members=5)
    owner.remnawave_uuid = None
    group = SimpleNamespace(id=88, owner_user_id=owner.id)
    invite = SimpleNamespace(
        id=10,
        invitee_user_id=2,
        family_group_id=group.id,
        inviter_user_id=owner.id,
        status='pending',
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=1),
        decided_at=None,
    )
    member_user = SimpleNamespace(id=2, username='member', telegram_id=222)

    monkeypatch.setattr(family_service, '_invite_for_update', AsyncMock(return_value=invite))
    monkeypatch.setattr(family_service, '_load_user', AsyncMock(return_value=owner))
    monkeypatch.setattr(family_service, '_in_active_family', AsyncMock(return_value=True))

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(side_effect=[FakeScalarResult(value=group)])

    with pytest.raises(HTTPException) as exc:
        await family_service.accept_family_invite(db, member_user, invite.id)

    assert exc.value.status_code == 400
    assert exc.value.detail == 'User is already in another family'


async def test_accept_family_invite_marks_statuses(monkeypatch):
    owner = _make_owner(family_enabled=True, family_max_members=5)
    owner.remnawave_uuid = None
    group = SimpleNamespace(id=50, owner_user_id=owner.id)
    invite = SimpleNamespace(
        id=11,
        invitee_user_id=2,
        family_group_id=group.id,
        inviter_user_id=owner.id,
        status='pending',
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=1),
        decided_at=None,
    )
    member_user = SimpleNamespace(id=2, username='member', telegram_id=222)

    monkeypatch.setattr(family_service, '_invite_for_update', AsyncMock(return_value=invite))
    monkeypatch.setattr(family_service, '_load_user', AsyncMock(return_value=owner))
    monkeypatch.setattr(family_service, '_in_active_family', AsyncMock(return_value=False))
    monkeypatch.setattr(family_service, '_active_member_count', AsyncMock(return_value=0))
    monkeypatch.setattr(family_service, '_notify', AsyncMock())
    monkeypatch.setattr(family_service, '_send_tg', AsyncMock())

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(
        side_effect=[
            FakeScalarResult(value=group),  # group for update
            FakeScalarResult(value=None),  # family member lookup
        ]
    )
    db.add = MagicMock()

    result = await family_service.accept_family_invite(db, member_user, invite.id)

    assert result is invite
    assert invite.status == 'accepted'
    assert invite.decided_at is not None
    assert db.add.called


async def test_decline_family_invite_marks_statuses(monkeypatch):
    owner = _make_owner(family_enabled=True, family_max_members=4)
    invite = SimpleNamespace(
        id=12,
        invitee_user_id=2,
        family_group_id=90,
        inviter_user_id=owner.id,
        status='pending',
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=1),
        decided_at=None,
    )
    member_row = SimpleNamespace(status='invited', removed_at=None)
    member_user = SimpleNamespace(id=2, username='member', telegram_id=222)
    group = SimpleNamespace(id=invite.family_group_id, owner_user_id=owner.id)

    monkeypatch.setattr(family_service, '_invite_for_update', AsyncMock(return_value=invite))
    monkeypatch.setattr(family_service, '_load_user', AsyncMock(return_value=owner))
    monkeypatch.setattr(family_service, '_notify', AsyncMock())
    monkeypatch.setattr(family_service, '_send_tg', AsyncMock())

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(side_effect=[FakeScalarResult(value=member_row)])
    db.get = AsyncMock(return_value=group)

    result = await family_service.decline_family_invite(db, member_user, invite.id)

    assert result is invite
    assert invite.status == 'declined'
    assert invite.decided_at is not None
    assert member_row.status == 'declined'


async def test_member_cannot_delete_owner_device(monkeypatch):
    owner = SimpleNamespace(id=1, remnawave_uuid='owner-uuid', subscription=SimpleNamespace(device_limit=3))
    member_user = SimpleNamespace(id=2)
    group = SimpleNamespace(id=10)
    ctx = FamilyAccessContext(
        requester=member_user,
        owner=owner,
        subscription=owner.subscription,
        tariff=None,
        group=group,
        role='member',
    )

    monkeypatch.setattr('app.cabinet.routes.subscription.get_access_context', AsyncMock(return_value=ctx))

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(side_effect=[FakeScalarResult(value=SimpleNamespace(owner_user_id=owner.id))])

    with pytest.raises(HTTPException) as exc:
        await delete_device('hwid-x', member_user, db)

    assert exc.value.status_code == 403
    assert exc.value.detail == 'Family member cannot delete owner devices'


async def test_owner_can_delete_member_device(monkeypatch):
    owner = SimpleNamespace(id=1, remnawave_uuid='owner-uuid', subscription=SimpleNamespace(device_limit=3))
    requester = SimpleNamespace(id=1)
    group = SimpleNamespace(id=10)
    device_row = SimpleNamespace(hwid='hwid-x')
    ctx = FamilyAccessContext(
        requester=requester,
        owner=owner,
        subscription=owner.subscription,
        tariff=None,
        group=group,
        role='owner',
    )

    monkeypatch.setattr('app.cabinet.routes.subscription.get_access_context', AsyncMock(return_value=ctx))

    class FakeApiClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def _make_request(self, method, path, data=None):
            return {'ok': True}

    class FakeService:
        def get_api_client(self):
            return FakeApiClient()

    monkeypatch.setattr('app.services.remnawave_service.RemnaWaveService', lambda: FakeService())

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(side_effect=[FakeScalarResult(value=device_row)])
    db.delete = AsyncMock()

    result = await delete_device('hwid-x', requester, db)

    assert result['success'] is True
    db.delete.assert_awaited_once_with(device_row)
