from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr
from typing import Dict, Optional

import smtplib

from app import logger
from app.db import GetDB, crud
from app.models.email_notification import EmailNotificationTrigger
from app.models.user import UserResponse


@dataclass
class SMTPSettings:
    host: str
    port: int
    username: Optional[str]
    password: Optional[str]
    use_tls: bool
    use_ssl: bool
    from_email: str
    from_name: Optional[str]
    updated_at: datetime


class EmailNotificationManager:
    def __init__(self) -> None:
        self._settings: Optional[SMTPSettings] = None
        self._preferences: Dict[EmailNotificationTrigger, bool] = {}
        self._last_loaded: Optional[datetime] = None

    def invalidate(self) -> None:
        self._settings = None
        self._preferences = {}
        self._last_loaded = None

    def _load_configuration(self) -> None:
        with GetDB() as db:
            settings = crud.get_email_smtp_settings(db)
            preferences = crud.get_email_notification_preferences(db)

        if settings:
            self._settings = SMTPSettings(
                host=settings.host,
                port=settings.port,
                username=settings.username,
                password=settings.password,
                use_tls=settings.use_tls,
                use_ssl=settings.use_ssl,
                from_email=settings.from_email,
                from_name=settings.from_name,
                updated_at=settings.updated_at or datetime.utcnow(),
            )
        else:
            self._settings = None

        self._preferences = {pref.trigger: pref.enabled for pref in preferences}
        self._last_loaded = datetime.utcnow()

    def _ensure_configuration(self) -> None:
        if self._settings is None or self._preferences is None:
            self._load_configuration()

    def is_enabled(self, trigger: EmailNotificationTrigger) -> bool:
        self._ensure_configuration()
        return bool(self._preferences.get(trigger))

    def send(
        self,
        trigger: EmailNotificationTrigger,
        user: UserResponse,
        context: Optional[Dict[str, object]] = None,
    ) -> None:
        if not user.email:
            return

        self._ensure_configuration()

        if not self._settings or not self._preferences.get(trigger):
            return

        context = context or {}
        subject, body = self._render(trigger, user, context)
        if not subject or not body:
            return

        message = EmailMessage()
        message["Subject"] = subject
        message["To"] = user.email
        from_name = self._settings.from_name or self._settings.from_email
        message["From"] = formataddr((from_name, self._settings.from_email))
        message.set_content(body)

        self._deliver_email(message, f"email notification for trigger {trigger.value}")

    def send_magic_link(
        self,
        *,
        email: str,
        username: Optional[str],
        link: str,
        expires_in_minutes: int,
    ) -> bool:
        identifier = username or email
        if not email:
            return False

        self._ensure_configuration()
        if not self._settings:
            logger.warning("Magic link email skipped because SMTP settings are not configured")
            return False

        message = EmailMessage()
        message["Subject"] = "Your VPN dashboard sign-in link"
        message["To"] = email
        from_name = self._settings.from_name or self._settings.from_email
        message["From"] = formataddr((from_name, self._settings.from_email))
        message.set_content(
            self._wrap_message(
                identifier,
                [
                    "Use the secure link below to open your dashboard:",
                    link,
                    f"This link expires in {expires_in_minutes} minute(s).",
                    "If you did not request this email, you can safely ignore it.",
                ],
            )
        )

        return self._deliver_email(message, "magic link email")

    def _login_if_required(self, smtp: smtplib.SMTP) -> None:
        if self._settings and self._settings.username and self._settings.password:
            smtp.login(self._settings.username, self._settings.password)

    def _deliver_email(self, message: EmailMessage, context: str) -> bool:
        if not self._settings:
            logger.warning("Cannot send %s because SMTP settings are not configured", context)
            return False

        try:
            if self._settings.use_ssl:
                with smtplib.SMTP_SSL(self._settings.host, self._settings.port) as smtp:
                    self._login_if_required(smtp)
                    smtp.send_message(message)
            else:
                with smtplib.SMTP(self._settings.host, self._settings.port) as smtp:
                    if self._settings.use_tls:
                        smtp.starttls()
                    self._login_if_required(smtp)
                    smtp.send_message(message)
            return True
        except Exception:
            logger.exception("Failed to send %s", context)
            return False

    def _render(
        self, trigger: EmailNotificationTrigger, user: UserResponse, context: Dict[str, object]
    ) -> tuple[str, str]:
        identifier = user.email or user.username
        base_details = self._format_user_details(user)

        if trigger == EmailNotificationTrigger.user_created:
            by = context.get("by")
            subject = "Your VPN access is ready"
            body = self._wrap_message(
                identifier,
                [
                    "Your account has been created successfully.",
                    base_details,
                    self._format_actor(by),
                ],
            )
        elif trigger == EmailNotificationTrigger.user_updated:
            by = context.get("by")
            subject = "Your VPN account was updated"
            body = self._wrap_message(
                identifier,
                [
                    "Your account settings were updated.",
                    base_details,
                    self._format_actor(by),
                ],
            )
        elif trigger == EmailNotificationTrigger.user_deleted:
            by = context.get("by")
            subject = "Your VPN account was removed"
            body = self._wrap_message(
                identifier,
                [
                    "Your access has been revoked and the account was removed from the system.",
                    self._format_actor(by),
                ],
            )
        elif trigger == EmailNotificationTrigger.user_limited:
            subject = "Your VPN account reached its limit"
            body = self._wrap_message(
                identifier,
                [
                    "Your account is limited because the allocated data has been used.",
                    base_details,
                ],
            )
        elif trigger == EmailNotificationTrigger.user_expired:
            subject = "Your VPN account expired"
            body = self._wrap_message(
                identifier,
                [
                    "Your subscription has expired.",
                    base_details,
                ],
            )
        elif trigger == EmailNotificationTrigger.user_enabled:
            by = context.get("by")
            subject = "Your VPN access is active again"
            body = self._wrap_message(
                identifier,
                [
                    "Your account has been enabled.",
                    base_details,
                    self._format_actor(by),
                ],
            )
        elif trigger == EmailNotificationTrigger.user_disabled:
            by = context.get("by")
            reason = context.get("reason")
            subject = "Your VPN access was disabled"
            reason_text = f"Reason: {reason}" if reason else None
            body = self._wrap_message(
                identifier,
                [
                    "Your account has been disabled.",
                    reason_text,
                    self._format_actor(by),
                ],
            )
        elif trigger == EmailNotificationTrigger.data_usage_reset:
            by = context.get("by")
            subject = "Your VPN data usage was reset"
            body = self._wrap_message(
                identifier,
                [
                    "Your data usage has been reset.",
                    base_details,
                    self._format_actor(by),
                ],
            )
        elif trigger == EmailNotificationTrigger.data_reset_by_next:
            subject = "Your VPN plan switched to the next cycle"
            body = self._wrap_message(
                identifier,
                [
                    "Your account has been refreshed according to the next plan schedule.",
                    base_details,
                ],
            )
        elif trigger == EmailNotificationTrigger.subscription_revoked:
            by = context.get("by")
            subject = "Your subscription links were revoked"
            body = self._wrap_message(
                identifier,
                [
                    "Subscription links were revoked. You will need to request new ones.",
                    self._format_actor(by),
                ],
            )
        elif trigger == EmailNotificationTrigger.reached_usage_percent:
            percent = context.get("percent")
            subject = "Your VPN usage alert"
            body = self._wrap_message(
                identifier,
                [
                    f"You have used {percent}% of your available data." if percent is not None else None,
                    base_details,
                ],
            )
        elif trigger == EmailNotificationTrigger.reached_days_left:
            days_left = context.get("days")
            subject = "Your VPN subscription is ending soon"
            body = self._wrap_message(
                identifier,
                [
                    f"You have {days_left} day(s) remaining on your subscription." if days_left is not None else None,
                    base_details,
                ],
            )
        else:
            subject = ""
            body = ""

        return subject, body

    def _wrap_message(self, identifier: str, lines: list[Optional[str]]) -> str:
        filtered_lines = [line for line in lines if line]
        return "\n\n".join([f"Hello {identifier},"] + filtered_lines + ["\nRegards,", "Your VPN Administrator"])

    def _format_user_details(self, user: UserResponse) -> str:
        data_limit = "Unlimited" if not user.data_limit else self._format_bytes(user.data_limit)
        expire = self._format_expire(user.expire)
        return f"Status: {user.status.value if hasattr(user.status, 'value') else user.status}\nData limit: {data_limit}\nExpires: {expire}"

    @staticmethod
    def _format_actor(actor) -> Optional[str]:
        if not actor:
            return None
        if isinstance(actor, str):
            return f"Changed by: {actor}"
        try:
            return f"Changed by: {actor.username}"
        except AttributeError:
            return None

    @staticmethod
    def _format_bytes(value: int) -> str:
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if value < 1024:
                return f"{value:.2f} {unit}"
            value /= 1024
        return f"{value:.2f} PB"

    @staticmethod
    def _format_expire(expire: Optional[int]) -> str:
        if not expire:
            return "No expiration"
        try:
            return datetime.utcfromtimestamp(expire).strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            return "Unknown"


email_notifications = EmailNotificationManager()


def invalidate_email_notifications_cache() -> None:
    email_notifications.invalidate()
