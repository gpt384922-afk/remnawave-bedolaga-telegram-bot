from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.services.family_service import (
    accept_family_invite,
    create_family_invite,
    decline_family_invite,
    get_family_overview,
    leave_family,
    remove_family_member,
    revoke_family_invite,
)

from ..dependencies import get_cabinet_db, get_current_cabinet_user


router = APIRouter(prefix='/subscription/family', tags=['Cabinet Family'])


class FamilyInviteRequest(BaseModel):
    tg_username: str = Field(..., min_length=2, max_length=255)


@router.get('')
async def family_overview(
    user: User = Depends(get_current_cabinet_user),
    db: AsyncSession = Depends(get_cabinet_db),
):
    return await get_family_overview(db, user)


@router.post('/invite')
async def invite_family_member(
    request: FamilyInviteRequest,
    user: User = Depends(get_current_cabinet_user),
    db: AsyncSession = Depends(get_cabinet_db),
):
    invite = await create_family_invite(db, user, request.tg_username)
    return {
        'success': True,
        'invite_id': invite.id,
        'status': invite.status,
    }


@router.post('/invite/{invite_id}/revoke')
async def revoke_invite(
    invite_id: int,
    user: User = Depends(get_current_cabinet_user),
    db: AsyncSession = Depends(get_cabinet_db),
):
    invite = await revoke_family_invite(db, user, invite_id)
    return {'success': True, 'invite_id': invite.id, 'status': invite.status}


@router.post('/members/{member_user_id}/remove')
async def remove_member(
    member_user_id: int,
    user: User = Depends(get_current_cabinet_user),
    db: AsyncSession = Depends(get_cabinet_db),
):
    await remove_family_member(db, user, member_user_id)
    return {'success': True}


@router.post('/leave')
async def leave_current_family(
    user: User = Depends(get_current_cabinet_user),
    db: AsyncSession = Depends(get_cabinet_db),
):
    await leave_family(db, user)
    return {'success': True}


@router.post('/invites/{invite_id}/accept')
async def accept_invite(
    invite_id: int,
    user: User = Depends(get_current_cabinet_user),
    db: AsyncSession = Depends(get_cabinet_db),
):
    invite = await accept_family_invite(db, user, invite_id)
    return {'success': True, 'invite_id': invite.id, 'status': invite.status}


@router.post('/invites/{invite_id}/decline')
async def decline_invite(
    invite_id: int,
    user: User = Depends(get_current_cabinet_user),
    db: AsyncSession = Depends(get_cabinet_db),
):
    invite = await decline_family_invite(db, user, invite_id)
    return {'success': True, 'invite_id': invite.id, 'status': invite.status}
