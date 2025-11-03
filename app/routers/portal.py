from datetime import timedelta

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Request,
    Response,
    status,
)
from fastapi.responses import RedirectResponse

from app import logger
from app.db import Session, crud, get_db
from app.dependencies import get_current_portal_user
from app.models.portal import MagicLinkRequest, MessageResponse, PortalUserResponse
from app.models.user import UserResponse
from app.utils.email_notifications import email_notifications
from app.utils.jwt import create_user_session_token
from config import (
    USER_LOGIN_TOKEN_EXPIRE_MINUTES,
    USER_SESSION_COOKIE_NAME,
    USER_SESSION_EXPIRE_MINUTES,
)

api_router = APIRouter(prefix="/api", tags=["Portal"])
router = APIRouter(tags=["Portal"])


GENERIC_MESSAGE = "If the email is registered, a sign-in link has been sent."


def _get_client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


@api_router.post(
    "/auth/magic-link",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_magic_link(
    payload: MagicLinkRequest,
    request: Request,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
) -> MessageResponse:
    identifier = payload.email.strip()
    dbuser = crud.get_user(db, identifier)
    if not dbuser:
        lowered = identifier.lower()
        if lowered != identifier:
            dbuser = crud.get_user(db, lowered)

    if not dbuser or not dbuser.email:
        return MessageResponse(detail=GENERIC_MESSAGE)

    expires_in = USER_LOGIN_TOKEN_EXPIRE_MINUTES if USER_LOGIN_TOKEN_EXPIRE_MINUTES > 0 else 15

    token = crud.create_user_login_token(
        db,
        dbuser,
        expires_in,
        requested_ip=_get_client_ip(request),
        requested_user_agent=request.headers.get("User-Agent"),
    )

    try:
        login_url = str(request.url_for("portal_magic_link", token=token))
    except Exception:
        base = str(request.base_url).rstrip("/")
        login_url = f"{base}/auth/magic?token={token}"

    # Capture primitives before scheduling background task to avoid accessing a detached ORM instance
    _email = dbuser.email
    _username = dbuser.username

    def _send_email(email: str, username: str) -> None:
        success = email_notifications.send_magic_link(
            email=email,
            username=username,
            link=login_url,
            expires_in_minutes=expires_in,
        )
        if success:
            logger.info("Sent magic link to %s", email)
        else:
            logger.warning("Magic link email was not sent to %s", email)

    bg.add_task(_send_email, _email, _username)

    return MessageResponse(detail=GENERIC_MESSAGE)


@api_router.get(
    "/me",
    response_model=PortalUserResponse,
)
def current_user(dbuser=Depends(get_current_portal_user)) -> PortalUserResponse:
    user = UserResponse.model_validate(dbuser)
    return PortalUserResponse.from_user(user)


@api_router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
def logout() -> Response:
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(USER_SESSION_COOKIE_NAME, path="/")
    return response


@router.get("/auth/magic", name="portal_magic_link")
def verify_magic_link(
    token: str,
    request: Request,
    db: Session = Depends(get_db),
):
    user, error = crud.consume_user_login_token(
        db,
        token,
        consumed_ip=_get_client_ip(request),
        consumed_user_agent=request.headers.get("User-Agent"),
    )

    if not user:
        logger.info("Magic link login failed: %s", error)
        target = "/?login=invalid" if error != "expired" else "/?login=expired"
        return RedirectResponse(target, status_code=status.HTTP_303_SEE_OTHER)

    session_token = create_user_session_token(user.id)
    response = RedirectResponse("/?login=success", status_code=status.HTTP_303_SEE_OTHER)
    max_age = (
        int(timedelta(minutes=USER_SESSION_EXPIRE_MINUTES).total_seconds())
        if USER_SESSION_EXPIRE_MINUTES > 0
        else None
    )
    secure_cookie = request.url.scheme == "https"
    response.set_cookie(
        USER_SESSION_COOKIE_NAME,
        session_token,
        max_age=max_age,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        path="/",
    )
    logger.info("User %s authenticated via magic link", user.username)
    return response
