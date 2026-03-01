from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import UserNotification


async def create_user_notification(
    db: AsyncSession,
    *,
    user_id: int,
    notification_type: str,
    title: str,
    body: str | None = None,
    payload: dict | None = None,
) -> UserNotification:
    notification = UserNotification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        body=body,
        payload=payload or {},
    )
    db.add(notification)
    await db.flush()
    return notification


async def get_user_notifications(
    db: AsyncSession,
    *,
    user_id: int,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[UserNotification], int]:
    query = (
        select(UserNotification)
        .where(UserNotification.user_id == user_id)
        .order_by(UserNotification.created_at.desc())
        .offset(max(0, offset))
        .limit(max(1, min(limit, 100)))
    )
    total_query = select(func.count(UserNotification.id)).where(UserNotification.user_id == user_id)

    rows = (await db.execute(query)).scalars().all()
    total = int((await db.execute(total_query)).scalar() or 0)
    return rows, total


async def mark_user_notification_read(
    db: AsyncSession,
    *,
    notification_id: int,
    user_id: int,
) -> bool:
    notification = await db.get(UserNotification, notification_id)
    if not notification or notification.user_id != user_id:
        return False

    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
        await db.flush()
    return True


async def mark_all_user_notifications_read(db: AsyncSession, *, user_id: int) -> int:
    query = select(UserNotification).where(UserNotification.user_id == user_id, UserNotification.read_at.is_(None))
    rows = (await db.execute(query)).scalars().all()
    now = datetime.now(UTC)
    for row in rows:
        row.read_at = now
    await db.flush()
    return len(rows)
