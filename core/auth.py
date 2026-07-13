from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.database.models import RefreshToken, User


ROLES = {"admin": 4, "manager": 3, "agent": 2, "viewer": 1}
bearer = HTTPBearer(auto_error=False)


def _secret() -> str:
    value = os.getenv("PLATFORM_JWT_SECRET", "")
    if len(value) < 32:
        raise RuntimeError("PLATFORM_JWT_SECRET must be at least 32 characters")
    return value


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000).hex()
    return f"pbkdf2_sha256${salt}${digest}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        _, salt, digest = encoded.split("$", 2)
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(password, salt), encoded)


def create_user(session: Session, username: str, password: str, role: str = "viewer") -> User:
    if role not in ROLES or len(password) < 10:
        raise ValueError("valid role and a password of at least 10 characters are required")
    user = User(username=username.strip().casefold(), password_hash=hash_password(password), role=role)
    session.add(user)
    session.commit()
    return user


def issue_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    minutes = int(os.getenv("PLATFORM_ACCESS_TOKEN_MINUTES", "15"))
    return jwt.encode({"sub": str(user.id), "username": user.username, "role": user.role, "type": "access", "iat": now, "exp": now + timedelta(minutes=minutes)}, _secret(), algorithm="HS256")


def issue_refresh_token(session: Session, user: User) -> str:
    raw = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    days = int(os.getenv("PLATFORM_REFRESH_TOKEN_DAYS", "7"))
    session.add(RefreshToken(id=str(uuid.uuid4()), user_id=user.id, token_hash=token_hash, expires_at=datetime.now(timezone.utc) + timedelta(days=days)))
    session.commit()
    return raw


def rotate_refresh_token(session: Session, raw: str) -> tuple[User, str]:
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    record = session.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    now = datetime.now(timezone.utc)
    if not record or record.revoked or record.expires_at.replace(tzinfo=timezone.utc) <= now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid refresh token")
    record.revoked = True
    user = session.get(User, record.user_id)
    new_token = issue_refresh_token(session, user)
    session.commit()
    return user, new_token


def revoke_refresh_token(session: Session, raw: str) -> None:
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    record = session.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if record:
        record.revoked = True
        session.commit()


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, _secret(), algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid access token") from exc
    if payload.get("type") != "access" or payload.get("role") not in ROLES:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid access token")
    return payload


def require_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "authentication required")
    return decode_access_token(credentials.credentials)


def require_role(minimum: str):
    def dependency(user: dict = Depends(require_user)) -> dict:
        if ROLES[user["role"]] < ROLES[minimum]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient permission")
        return user
    return dependency
