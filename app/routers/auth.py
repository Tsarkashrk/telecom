from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.database import get_db
from app.models import User, Subscription, TariffPlan, Invoice
from app.schemas import (
    UserRegisterRequest, UserLoginRequest, TokenResponse,
    UserResponse, TariffPlanResponse, SubscriptionResponse, InvoiceResponse
)
from app.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.dependencies import get_current_user, verify_object_access
from app.logging_config import log_audit, log_security_event, AuditAction

router = APIRouter()

# Защита от brute-force (простая реализация)
login_attempts = {}
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 900  # 15 минут


def check_login_attempts(username: str) -> bool:
    """Проверка попыток входа"""
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
    """Запись попытки входа"""
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
    """
    Регистрация нового пользователя.
    
    Требования безопасности:
    - Валидация всех входных данных через Pydantic
    - Хеширование пароля bcrypt
    - Проверка уникальности email и username
    """
    client_ip = x_forwarded_for.split(',')[0] if x_forwarded_for else "unknown"
    
    # Проверка уникальности username
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
    
    # Проверка уникальности email
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
    
    # Проверка уникальности телефона
    existing_phone = db.query(User).filter(User.phone == user_data.phone).first()
    if existing_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Номер телефона уже зарегистрирован"
        )
    
    # Создание пользователя
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
    
    # Логирование успешной регистрации
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
    """
    Вход пользователя.
    
    Требования безопасности:
    - Проверка пароля против хеша
    - Генерация JWT токена с ограниченным сроком жизни (access + refresh)
    - Защита от brute-force атак
    - Нейтральное сообщение об ошибке
    """
    client_ip = x_forwarded_for.split(',')[0] if x_forwarded_for else "unknown"
    
    # Проверка попыток входа
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
    
    # Поиск пользователя
    user = db.query(User).filter(User.username == credentials.username).first()
    
    # Нейтральное сообщение об ошибке (не раскрываем информацию)
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
    
    # Генерация токенов
    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})
    
    # Логирование успешного входа
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
    """
    Получить информацию о текущем пользователе.
    """
    return current_user
