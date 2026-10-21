import hashlib
import hmac
import logging
import secrets
import smtplib
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import delete, func, select, update

from app.api.dependencies import CurrentUser, DatabaseSession, bearer_scheme
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models.entities import (
    AuthenticationAttempt,
    AuthSession,
    Organization,
    PasswordResetToken,
    User,
)
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    UserResponse,
)
from app.services.audit import record_audit
from app.services.mail import send_password_reset_email

router = APIRouter(prefix="/auth", tags=["authentication"])
logger = logging.getLogger(__name__)


def _rate_limit_key(identity: str) -> str:
    secret = get_settings().jwt_secret or "fleetfuel"
    return hmac.new(secret.encode(), identity.encode(), hashlib.sha256).hexdigest()


def _count_recent_attempts(session: DatabaseSession, key_hash: str, cutoff: datetime) -> int:
    session.execute(
        delete(AuthenticationAttempt).where(
            AuthenticationAttempt.key_hash == key_hash,
            AuthenticationAttempt.attempted_at < cutoff,
        )
    )
    return (
        session.scalar(
            select(func.count(AuthenticationAttempt.id)).where(
                AuthenticationAttempt.key_hash == key_hash,
                AuthenticationAttempt.attempted_at >= cutoff,
            )
        )
        or 0
    )


@router.post("/login", response_model=AccessTokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    session: DatabaseSession,
) -> AccessTokenResponse:
    client_host = request.client.host if request.client else "unknown"
    key_hash = _rate_limit_key(f"login:{client_host}:{payload.email.lower()}")
    cutoff = datetime.now(UTC) - timedelta(minutes=15)
    if _count_recent_attempts(session, key_hash, cutoff) >= 10:
        session.commit()
        raise HTTPException(status_code=429, detail="Too many login attempts; try again later")
    user = session.scalar(select(User).where(User.email == payload.email.lower()))
    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
        or (
            user.organization_id is not None
            and session.scalar(
                select(Organization.id).where(
                    Organization.id == user.organization_id,
                    Organization.status == "ACTIVE",
                )
            )
            is None
        )
    ):
        session.add(AuthenticationAttempt(key_hash=key_hash))
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token, session_id, expires_at = create_access_token(user.id)
    session.add(AuthSession(id=session_id, user_id=user.id, expires_at=expires_at))
    record_audit(
        session,
        organization_id=user.organization_id,
        actor_id=user.id,
        action="auth.login_succeeded",
        resource_type="user",
        resource_id=user.id,
    )
    session.commit()
    return AccessTokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def current_user(user: CurrentUser) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        organization_id=str(user.organization_id) if user.organization_id else None,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
    )


@router.post("/logout", status_code=204)
def logout(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    session: DatabaseSession,
    user: CurrentUser,
) -> None:
    _, session_id = decode_access_token(credentials.credentials)
    auth_session = session.get(AuthSession, session_id)
    if auth_session is not None and auth_session.user_id == user.id:
        auth_session.revoked_at = datetime.now(UTC)
        record_audit(
            session,
            organization_id=user.organization_id,
            actor_id=user.id,
            action="auth.logout",
            resource_type="auth_session",
            resource_id=session_id,
        )
        session.commit()


@router.post("/password-reset/request", status_code=202)
def request_password_reset(
    payload: PasswordResetRequest,
    request: Request,
    session: DatabaseSession,
) -> dict[str, str]:
    client_host = request.client.host if request.client else "unknown"
    key_hash = _rate_limit_key(f"reset:{client_host}")
    cutoff = datetime.now(UTC) - timedelta(hours=1)
    if _count_recent_attempts(session, key_hash, cutoff) >= 5:
        session.commit()
        raise HTTPException(status_code=429, detail="Too many reset requests; try again later")
    session.add(AuthenticationAttempt(key_hash=key_hash))
    user = session.scalar(
        select(User).where(User.email == payload.email.lower(), User.is_active.is_(True))
    )
    raw_token: str | None = None
    if user is not None:
        raw_token = secrets.token_urlsafe(48)
        reset = PasswordResetToken(
            user_id=user.id,
            token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
        )
        session.add(reset)
        record_audit(
            session,
            organization_id=user.organization_id,
            actor_id=user.id,
            action="auth.password_reset_requested",
            resource_type="user",
            resource_id=user.id,
        )
    session.commit()
    if user is not None and raw_token is not None:
        try:
            if not send_password_reset_email(user.email, raw_token):
                logger.warning("Password reset requested but SMTP delivery is not configured")
        except (OSError, smtplib.SMTPException):
            logger.exception("Password reset email delivery failed")
    return {"message": "If the account exists, reset instructions will be sent"}


@router.post("/password-reset/confirm", status_code=204)
def confirm_password_reset(
    payload: PasswordResetConfirm,
    session: DatabaseSession,
) -> None:
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    reset = session.scalar(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == token_hash)
        .with_for_update()
    )
    if reset is None or reset.used_at is not None:
        raise HTTPException(status_code=400, detail="Reset token is invalid or already used")
    expires_at = reset.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=400, detail="Reset token has expired")
    user = session.get(User, reset.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="Reset token is invalid or already used")
    user.password_hash = hash_password(payload.new_password)
    reset.used_at = datetime.now(UTC)
    session.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    record_audit(
        session,
        organization_id=user.organization_id,
        actor_id=user.id,
        action="auth.password_reset_completed",
        resource_type="user",
        resource_id=user.id,
    )
    session.commit()
