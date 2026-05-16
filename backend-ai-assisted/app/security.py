from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])

    issued_at = datetime.now(timezone.utc)
    if expires_delta:
        expire = issued_at + expires_delta
    else:
        expire = issued_at + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update(
        {
            "exp": expire,
            "iat": issued_at,
            "type": "access",
            "jti": str(uuid4()),
        }
    )
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )
    return encoded_jwt


def create_refresh_token(data: dict, token_version: int) -> str:
    to_encode = data.copy()
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    issued_at = datetime.now(timezone.utc)
    expire = issued_at + timedelta(
        days=settings.refresh_token_expire_days
    )
    to_encode.update(
        {
            "exp": expire,
            "iat": issued_at,
            "type": "refresh",
            "jti": str(uuid4()),
            "rtv": token_version,
        }
    )
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )
    return encoded_jwt
    

def verify_token(token: str, expected_type: Optional[str] = None) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )

        if payload.get("sub") is None:
            return None

        token_type = payload.get("type")
        if token_type not in {"access", "refresh"}:
            return None

        if expected_type is not None and token_type != expected_type:
            return None

        return payload
    except JWTError:
        return None
