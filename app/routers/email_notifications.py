from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import crud, get_db
from app.db.models import EmailNotificationPreference, EmailSMTPSettings
from app.models.admin import Admin
from app.models.email_notification import (
    EmailNotificationConfigResponse,
    EmailNotificationConfigUpdate,
    EmailNotificationPreferenceModel,
    EmailSMTPSettingsResponse,
    EmailNotificationTrigger,
)
from app.utils import responses
from app.utils.email_notifications import invalidate_email_notifications_cache


router = APIRouter(
    tags=["Email Notifications"],
    prefix="/api",
    responses={401: responses._401, 403: responses._403},
)


def _serialize_preferences(
    preferences: list[EmailNotificationPreference],
) -> list[EmailNotificationPreferenceModel]:
    return sorted(
        [EmailNotificationPreferenceModel.model_validate(pref) for pref in preferences],
        key=lambda pref: pref.trigger.value,
    )


def _serialize_smtp(settings: EmailSMTPSettings | None) -> EmailSMTPSettingsResponse | None:
    if not settings:
        return None

    smtp = EmailSMTPSettingsResponse.model_validate(settings)
    smtp.has_password = bool(getattr(settings, "password", None))
    return smtp


@router.get(
    "/email/notifications",
    response_model=EmailNotificationConfigResponse,
)
def get_email_notification_config(
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    settings = crud.get_email_smtp_settings(db)
    preferences = crud.get_email_notification_preferences(db)
    return EmailNotificationConfigResponse(
        smtp=_serialize_smtp(settings),
        preferences=_serialize_preferences(preferences),
    )


@router.put(
    "/email/notifications",
    response_model=EmailNotificationConfigResponse,
)
def update_email_notification_config(
    payload: EmailNotificationConfigUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    existing_settings = crud.get_email_smtp_settings(db)
    smtp_payload = payload.smtp.model_dump(exclude_none=True)
    if smtp_payload.get("username") == "":
        smtp_payload["username"] = None
    if smtp_payload.get("from_name") == "":
        smtp_payload["from_name"] = None

    password = smtp_payload.get("password")
    if password is not None:
        smtp_payload["password"] = password or None
    elif not existing_settings:
        # Ensure a record is created with an explicit password value when none existed before.
        smtp_payload["password"] = None

    settings = crud.upsert_email_smtp_settings(db, smtp_payload)

    preference_payload = {trigger: False for trigger in EmailNotificationTrigger}
    preference_payload.update(
        {pref.trigger: pref.enabled for pref in payload.preferences}
    )
    preferences = crud.update_email_notification_preferences(db, preference_payload)

    invalidate_email_notifications_cache()

    return EmailNotificationConfigResponse(
        smtp=_serialize_smtp(settings),
        preferences=_serialize_preferences(preferences),
    )
