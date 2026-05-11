import secrets
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.security import verify_token
from app.logging_config import AuditAction, log_audit, log_security_event
from app.models import Invoice, Subscription, User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Неверные учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise credentials_exception

    token = credentials.credentials
    payload = verify_token(token, expected_type="access")
    if payload is None:
        raise credentials_exception

    user_id_raw = payload.get("sub")
    if user_id_raw is None:
        raise credentials_exception

    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь неактивен"
        )

    return user


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Требуется роль администратора"
        )
    return current_user


async def get_current_operator(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ["operator", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Требуется роль оператора или администратора"
        )
    return current_user


async def verify_object_access(
    resource_owner_id: int,
    current_user: User
) -> bool:
    if current_user.role == "admin":
        return True

    if current_user.id == resource_owner_id:
        return True

    return False


def ensure_resource_access(
    *,
    resource_owner_id: int,
    current_user: User,
    resource_type: str,
    resource_id: int,
    action: str = "access",
    privileged_roles: set[str] | None = None,
    client_ip: str | None = None,
) -> None:
    allowed_roles = privileged_roles or {"admin"}
    if current_user.id == resource_owner_id or current_user.role in allowed_roles:
        return

    event_suffix = "payment_attempt" if action == "pay" else action
    log_security_event(
        event_type=f"unauthorized_{resource_type}_{event_suffix}",
        user_id=current_user.id,
        reason=(
            f"Attempted to {action} {resource_type} {resource_id} "
            f"owned by user {resource_owner_id}"
        ),
        severity="WARNING",
        ip_address=client_ip,
    )
    log_audit(
        action=AuditAction.UNAUTHORIZED_ACCESS_ATTEMPT,
        user_id=current_user.id,
        details=f"{action}:{resource_type}:{resource_id}",
        ip_address=client_ip,
        success=False,
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Доступ запрещен",
    )


def ensure_subscription_access(
    subscription: Subscription,
    current_user: User,
    client_ip: str | None = None,
) -> Subscription:
    ensure_resource_access(
        resource_owner_id=subscription.user_id,
        current_user=current_user,
        resource_type="subscription",
        resource_id=subscription.id,
        privileged_roles={"operator", "admin"},
        client_ip=client_ip,
    )
    return subscription


def ensure_invoice_access(
    invoice: Invoice,
    current_user: User,
    *,
    action: str = "access",
    client_ip: str | None = None,
) -> Invoice:
    ensure_resource_access(
        resource_owner_id=invoice.user_id,
        current_user=current_user,
        resource_type="invoice",
        resource_id=invoice.id,
        action=action,
        privileged_roles={"operator", "admin"},
        client_ip=client_ip,
    )
    return invoice


async def get_internal_service(
    x_internal_api_key: Optional[str] = Header(None, alias="X-Internal-API-Key")
) -> str:
    if not settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Внутренний API недоступен"
        )

    # Безопасно: compare_digest снижает риск тайминговых атак.

    # vul: if x_internal_api_key != "hardcoded-demo-key":
    
    if x_internal_api_key is None or not secrets.compare_digest(
        x_internal_api_key,
        settings.internal_api_key
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Доступ запрещен"
        )

    return "billing-service"
