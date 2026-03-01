from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.cabinet.schemas.personal_vpn import (
    PersonalVPNCreateSubUserRequest,
    PersonalVPNCreateSubUserResponse,
    PersonalVPNDeleteSubUserResponse,
    PersonalVPNOverviewResponse,
    PersonalVPNRestartResponse,
)
from app.database.models import User
from app.services.personal_vpn_service import (
    create_personal_vpn_sub_user,
    delete_personal_vpn_sub_user,
    get_personal_vpn_overview,
    restart_personal_vpn_node,
)

from ..dependencies import get_cabinet_db, get_current_cabinet_user


router = APIRouter(prefix='/personal_vpn', tags=['Cabinet Personal VPN'])


@router.get('', response_model=PersonalVPNOverviewResponse)
async def personal_vpn_overview(
    user: User = Depends(get_current_cabinet_user),
    db: AsyncSession = Depends(get_cabinet_db),
):
    return await get_personal_vpn_overview(db, user)


@router.post('/restart', response_model=PersonalVPNRestartResponse)
async def restart_personal_vpn(
    user: User = Depends(get_current_cabinet_user),
    db: AsyncSession = Depends(get_cabinet_db),
):
    instance = await restart_personal_vpn_node(db, user)
    return PersonalVPNRestartResponse(last_restart_at=instance.last_restart_at)


@router.post('/users', response_model=PersonalVPNCreateSubUserResponse)
async def create_sub_user(
    payload: PersonalVPNCreateSubUserRequest,
    user: User = Depends(get_current_cabinet_user),
    db: AsyncSession = Depends(get_cabinet_db),
):
    sub_user = await create_personal_vpn_sub_user(
        db,
        user,
        expires_at=payload.expires_at,
        device_limit=payload.device_limit,
        traffic_limit_gb=payload.traffic_limit_gb,
    )
    return PersonalVPNCreateSubUserResponse(sub_user=sub_user)


@router.delete('/users/{sub_user_id}', response_model=PersonalVPNDeleteSubUserResponse)
async def delete_sub_user(
    sub_user_id: int,
    user: User = Depends(get_current_cabinet_user),
    db: AsyncSession = Depends(get_cabinet_db),
):
    await delete_personal_vpn_sub_user(db, user, sub_user_id=sub_user_id)
    return PersonalVPNDeleteSubUserResponse()

