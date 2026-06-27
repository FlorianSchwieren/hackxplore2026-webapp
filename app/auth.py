from dataclasses import dataclass
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, status
from jwt import PyJWKClient

from app.config import Settings, get_settings


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    email: str | None = None


def _extract_bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    return authorization.split(" ", 1)[1].strip()


def _decode_with_jwks(token: str, settings: Settings) -> dict:
    if not settings.supabase_jwks_url:
        raise HTTPException(status_code=500, detail="SUPABASE_JWKS_URL is not configured")
    signing_key = PyJWKClient(settings.supabase_jwks_url).get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256", "ES256"],
        options={"verify_aud": False},
    )


def _decode_with_secret(token: str, settings: Settings) -> dict:
    if not settings.supabase_jwt_secret:
        raise HTTPException(status_code=500, detail="SUPABASE_JWT_SECRET is not configured")
    return jwt.decode(
        token,
        settings.supabase_jwt_secret,
        algorithms=["HS256"],
        options={"verify_aud": False},
    )


def decode_supabase_jwt(token: str, settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    try:
        if settings.supabase_jwks_url:
            return _decode_with_jwks(token, settings)
        return _decode_with_secret(token, settings)
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


def require_user(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    if settings.dev_auth_disabled:
        return CurrentUser(id=UUID("00000000-0000-0000-0000-000000000001"), email="dev@local")

    token = _extract_bearer(authorization)
    claims = decode_supabase_jwt(token, settings)
    subject = claims.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject")
    return CurrentUser(id=UUID(subject), email=claims.get("email"))


def require_ingest_secret(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    token = _extract_bearer(authorization)
    if token != settings.ingest_shared_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid ingest token")
