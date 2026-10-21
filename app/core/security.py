from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

password_hash = PasswordHash.recommended()
ALGORITHM = "HS256"
TOKEN_ISSUER = "fleetfuel"
TOKEN_AUDIENCE = "fleetfuel-api"


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(
    user_id: UUID,
    expires_in: timedelta = timedelta(minutes=20),
) -> tuple[str, UUID, datetime]:
    secret = get_settings().jwt_secret
    if not secret:
        raise RuntimeError("FLEETFUEL_JWT_SECRET must be configured")
    now = datetime.now(UTC)
    session_id = uuid4()
    expires_at = now + expires_in
    claims = {
        "sub": str(user_id),
        "jti": str(session_id),
        "iss": TOKEN_ISSUER,
        "aud": TOKEN_AUDIENCE,
        "iat": now,
        "exp": expires_at,
    }
    return jwt.encode(claims, secret, algorithm=ALGORITHM), session_id, expires_at


def decode_access_token(token: str) -> tuple[UUID, UUID]:
    secret = get_settings().jwt_secret
    if not secret:
        raise RuntimeError("FLEETFUEL_JWT_SECRET must be configured")
    claims = jwt.decode(
        token,
        secret,
        algorithms=[ALGORITHM],
        issuer=TOKEN_ISSUER,
        audience=TOKEN_AUDIENCE,
        options={"require": ["sub", "jti", "exp", "iat"]},
    )
    return UUID(claims["sub"]), UUID(claims["jti"])
