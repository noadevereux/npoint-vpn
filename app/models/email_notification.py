from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class EmailNotificationTrigger(str, Enum):
    user_created = "user_created"
    user_updated = "user_updated"
    user_deleted = "user_deleted"
    user_limited = "user_limited"
    user_expired = "user_expired"
    user_enabled = "user_enabled"
    user_disabled = "user_disabled"
    data_usage_reset = "data_usage_reset"
    data_reset_by_next = "data_reset_by_next"
    subscription_revoked = "subscription_revoked"
    reached_usage_percent = "reached_usage_percent"
    reached_days_left = "reached_days_left"


class EmailSMTPSettingsBase(BaseModel):
    host: str
    port: int = Field(ge=1, le=65535, default=587)
    username: Optional[str] = None
    use_tls: bool = True
    use_ssl: bool = False
    from_email: EmailStr
    from_name: Optional[str] = None

    @field_validator("use_ssl")
    @classmethod
    def validate_tls_ssl(cls, use_ssl, values):
        use_tls = values.data.get("use_tls", True)
        if use_ssl and use_tls:
            raise ValueError("use_ssl and use_tls cannot both be enabled")
        return use_ssl


class EmailSMTPSettingsResponse(EmailSMTPSettingsBase):
    has_password: bool = False
    model_config = ConfigDict(from_attributes=True)


class EmailSMTPSettingsUpdate(EmailSMTPSettingsBase):
    password: Optional[str] = None


class EmailNotificationPreferenceModel(BaseModel):
    trigger: EmailNotificationTrigger
    enabled: bool = False
    model_config = ConfigDict(from_attributes=True)


class EmailNotificationConfigResponse(BaseModel):
    smtp: Optional[EmailSMTPSettingsResponse] = None
    preferences: List[EmailNotificationPreferenceModel]


class EmailNotificationConfigUpdate(BaseModel):
    smtp: EmailSMTPSettingsUpdate
    preferences: List[EmailNotificationPreferenceModel]
