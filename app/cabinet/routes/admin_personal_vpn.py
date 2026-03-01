from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.cabinet.schemas.personal_vpn import (
    AdminPersonalVPNAssignRequest,
    AdminPersonalVPNInstanceResponse,
    AdminPersonalVPNNodesResponse,
    AdminPersonalVPNSquadsResponse,
    AdminPersonalVPNUpdateRequest,
)
from app.database.models import User
from app.services.personal_vpn_service import (
    assign_personal_vpn_instance,
    list_available_nodes,
    list_squads,
    update_personal_vpn_instance,
)

from ..dependencies import get_cabinet_db, require_permission


router = APIRouter(prefix='/admin/personal_vpn', tags=['Cabinet Admin Personal VPN'])


@router.get('/nodes', response_model=AdminPersonalVPNNodesResponse)
async def get_nodes(
    admin: User = Depends(require_permission('remnawave:read')),
):
    _ = admin
    items = await list_available_nodes()
    return AdminPersonalVPNNodesResponse(items=items, total=len(items))


@router.get('/squads', response_model=AdminPersonalVPNSquadsResponse)
async def get_squads(
    admin: User = Depends(require_permission('remnawave:read')),
):
    _ = admin
    items = await list_squads()
    return AdminPersonalVPNSquadsResponse(items=items, total=len(items))


@router.post('/assign', response_model=AdminPersonalVPNInstanceResponse, status_code=status.HTTP_201_CREATED)
async def assign_instance(
    payload: AdminPersonalVPNAssignRequest,
    admin: User = Depends(require_permission('remnawave:manage')),
    db: AsyncSession = Depends(get_cabinet_db),
):
    _ = admin

    if payload.owner_user_id is None and payload.owner_username is None and payload.owner_telegram_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='owner_user_id or owner_username or owner_telegram_id is required',
        )

    instance = await assign_personal_vpn_instance(
        db,
        owner_user_id=payload.owner_user_id,
        owner_username=payload.owner_username,
        owner_telegram_id=payload.owner_telegram_id,
        remnawave_node_id=payload.remnawave_node_id,
        remnawave_squad_id=payload.remnawave_squad_id,
        expires_at=payload.expires_at,
        max_users=payload.max_users,
    )

    return AdminPersonalVPNInstanceResponse.model_validate(instance, from_attributes=True)


@router.patch('/{instance_id}', response_model=AdminPersonalVPNInstanceResponse)
async def update_instance(
    instance_id: int,
    payload: AdminPersonalVPNUpdateRequest,
    admin: User = Depends(require_permission('remnawave:manage')),
    db: AsyncSession = Depends(get_cabinet_db),
):
    _ = admin

    if payload.expires_at is None and payload.max_users is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='No fields provided for update')

    instance = await update_personal_vpn_instance(
        db,
        instance_id=instance_id,
        expires_at=payload.expires_at,
        max_users=payload.max_users,
    )

    return AdminPersonalVPNInstanceResponse.model_validate(instance, from_attributes=True)

