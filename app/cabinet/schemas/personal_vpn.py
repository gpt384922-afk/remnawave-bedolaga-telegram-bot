from datetime import datetime

from pydantic import BaseModel, Field


class PersonalVPNNodeInfo(BaseModel):
    id: str
    name: str | None = None
    online: bool = False
    is_disabled: bool | None = None


class PersonalVPNSubUserInfo(BaseModel):
    id: int
    remnawave_user_id: str
    expires_at: datetime
    device_limit: int
    traffic_limit_bytes: int
    traffic_limit_gb: float
    status: str
    traffic_used_bytes: int
    traffic_used_gb: float
    devices_used: int
    subscription_link: str | None = None
    created_at: datetime


class PersonalVPNOverviewResponse(BaseModel):
    has_instance: bool
    instance_id: int | None = None
    status: str | None = None
    expires_at: datetime | None = None
    max_users: int = 0
    current_user_count: int = 0
    restart_cooldown_remaining_seconds: int = 0
    last_restart_at: datetime | None = None
    node: PersonalVPNNodeInfo | None = None
    sub_users: list[PersonalVPNSubUserInfo] = Field(default_factory=list)


class PersonalVPNRestartResponse(BaseModel):
    success: bool = True
    last_restart_at: datetime


class PersonalVPNCreateSubUserRequest(BaseModel):
    expires_at: datetime
    device_limit: int = Field(..., ge=1)
    traffic_limit_gb: float = Field(..., ge=0)


class PersonalVPNCreateSubUserResponse(BaseModel):
    success: bool = True
    sub_user: PersonalVPNSubUserInfo


class PersonalVPNDeleteSubUserResponse(BaseModel):
    success: bool = True


class AdminPersonalVPNAssignRequest(BaseModel):
    owner_user_id: int | None = None
    owner_username: str | None = None
    owner_telegram_id: int | None = None
    remnawave_node_id: str
    remnawave_squad_id: str
    expires_at: datetime
    max_users: int = Field(..., ge=1)


class AdminPersonalVPNUpdateRequest(BaseModel):
    expires_at: datetime | None = None
    max_users: int | None = Field(default=None, ge=1)


class AdminPersonalVPNInstanceResponse(BaseModel):
    id: int
    owner_user_id: int
    remnawave_node_id: str
    remnawave_squad_id: str
    expires_at: datetime
    status: str
    max_users: int
    last_restart_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AdminPersonalVPNNodesResponse(BaseModel):
    items: list[dict]
    total: int


class AdminPersonalVPNSquadsResponse(BaseModel):
    items: list[dict]
    total: int

