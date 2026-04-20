from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.database import get_db
from app.models import User
from app.schemas import (
    UserRegisterRequest, UserLoginRequest, RefreshTokenRequest, TokenResponse,
    UserResponse
)
from app.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from app.dependencies import get_current_user, verify_object_access
from app.logging_config import log_audit, log_security_event, AuditAction

router = APIRouter()

login_attempts = {}
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 900  


def check_login_attempts(username: str) -> bool:
    if username not in login_attempts:
        return True
    
    attempts, lockout_time = login_attempts[username]
    if datetime.now(timezone.utc) > lockout_time:
        del login_attempts[username]
        return True
    
    if attempts >= MAX_LOGIN_ATTEMPTS:
        return False
    
    return True


def record_login_attempt(username: str, success: bool) -> None:
    if success:
        if username in login_attempts:
            del login_attempts[username]
    else:
        if username not in login_attempts:
            login_attempts[username] = (1, datetime.now(timezone.utc) + timedelta(seconds=LOCKOUT_DURATION))
        else:
            attempts, _ = login_attempts[username]
            login_attempts[username] = (attempts + 1, datetime.now(timezone.utc) + timedelta(seconds=LOCKOUT_DURATION))


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    user_data: UserRegisterRequest,
    db: Session = Depends(get_db),
    x_forwarded_for: Optional[str] = Header(None)
):

    client_ip = x_forwarded_for.split(',')[0] if x_forwarded_for else "unknown"
    
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        log_security_event(
            event_type="duplicate_registration",
            reason=f"Username already exists: {user_data.username}",
            severity="WARNING"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким именем уже существует"
        )
    
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        log_security_event(
            event_type="duplicate_email",
            reason="Email already registered",
            severity="WARNING"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email уже зарегистрирован"
        )
    
    existing_phone = db.query(User).filter(User.phone == user_data.phone).first()
    if existing_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Номер телефона уже зарегистрирован"
        )
    
    hashed_password = hash_password(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        phone=user_data.phone,
        hashed_password=hashed_password,
        role="customer"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    log_audit(
        action=AuditAction.USER_REGISTERED,
        user_id=new_user.id,
        ip_address=client_ip,
        success=True
    )
    
    return new_user


@router.post("/login", response_model=TokenResponse)
def login_user(
    credentials: UserLoginRequest,
    db: Session = Depends(get_db),
    x_forwarded_for: Optional[str] = Header(None)
):

    client_ip = x_forwarded_for.split(',')[0] if x_forwarded_for else "unknown"
    
    if not check_login_attempts(credentials.username):
        log_security_event(
            event_type="brute_force_attempt",
            reason=f"Too many login attempts for {credentials.username}",
            severity="CRITICAL"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много попыток входа. Попробуйте позже"
        )
    
    user = db.query(User).filter(User.username == credentials.username).first()
    
    if user is None or not verify_password(credentials.password, user.hashed_password):
        record_login_attempt(credentials.username, False)
        log_security_event(
            event_type="failed_login",
            reason=f"Invalid credentials for {credentials.username}",
            ip_address=client_ip,
            severity="WARNING"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль"
        )
    
    if not user.is_active:
        log_security_event(
            event_type="inactive_user_login_attempt",
            user_id=user.id,
            severity="WARNING"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Неверное имя пользователя или пароль"
        )
    
    record_login_attempt(credentials.username, True)
    
    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})
    
    log_audit(
        action=AuditAction.USER_LOGIN,
        user_id=user.id,
        ip_address=client_ip,
        success=True
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/refresh", response_model=TokenResponse)
def refresh_tokens(
    refresh_request: RefreshTokenRequest,
    db: Session = Depends(get_db),
    x_forwarded_for: Optional[str] = Header(None)
):

    client_ip = x_forwarded_for.split(',')[0] if x_forwarded_for else "unknown"

    payload = verify_token(refresh_request.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        log_security_event(
            event_type="invalid_refresh_token",
            reason="Invalid or expired refresh token",
            severity="WARNING"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учетные данные"
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учетные данные"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учетные данные"
        )

    access_token = create_access_token(data={"sub": user.id})
    new_refresh_token = create_refresh_token(data={"sub": user.id})

    log_audit(
        action=AuditAction.USER_LOGIN,
        user_id=user.id,
        details="Access token refreshed",
        ip_address=client_ip,
        success=True
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token
    )


@router.post("/logout", response_model=dict)
def logout_user(
    current_user: User = Depends(get_current_user),
    x_forwarded_for: Optional[str] = Header(None)
):

    client_ip = x_forwarded_for.split(',')[0] if x_forwarded_for else "unknown"

    log_audit(
        action=AuditAction.USER_LOGOUT,
        user_id=current_user.id,
        ip_address=client_ip,
        success=True
    )

    return {"message": "Выход выполнен успешно"}
