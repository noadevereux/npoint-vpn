from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import UserDataLimitResetStrategy, UserResponse, UserStatus
from config import (
    ACTIVE_STATUS_TEXT,
    DISABLED_STATUS_TEXT,
    EXPIRED_STATUS_TEXT,
    LIMITED_STATUS_TEXT,
    ONHOLD_STATUS_TEXT,
)


STATUS_LABELS: Dict[UserStatus, str] = {
    UserStatus.active: ACTIVE_STATUS_TEXT,
    UserStatus.disabled: DISABLED_STATUS_TEXT,
    UserStatus.expired: EXPIRED_STATUS_TEXT,
    UserStatus.limited: LIMITED_STATUS_TEXT,
    UserStatus.on_hold: ONHOLD_STATUS_TEXT,
}


class PortalSubscriptionLinks(BaseModel):
    universal: str
    clash: str
    clash_meta: str
    sing_box: str
    outline: str
    v2ray: str
    v2ray_json: str


class PortalUserResponse(BaseModel):
    username: str
    email: Optional[EmailStr]
    status: UserStatus
    status_label: str
    used_traffic: int
    lifetime_used_traffic: int
    data_limit: Optional[int]
    data_limit_reset_strategy: UserDataLimitResetStrategy
    expire: Optional[int]
    expire_at: Optional[datetime]
    on_hold_timeout: Optional[datetime]
    on_hold_expire_duration: Optional[int]
    subscription: PortalSubscriptionLinks
    links: List[str]
    created_at: datetime
    subscription_last_updated_at: Optional[datetime]
    usage_percent: Optional[float]

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_user(cls, user: UserResponse) -> "PortalUserResponse":
        base_url = user.subscription_url.rstrip("/")
        subscription = PortalSubscriptionLinks(
            universal=base_url,
            clash=f"{base_url}/clash",
            clash_meta=f"{base_url}/clash-meta",
            sing_box=f"{base_url}/sing-box",
            outline=f"{base_url}/outline",
            v2ray=f"{base_url}/v2ray",
            v2ray_json=f"{base_url}/v2ray-json",
        )

        expire_at: Optional[datetime]
        if user.expire:
            expire_at = datetime.utcfromtimestamp(user.expire)
        else:
            expire_at = None

        if user.data_limit and user.data_limit > 0:
            usage_percent = round((user.used_traffic / user.data_limit) * 100, 2)
        else:
            usage_percent = None

        return cls(
            username=user.username,
            email=user.email,
            status=user.status,
            status_label=STATUS_LABELS.get(user.status, user.status.value.title()),
            used_traffic=user.used_traffic,
            lifetime_used_traffic=user.lifetime_used_traffic,
            data_limit=user.data_limit,
            data_limit_reset_strategy=user.data_limit_reset_strategy,
            expire=user.expire,
            expire_at=expire_at,
            on_hold_timeout=user.on_hold_timeout,
            on_hold_expire_duration=user.on_hold_expire_duration,
            subscription=subscription,
            links=user.links,
            created_at=user.created_at,
            subscription_last_updated_at=user.sub_updated_at,
            usage_percent=usage_percent,
        )


class MagicLinkRequest(BaseModel):
    email: EmailStr


class MessageResponse(BaseModel):
    detail: str
